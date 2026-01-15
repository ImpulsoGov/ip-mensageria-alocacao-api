# API de alocação de mensagens para o cidadão

[![License](https://img.shields.io/cocoapods/l/AFNetworking?style=flat-square)](https://github.com/rednafi/think-asyncio/blob/master/LICENSE)

***Veja a documentação pública da API em <https://ip-mensageria-alocacao-api-567502497958.us-central1.run.app/docs>.***

Este pacote implementa um serviço com [FastAPI][fastapi] para alocação automatizada entre diferentes templates de mensagens, mídias e condições de envio (horário, dia da semana), equilibrando o valor de obter novas informações com a priorização das mensagens com maior probabilidade de sucesso.

<details>
<summary> <b>Este diretório contém:</b> (<i>clique para expandir</i>) </summary>

```txt
├── bin
|   ├── Dockerfile-template
|   ├── generate_dockerfile.sh
|   └── update_deps.sh
├── dockerfiles
│   ├── python311
│   │   └── Dockerfile
|   ├── python312
│   │   └── Dockerfile
│   └── python313
│       └── Dockerfile
├── src
│   ├── ip_mensageria_alocacao_api
│   │   ├── __init__.py
│   │   ├── apis.py                 # funções principais
│   │   ├── core
│   │   │   ├── __init__.py
│   │   │   ├── autenticacao.py     # autenticação com JWT  
│   │   │   ├── auxiliar.py         # funções auxiliares
│   │   │   ├── bd.py               # conexão com BigQuery
│   │   │   ├── classificadores.py  # carrega pesos dos classificadores   
│   │   │   ├── configs.py          # lê configurações      
│   │   │   ├── modelos.py          # modelos do pydantic
│   │   │   └── logger.py           # log
│   │   ├── main.py                 # Define aplicação FastAPI
│   │   └── routes.py               # Define endpoints
├── tests
│   ├── __init__.py
│   ├── test_apis.py
│   ├── test_autenticacao.py
│   ├── test_auxiliar.py
│   ├── test_classificadores.py
│   ├── test_modelos.py
│   ├── test_logger.py
│   └── test_routes.py
├── LICENSE                     # licença MIT
├── makefile                    # scripts de manutenção e execução
├── pyproject.toml              # Configurações do Python
├── README.md                   # Este arquivo!
└── uv.lock                     # Dependências do Python/uv
```
</details>

## Sumário

- [Contexto](#contexto)
- [Instalação](#instalação)
  - [Rodando no Docker](#rodando-no-docker)
  - [Rodando localmente](#rodando-localmente)
- [Usando o serviço](#usando-o-serviço)
  - [Explorando os endpoints](#explorando-os-endpoints)
- [API](#api)
- [Contribuindo](#contribuindo)
  - [Desenvolvendo](#desenvolvendo)
- [Apêndice técnico](#apêndice-técnico)
  - [Treinamento do algoritmo para aprendizado a partir de envios anteriores](#treinamento-do-algoritmo-para-aprendizado-a-partir-de-envios-anteriores)
  - [Predição de probabilidade de mensagem ser efetiva](#predição-de-probabilidade-de-mensagem-ser-efetiva)
- [Licença](#licença)

## Contexto

A [ImpulsoGov](https://www.impulsogov.org/quem-somos) desenvolve e disponibiliza o [Impulso Previne](https://www.impulsoprevine.org/), plataforma de gestão da Atenção Primária à Saúde (APS) focada em promover a melhoria no cuidado dos usuários do Sistema Único de Saúde (SUS) em centenas de municípios brasileiros, por meio do uso de dados para facilitar a tomada de decisões e o dia a dia da profissional de saúde.

Desde 2025, o Impulso Previne tem disponibilizado para parte dos municípios atendidos o recurso de envio de mensagens multimídia por meio do WhatsApp, com o objetivo de incentivar o uso da APS e promover o cuidado da população.

Como parte do processo de melhoria contínua do serviço de mensageria para o cidadão, a equipe da ImpulsoGov realiza testes com diferentes modelos de mensagens e condições de envio. Esses testes ajudam a encontrar as condições quem melhor conduzem os usuários do SUS a adotarem comportamentos de cuidado com a própria saúde e com a saúde dos seus familiares - em especial o comparecimento a procedimentos preventivos de rotina.

Este pacote automatiza o processo de decisão dos melhores templates e contextos para envio de mensagens multimídia, a partir do aprendizado obtido com envios anteriores. Ele lida com dois desafios principais:

* Selecionar as melhores variações de mensagens e condições de envio para cada cidadão, levando em consideração suas características sociodemográficas;
* Obter informações sobre quais mensagens funcionam melhor e em que condições, de forma que os disparos de mensagens realizados no presente contribuam para uma alocação ainda mais efetiva no futuro.

A seção [Apêndice técnico](#apendice-tecnico) apresenta a abordagem utilizada pelo pacote para lidar com o [dilema prospecção X aproveitamento](https://en.wikipedia.org/wiki/Exploration%E2%80%93exploitation_dilemma) que surge da tensão entre esses dois objetivos.


## Instalação

### Pré-requisitos

* Python >= 3.11 e <= 3.13
* uv
* Docker
* Google Cloud SDK (gcloud)

### 🔐 Configuração de credenciais (IMPORTANTE)

Este projeto suporta **dois modos de autenticação**:

#### Desenvolvimento local (com arquivo JSON)

Usado apenas em máquinas locais.

* Crie uma Service Account na GCP
* Conceda as roles:
  * BigQuery Data Viewer
  * BigQuery Job User
  * Cloud Storage Viewer (para o bucket de modelos classificadores)
  * Secret Manager Secret Accessor (para segredo com chave de API)
  * Artifact Registry Writer (para implementação contínua)
  * Service Account Token Creator (para criar tokens de acesso)
* Baixe o arquivo `credentials.json`
* Copie `.env_sample` → `.env` e configure as variáveis necessárias, incluindo:

```env
GOOGLE_ARQUIVO_CREDENCIAIS=/app/credentials.json
```

#### Produção (Cloud Run – recomendado)

**Não use arquivo JSON.**

* Configure uma **Service Account no Cloud Run**
* Atribua as mesmas roles acima
* O código usa **Application Default Credentials (ADC)** automaticamente

### Início rápido (TL;DR)

#### Rodar localmente (sem Docker)

```sh
$ make setup-local
$ make run-local
```

#### Rodar localmente em um container Docker

```sh
$ make run-container
```

A API ficará disponível em `http://localhost:5002/`.

# Deploy Cloud Run

Pré-requisitos:

* `gcloud auth login`
* Projeto GCP configurado

```sh
make deploy-cloudrun \
  PROJECT_ID=meu-projeto-aqui \
  REGION=regiao-do-projeto \
  ARTEFATOS_PREDICAO_URI=gs://meu-bucket/modelos
```

O comando:

* Constrói a imagem
* Faz push para Google Cloud Registry
* Cria/atualiza o serviço no Cloud Run

- Clone o repositório e navegue até a raiz do projeto.

- Para rodar o aplicativo usando Docker, certifique-se de que você tenha [Docker][docker] instalado no seu sistema. A partir da raiz do projeto, execute:

    ```sh
    make run-container
    ```

## Usando o serviço

### Explorando os endpoints

Para explorar os endpoints, acesse o seguinte link no seu navegador (_caso rodando localmente; se no Cloud Run, substitua `localhost` pelo endereço do serviço_ ):

```sh
http://localhost:5002/docs
```

## API

### Autenticação

Todos os endpoints (exceto o raiz `/`) requerem autenticação via token JWT no header `X-Api-Key`.

#### Obter Token de Acesso

**Endpoint:** `POST /token`

Autentica um usuário e retorna um token JWT para uso nos demais endpoints.

**Requisição:**

```json
{
    "username": "string",
    "password": "string"
}
```

**Resposta:**

```json
{
    "access_token": "string",
    "token_type": "bearer"
}
```

**Exemplo de uso com Python (requests):**

```python
import requests

url = "http://0.0.0.0:5002/token"
data = {
    "username": "meu-usuario-aqui",
    "password": "minha-senha-aqui",
    "scope": "",
    "client_id": "",
    "client_secret": ""
}
headers = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

response = requests.post(url, data=data, headers=headers)
print(response.json())
# Saída esperada: {"access_token": "meu-token-aqui", "token_type": "bearer"}
```

### Prever Efetividade de Mensagem

**Endpoint:** `POST /prever_efetividade_mensagem`

Prevê a probabilidade de uma mensagem ser efetiva para um cidadão específico.

#### Requisição

```json
{
    "cidadao_id": "string",
    "linha_cuidado": "crônicos | citopatológico",
    "mensagem_tipo": "mensagem_inicial | primeiro_lembrete | segundo_lembrete",
    "mensagem": {
        "template_nome": "string (opcional)",
        "template": {
            "texto": "string",
            "botao0_texto": "string",
            "botao1_texto": "string",
            "botao2_texto": "string"
        },
        "midia_url": "string (opcional)",
        "dia_semana": "Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday",
        "horario": "number"
    }
}
```

#### Resposta

```json
{
    "mensagem": { ... },
    "probabilidade": "number",
    "erro_padrao": "number"
}
```

**Exemplo de uso com Python (requests):**

```python
import requests

url = "http://0.0.0.0:5002/prever_efetividade_mensagem"
params = {
    "cidadao_id": "meu-id-aqui",
    "linha_cuidado": "crônicos",
    "mensagem_tipo": "mensagem_inicial"
}
headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "X-Api-Key": "meu-token-aqui"
}
data = {
    "dia_semana": "Monday",
    "horario": 0,
    "template_nome": "mensageria_usuarios_citopatologico_v1",
    "midia_url": "https://storage.googleapis.com/mensageria_mvp/ma_tutoia/tutoia-%20cronicos.png"
}

response = requests.post(url, params=params, json=data, headers=headers)
print(response.json())
# Saída esperada: {"mensagem":{"dia_semana":"Monday","horario":0,"midia_url":"https://storage.googleapis.com/mensageria_mvp/ma_tutoia/tutoia-%20cronicos.png","template_nome":"mensageria_usuarios_citopatologico_v1","template":null},"probabilidade":0.0006222374275765401,"erro_padrao":0.0006264287273}
```

### Alocar Entre Mensagens

**Endpoint:** `POST /alocar`

Seleciona a melhor mensagem entre várias opções usando Thompson Sampling.

#### Requisição

```json
{
    "predicoes": [ { "mensagem": {...}, "probabilidade": "number", "erro_padrao": "number" } ],
    "mensagens": [ { ... } ]
}
```

#### Resposta

```json
{
    "mensagem": { ... },
    "probabilidade_sorteada": "number"
}
```

**Exemplo de uso com Python (requests):**

```python
import requests

url = "http://0.0.0.0:5002/alocar"
headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "X-Api-Key": "meu-token-aqui"
}
data = [
    {
        "mensagem": {
            "dia_semana": "Monday",
            "horario": 0,
            "midia_url": None,
            "template_nome": "mensageria_usuarios_citopatologico_v1",
            "template": None
        },
        "probabilidade": 0.0012320164863280504,
        "erro_padrao": 0.0007575775322684586
    },
    {
        "mensagem": {
            "dia_semana": "Monday",
            "horario": 0,
            "midia_url": "https://storage.googleapis.com/mensageria_mvp/ma_tutoia/tutoia-%20cronicos.png",
            "template_nome": "mensageria_usuarios_citopatologico_v1",
            "template": None
        },
        "probabilidade": 0.0006222374275765401,
        "erro_padrao": 0.000626428727381462
    }
]

response = requests.post(url, json=data, headers=headers)
print(response.json())
# Saída esperada: {"mensagem":{"dia_semana":"Monday","horario":0,"midia_url":null,"template_nome":"mensageria_usuarios_citopatologico_v1","template":null},"probabilidade_sorteada":2.9112283066162857e-06}
```

## Contribuindo

Este pacote está aberto para contribuições **apenas por colaboradores da ImpulsoGov**. Você pode entrar em contato com a ImpulsoGov por meio do e-mail [contato@impulsogov.org](mailto:contato@impulsogov.org).

Passo-a-passo para introduzir uma alteração:

1. Crie uma _branch_ no GitHub
2. Faça as alterações necessárias no código e comite os resultados
2. Rode `make test`
3. Rode `make lint`
4. Submeta um _pull request_

### CI/CD

O pipeline de CI/CD é configurado para rodar os testes, a análise de qualidade (lint), construir a imagem Docker e enviá-la ao Google Cloud Run automaticamente após cada push para o `main` branch.

Para que a implantação contínua com o Cloud Run funcione, você garantir que a Service Account utilizada está conectada ao GitHub por meio do Workload Identity Federation - mais informações [neste link](https://github.com/google-github-actions/auth?tab=readme-ov-file#workload-identity-federation-through-a-service-account).

Garanta também que os seguintes segredos estejam disponíveis no ambiente de CI/CD:

* `PROJECT_ID`: ID do projeto do BigQuery.
* `PROJECT_NUMBER`: Número do projeto do BigQuery.
* `IDENTITY_POOL`: ID do pool de identidade do Workload Identity Federation.
* `IDENTITY_PROVIDER`: Nome do provedor de identidade do Workload Identity Federation.
* `SERVICE_ACCOUNT`: Nome da Service Account do Cloud Run.
* `API_CHAVE`: Chave de API para autenticação no serviço.
* `ARTEFATOS_PREDICAO_URI`: URI do bucket de modelos classificadores.


## Apêndice técnico

Este pacote conceitualiza o envio de mensagens multimídia como uma instância do [Problema do Bandido de Múltiplos Braços](https://medium.com/itau-data/multi-armed-bandits-uma-alternativa-para-testes-a-b-d5db47d24006), em que tem há um número de diferentes ações, cada uma associada a uma distribuição desconhecida de possíveis recompensas. Nessa classe de problemas, o agente executa iterativamente uma ação e recebe uma recompensa numérica associada à essa ação. O objetivo é maximizar as recompensas recebidas durante as interações, ou seja, encontrar a ação que possui a maior recompensa esperada.

No cenário das mensagens de incentivo a comportamentos de cuidado, pode-se entender:

* As **recompensas** como a execução do comportamento promovido - no caso, o registro no [eSUS APS](https://sisaps.saude.gov.br/sistemas/esusaps/docs/manual/PEC/) do um procedimento ou consulta incentivado, em até 30 dias após o disparo da mensagem.
* As **ações** como o envio de uma mensagem multimídia, em um dado dia e horário escolhido.
  * Nesse caso, a escolha da melhor ação (_i.e., da melhor combinação de template de mensagem, mídia, dia e horário_) têm a dupla função de 1) maximizar a recompensa imediata (_a chance daquele usuário em particular executar o comportamento promovido_) e 2) de obter informações sobre a distribuição de probabilidades de sucesso daquela ação, permitindo melhores escolhas no futuro.

A abordagem adotada para facilitar o processo de aprendizado e entrega das melhores mensagens para os cidadãos, dentro desse referencial teórico, é descrita em detalhes nas sub-seções a seguir.

### Treinamento do algoritmo para aprendizado a partir de envios anteriores

Os resultados de envios anteriores são divididos inicialmente em um conjunto de treinamento (85%) e de teste (15%). 

Em seguida, são sorteados (com repetição) 15 reamostragens pequenos subconjuntos reamostrados com repetição a partir do conjunto de treinamento (_bootstrapping_). Cada uma dessas reamostragens é utilizada para treinar um classificador plausível o algoritmo [CatBoost](https://catboost.ai/docs/en/concepts/python-quickstart#classification).

O resultado considerado (_variável-resposta_) é uma variável binária indicando se houve o registro no prontuário local do eSUS APS de **pelo menos um** entre os comportamentos promovidos pela mensagem, em **até 30 dias após o disparo**:

* Para a linha de cuidados de **doenças crônicas não-transmissíveis** (DCNTs):
    * consulta com profissional da medicina ou enfermagem tendo como problema/condição avaliada a DCNT diagnosticada ou autorreferida (diabetes ou hipertensão), caso não haja registro de consulta durante o semestre corrente;
    * solicitação de exame de hemoglobina glicada, caso possua diabetes diagnosticada ou autorreferida e ainda não haja registro da solicitação do exame no semestre;
    * aferição da pressão arterial, caso possua hipertensão diagnosticada ou autorreferida e ainda não tenha registro de aferição no semestre.
* Para a linha de cuidados de **prevenção do câncer na mulher e no homem trans**, o registro da coleta do exame citopatológico no eSUS APS.

Já as covariáveis (_features_) utilizadas estão descritas na tabela abaixo:

<details>

<summary> <b>Tabela de covariáveis</b> (<i>clique para expandir</i>) </summary>

| Variável | Descrição | Domínio de valores aceitos |
| --- | --- | --- |
**linha_cuidado** | Linha de cuidados cujos comportamentos são promovidos | [`'crônicos'`, `'citopatológico'`] |
**cidadao_idade** | Idade em anos do cidadão, a partir da data de aniversário registrada no cadastro do eSUS APS | Número inteiro ou `null` |
**cidadao_sexo** | Sexo biológico registrado no cadastro do eSUS APS local | [`'Feminino'`, `'Masculino'`, `null`] |
**cidadao_raca_cor** | Cor/raça registrada no cadastro do eSUS APS local | [`'Amarela'`, `'Branca'`, `'Indígena'`, `'Parda'`, `'Preta'`, `null`] |
**cidadao_plano_saude_privado** | Se foi registrado uso de plano de saúde privado no cadastro do eSUS APS local | [`True`, `False`, `null`] |
**cidadao_tempo_desde_ultimo_procedimento** | Tempo desde a realização do último procedimento preventivo de rotina na linha de cuidados, em dias | Número inteiro ou `null` (se não houver registro de procedimento) |
**municipio_prop_domicilios_zona_rural** | Proporção dos domicílios particulares permanentes localizados em setores censitários rurais no município do cadastro do cidadão | `float` entre 0 e 1 ou `null` |
**mensagem_tipo** | Tipo de mensagem, quanto ao número de disparos já realizados | [`'mensagem_inicial'`, `'primeiro_lembrete'`, `'segundo_lembrete'`] |
**mensagem_dia_semana** | Dia da semana em que a mensagem foi enviada | [`'Monday'`, `'Tuesday'`, `'Wednesday'`, `'Thursday'`, `'Friday'`, `'Saturday'`, `'Sunday'`] |
**mensagem_horario_relativo_12h** | Diferença em horas entre a hora em que a mensagem foi enviada e o meio-dia (12h) | `int` ou `float` entre -12 e 12 |
**template_embedding** | Representação em 128 dimensões do texto do template de mensagem e dos botões de resposta rápida que o acompanham, gerado pelo [modelo `multimodalembedding@001` do Google](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings) | Vetor com 128 elementos `float` entre -1 e 1 |
**midia_embedding** | Representação em 128 dimensões do do vídeo ou imagem que funciona como cabeçalho da mensagem, gerado pelo [modelo `multimodalembedding@001` do Google](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings) | Vetor com 128 elementos `float` entre -1 e 1 |

</details>

### Predição de probabilidade de mensagem ser efetiva

Os quinze classificadores treinados têm seus pesos armazenados no Google Cloud Storage da ImpulsoGov e carregados em memória pelo serviço web de predição.

Quando o serviço recebe uma requisição POST autenticada e formatada corretamente no _endpoint_ `/prever_efetividade_mensagem`, ele utiliza esses pesos para calcular a probabilidade da uma mensagem ser efetiva, baseada nas características do cidadão e no contexto da mensagem fornecidos pela requisição, segundo cada um dos modelos no _ensemble_ de classificadores treinados.

O serviço não retorna as probabilidades estimadas por cada modelo individual, mas sim a probabilidade média e desvio padrão entre as diferentes predições. Esses resultados podem então ser enviados para o endpoint `/alocar`, que se encarrega de escolher uma mensagem entre as opções fornecidas. 

Para isso, o serviço usa um algoritmo de [Thompson Sampling](https://en.wikipedia.org/wiki/Thompson_sampling), que funciona sorteando uma probabilidade para cada variação de mensagem/condição de envio a partir de uma distribuição Beta(α,β) gerada a partir da média e desvio padrão dos modelos, e retornando a mensagem com a maior probabilidade sorteada. Esse algoritmo garante a minimização do [_arrependimento_](https://en.wikipedia.org/wiki/Multi-armed_bandit#:~:text=decision%20process.-,The%20regret,rewards), que é a diferença esperada entre a soma das recompensas associadas a uma estratégia ótima e a soma das recompensas obtidas.

## Licença

Este pacote está licenciado sob a [Licença MIT](LICENSE).

Copyright (c) 2026 ImpulsoGov.

[docker]: https://www.docker.com/
[fastapi]: https://fastapi.tiangolo.com/
[pytest]: https://docs.pytest.org/en/stable/
[ruff]: https://astral.sh/ruff
[uvicorn]: https://uvicorn.org/
[uv]: https://docs.astral.sh/uv/
