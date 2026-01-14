from ip_mensageria_alocacao_api.core import modelos


def test_mensagem_validation_both_template_fields_none():
    """Test Mensagem model allows both template_nome and template to be None."""
    
    # This should be valid - the API logic handles the error case
    msg = modelos.Mensagem(
        dia_semana=modelos.DiaSemana.segunda,
        horario=10,
        template_nome=None,
        template=None
    )
    assert msg.template_nome is None
    assert msg.template is None


def test_cidadao_caracteristicas_optional_fields():
    """Test CidadaoCaracteristicas with all None values."""
    
    cidadao = modelos.CidadaoCaracteristicas(
        idade=None,
        plano_saude_privado=None,
        raca_cor=None,
        sexo=None,
        tempo_desde_ultimo_procedimento=None,
        municipio_prop_domicilios_zona_rural=None,
    )
    assert cidadao.idade is None
    assert cidadao.sexo is None

def test_predicao_validation():
    """Test Predicao model validation."""
    
    msg = modelos.Mensagem(
        dia_semana=modelos.DiaSemana.segunda,
        horario=10
    )
    pred = modelos.Predicao(
        mensagem=msg,
        probabilidade=0.75,
        erro_padrao=0.05
    )
    assert pred.probabilidade == 0.75
    assert pred.erro_padrao == 0.05
