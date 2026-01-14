from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Sequence

import numpy as np
from fastapi import HTTPException

from ip_mensageria_alocacao_api.core.auxiliar import (
    converter_df_em_pool,
    obter_caracteristicas_usuario,
    obter_midia_embedding,
    obter_template_embedding_por_nome,
    obter_template_embedding_por_texto,
    obter_tempo_desde_ultimo_procedimento,
    preparar_atributos_para_predicao,
    thompson_sample,
)
from ip_mensageria_alocacao_api.core.modelos import (
    Classificador,
    LinhaCuidado,
    Mensagem,
    MensagemTipo,
    Predicao,
    PredicaoSimulacao,
)

logger = logging.getLogger(__name__)


def prever_probabilidade_mensagem_ser_efetiva(
    cidadao_id: str,
    linha_cuidado: LinhaCuidado,
    mensagem_tipo: MensagemTipo,
    mensagem: Mensagem,
    classificadores: Classificador,
) -> Predicao:
    logger.info(f"Iniciando predição para cidadão {cidadao_id}")
    cidadao_caracteristicas = obter_caracteristicas_usuario(cidadao_id)
    logger.info("Características do cidadão obtidas")
    tempo_desde_ultimo_procedimento = obter_tempo_desde_ultimo_procedimento(
        cidadao_id=cidadao_id,
        linha_cuidado=linha_cuidado,
    )
    logger.info("Tempo desde último procedimento obtido")
    if mensagem.template_nome:
        template_embedding = obter_template_embedding_por_nome(
            mensagem.template_nome,
        )
    elif mensagem.template:
        template_embedding = obter_template_embedding_por_texto(
            mensagem.template.texto,
            mensagem.template.botao0_texto,
            mensagem.template.botao1_texto,
            mensagem.template.botao2_texto,
        )
    else:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=("Bad Request :: `template_nome` ou `template` não informado."),
        )
    logger.info("Template embedding obtido")
    if mensagem.midia_url:
        midia_embedding = obter_midia_embedding(mensagem.midia_url)
    else:
        midia_embedding = np.zeros(
            classificadores.midia_embedding_dims,
            dtype=float,
        )
    logger.info("Mídia embedding obtido")
    atributos = preparar_atributos_para_predicao(
        classificadores=classificadores,
        cidadao_caracteristicas=cidadao_caracteristicas,
        linha_cuidado=linha_cuidado,
        tempo_desde_ultimo_procedimento=tempo_desde_ultimo_procedimento,
        mensagem_tipo=mensagem_tipo,
        mensagem_dia_semana=mensagem.dia_semana,
        mensagem_horario=mensagem.horario,
        mensagem_template_embedding=template_embedding,
        mensagem_midia_embedding=midia_embedding,
    )
    pool = converter_df_em_pool(atributos, classificadores)

    # ensemble bootstrap -> média e desvio entre modelos
    ps = np.array([float(m.predict_proba(pool)[0, 1]) for m in classificadores.modelos])
    p_mean = float(ps.mean())
    p_std = float(ps.std(ddof=1)) if len(ps) > 1 else 0.0

    logger.info(f"Predição concluída: prob={p_mean}, std={p_std}")
    return Predicao(
        mensagem=mensagem,
        probabilidade=p_mean,
        erro_padrao=p_std,
    )


def alocar_entre_mensagens(predicoes: Sequence[Predicao]) -> PredicaoSimulacao:
    """
    Bootstrapped TS sobre as opções de mensagens, usando a média
    (probabilidade) e erro-padrão (desvio entre modelos) para aproximar um
    Beta(α,β) e amostrar uma 'probabilidade sorteada'.
    """
    assert len(predicoes) > 0, "Lista vazia"

    amostras = []
    for pr in predicoes:
        p = float(pr.probabilidade)
        se = max(float(pr.erro_padrao), 1e-6)
        amostras.append(thompson_sample(p, se))

    idx = int(np.argmax(amostras))
    return PredicaoSimulacao(
        mensagem=predicoes[idx].mensagem,
        probabilidade_sorteada=float(amostras[idx]),
    )
