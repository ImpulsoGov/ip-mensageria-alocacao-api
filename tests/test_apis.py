from unittest.mock import Mock, patch

import numpy as np
import pytest
from fastapi import HTTPException

from ip_mensageria_alocacao_api.apis import (
    alocar_entre_mensagens,
    prever_probabilidade_mensagem_ser_efetiva,
)
from ip_mensageria_alocacao_api.core.modelos import (
    DiaSemana,
    LinhaCuidado,
    Mensagem,
    MensagemTipo,
    Predicao,
    PredicaoSimulacao,
    Template,
)


@pytest.fixture
def mock_classificadores():
    classificadores = Mock()
    classificadores.modelos = [Mock(), Mock()]  # dois modelos mock
    classificadores.template_embedding_dims = 3
    classificadores.midia_embedding_dims = 2
    classificadores.modelos[0].predict_proba.return_value = np.array([[0.3, 0.7]])
    classificadores.modelos[1].predict_proba.return_value = np.array([[0.2, 0.8]])
    return classificadores


@pytest.fixture
def mock_cidadao_caracteristicas():
    return {
        "idade": 30,
        "plano_saude_privado": True,
        "raca_cor": "Branca",
        "sexo": "Feminino",
        "tempo_desde_ultimo_procedimento": 10,
        "municipio_prop_domicilios_zona_rural": 0.1,
    }


@pytest.fixture
def sample_mensagem():
    return Mensagem(
        dia_semana=DiaSemana.segunda,
        horario=10,
        template_nome="template1",
        midia_url=None,
        template=None,
    )


@pytest.fixture
def sample_mensagem_com_template():
    return Mensagem(
        dia_semana=DiaSemana.segunda,
        horario=10,
        template_nome=None,
        midia_url=None,
        template=Template(
            texto="Olá!",
            botao0_texto="Sim",
            botao1_texto="Não",
            botao2_texto=None,
        ),
    )


@pytest.fixture
def sample_mensagem_sem_template():
    return Mensagem(
        dia_semana=DiaSemana.segunda,
        horario=10,
        template_nome=None,
        midia_url=None,
        template=None,
    )


@patch("ip_mensageria_alocacao_api.apis.obter_caracteristicas_usuario")
@patch("ip_mensageria_alocacao_api.apis.obter_tempo_desde_ultimo_procedimento")
@patch("ip_mensageria_alocacao_api.apis.obter_template_embedding_por_nome")
@patch("ip_mensageria_alocacao_api.apis.preparar_atributos_para_predicao")
@patch("ip_mensageria_alocacao_api.apis.converter_df_em_pool")
def test_prever_probabilidade_com_template_nome(
    mock_converter,
    mock_preparar,
    mock_obter_template,
    mock_obter_tempo,
    mock_obter_caracteristicas,
    mock_classificadores,
    mock_cidadao_caracteristicas,
    sample_mensagem,
):
    mock_obter_caracteristicas.return_value = mock_cidadao_caracteristicas
    mock_obter_tempo.return_value = 10
    mock_obter_template.return_value = np.array([0.1, 0.2, 0.3])
    mock_preparar.return_value = Mock()
    mock_converter.return_value = Mock()

    result = prever_probabilidade_mensagem_ser_efetiva(
        cidadao_id="123",
        linha_cuidado=LinhaCuidado.cronicos,
        mensagem_tipo=MensagemTipo.mensagem_inicial,
        mensagem=sample_mensagem,
        classificadores=mock_classificadores,
    )

    assert isinstance(result, Predicao)
    assert result.probabilidade == pytest.approx(0.75)  # média de 0.7 e 0.8
    assert result.erro_padrao == pytest.approx(0.0707, rel=1e-3)  # std de [0.7, 0.8]


@patch("ip_mensageria_alocacao_api.apis.obter_caracteristicas_usuario")
@patch("ip_mensageria_alocacao_api.apis.obter_tempo_desde_ultimo_procedimento")
@patch("ip_mensageria_alocacao_api.apis.obter_template_embedding_por_texto")
@patch("ip_mensageria_alocacao_api.apis.preparar_atributos_para_predicao")
@patch("ip_mensageria_alocacao_api.apis.converter_df_em_pool")
def test_prever_probabilidade_com_template(
    mock_converter,
    mock_preparar,
    mock_obter_template,
    mock_obter_tempo,
    mock_obter_caracteristicas,
    mock_classificadores,
    mock_cidadao_caracteristicas,
    sample_mensagem_com_template,
):
    mock_obter_caracteristicas.return_value = mock_cidadao_caracteristicas
    mock_obter_tempo.return_value = 10
    mock_obter_template.return_value = np.array([0.1, 0.2, 0.3])
    mock_preparar.return_value = Mock()
    mock_converter.return_value = Mock()

    result = prever_probabilidade_mensagem_ser_efetiva(
        cidadao_id="123",
        linha_cuidado=LinhaCuidado.cronicos,
        mensagem_tipo=MensagemTipo.mensagem_inicial,
        mensagem=sample_mensagem_com_template,
        classificadores=mock_classificadores,
    )

    assert isinstance(result, Predicao)


@patch("ip_mensageria_alocacao_api.apis.obter_caracteristicas_usuario")
@patch("ip_mensageria_alocacao_api.apis.obter_tempo_desde_ultimo_procedimento")
def test_prever_probabilidade_sem_template(
    mock_obter_tempo,
    mock_obter_caracteristicas,
    mock_classificadores,
    mock_cidadao_caracteristicas,
    sample_mensagem_sem_template,
):
    mock_obter_caracteristicas.return_value = mock_cidadao_caracteristicas
    mock_obter_tempo.return_value = 10

    with pytest.raises(HTTPException) as exc_info:
        prever_probabilidade_mensagem_ser_efetiva(
            cidadao_id="123",
            linha_cuidado=LinhaCuidado.cronicos,
            mensagem_tipo=MensagemTipo.mensagem_inicial,
            mensagem=sample_mensagem_sem_template,
            classificadores=mock_classificadores,
        )
    assert exc_info.value.status_code == 400


@patch("ip_mensageria_alocacao_api.apis.thompson_sample")
def test_alocar_entre_mensagens(mock_thompson):
    mock_thompson.side_effect = [0.5, 0.8, 0.3]  # amostras

    mensagens = [
        Mensagem(dia_semana=DiaSemana.segunda, horario=10, template_nome="t1"),
        Mensagem(dia_semana=DiaSemana.terca, horario=11, template_nome="t2"),
        Mensagem(dia_semana=DiaSemana.quarta, horario=12, template_nome="t3"),
    ]

    predicoes = [
        Predicao(mensagem=mensagens[0], probabilidade=0.6, erro_padrao=0.1),
        Predicao(mensagem=mensagens[1], probabilidade=0.7, erro_padrao=0.1),
        Predicao(mensagem=mensagens[2], probabilidade=0.5, erro_padrao=0.1),
    ]

    result = alocar_entre_mensagens(predicoes=predicoes)

    assert isinstance(result, PredicaoSimulacao)
    assert result.probabilidade_sorteada == 0.8  # max das amostras
    assert result.mensagem == mensagens[1]  # índice 1


def test_alocar_entre_mensagens_listas_vazias():
    with pytest.raises(AssertionError):
        alocar_entre_mensagens(predicoes=[])
