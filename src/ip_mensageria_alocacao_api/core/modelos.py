from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import AnyUrl, BaseModel, Field


class Classificador(BaseModel):
    modelos: list[Any]
    atributos_colunas: list[str]
    atributos_categoricos: list[str]
    imputador_numerico: Any
    template_embedding_dims: int
    midia_embedding_dims: int


class CidadaoCaracteristicas(BaseModel):
    idade: Optional[int]
    plano_saude_privado: Optional[bool]
    raca_cor: Optional[
        Literal[
            "Amarela",
            "Branca",
            "Indígena",
            "Parda",
            "Preta",
        ]
    ]
    sexo: Optional[Literal["Feminino", "Masculino"]]
    tempo_desde_ultimo_procedimento: Optional[int]
    municipio_prop_domicilios_zona_rural: Optional[float]


class DiaSemana(StrEnum):
    segunda = "Monday"
    terca = "Tuesday"
    quarta = "Wednesday"
    quinta = "Thursday"
    sexta = "Friday"
    sabado = "Saturday"
    domingo = "Sunday"


class LinhaCuidado(StrEnum):
    cronicos = "crônicos"
    citotopatologico = "citopatológico"


class Mensagem(BaseModel):
    dia_semana: DiaSemana
    horario: int
    midia_url: Optional[AnyUrl] = Field(None)
    template_nome: Optional[str] = Field(None)
    template: Optional["Template"] = Field(None)


class MensagemTipo(StrEnum):
    mensagem_inicial = "mensagem_inicial"
    primeiro_lembrete = "primeiro_lembrete"
    segundo_lembrete = "segundo_lembrete"


class Predicao(BaseModel):
    mensagem: Mensagem
    probabilidade: float
    erro_padrao: float


class PredicaoSimulacao(BaseModel):
    mensagem: Mensagem
    probabilidade_sorteada: float


class Template(BaseModel):
    texto: str
    botao0_texto: Optional[str] = Field(None, alias="botao0_texto")
    botao1_texto: Optional[str] = Field(None, alias="botao1_texto")
    botao2_texto: Optional[str] = Field(None, alias="botao2_texto")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenDados(BaseModel):
    usuario_nome: str | None = None


class Usuario(BaseModel):
    usuario_nome: str
    desativado: bool = False


class UsuarioNaBase(Usuario):
    senha_hash: str


# Update forward references
Mensagem.model_rebuild()
