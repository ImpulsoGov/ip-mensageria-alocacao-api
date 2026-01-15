# ============================
# Configurações padrão
# ============================

PYTHON_VERSION ?= 3.13
IMAGE_NAME ?= ip-mensageria-alocacao-api
REGION ?= us-central1
SERVICE_NAME ?= ip-mensageria-alocacao-api
JWT_ALGORITMO ?= HS256
TOKEN_VALIDADE_MINUTOS ?= 5256000000
BQ_PROJETO ?= $(PROJECT_ID)
ARTEFATOS_PREDICAO_URI ?=
REGISTRY_REPOSITORY ?= $(IMAGE_NAME)
IMAGE_TAG ?= latest
IMAGE_URI := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REGISTRY_REPOSITORY)/$(IMAGE_NAME):$(IMAGE_TAG)
API_CHAVE_SECRET ?= API_CHAVE:latest

IMAGE_URI := gcr.io/$(PROJECT_ID)/$(IMAGE_NAME)
DOCKERFILE := dockerfiles/python313/Dockerfile

PORT ?= 8080

# ============================
# Ajuda
# ============================

help:
	@echo ""
	@echo "Comandos disponíveis:"
	@echo ""
	@echo "  setup-local        Cria .venv e instala dependências (uv)"
	@echo "  run-local          Roda API localmente (uvicorn)"
	@echo "  run-container      Roda API em container Docker"
	@echo "  kill-container     Para containers docker-compose"
	@echo ""
	@echo "  test               Executa testes (pytest)"
	@echo "  lint               Ruff  mypy"
	@echo "  dep-update         Atualiza dependências (uv)"
	@echo ""
	@echo "  docker-build       Build da imagem Docker"
	@echo "  docker-push        Push da imagem para GCR"
	@echo "  deploy-cloudrun    Deploy no Google Cloud Run"
	@echo ""

# ============================
# Desenvolvimento local
# ============================

setup-local:
	uv venv --python $(PYTHON_VERSION)
	uv pip install -e .

run-local:
	uv run uvicorn ip_mensageria_alocacao_api.main:app \
		--host 0.0.0.0 \
		--port 5002 \
		--reload

# ============================
# Containers
# ============================

run-container:
	docker build -f $(DOCKERFILE) -t $(IMAGE_NAME):local .
	docker run --rm \
		-p 5002:$(PORT) \
		--env-file .env \
		-e PORT=$(PORT) \
 		-e GOOGLE_ARQUIVO_CREDENCIAIS=/app/credentials.json \
 		-v $$(pwd)/credentials.json:/app/credentials.json \
		$(IMAGE_NAME):local

kill-container:
	docker ps -q --filter "ancestor=$(IMAGE_NAME):local" | xargs -r docker stop

# ============================
# Qualidade
# ============================

test:
	uv run pytest

lint:
	uv run ruff check --fix ./src
	uv run ruff format ./src
	uv run mypy ./src

dep-update:
	bash bin/update_deps.sh

# ============================
# Build & Deploy
# ============================

docker-login:
	gcloud auth configure-docker $(REGION)-docker.pkg.dev --quiet

docker-build:
	docker build -f $(DOCKERFILE) -t $(IMAGE_URI) .

docker-push: docker-login
	docker push $(IMAGE_URI)

deploy-cloudrun: docker-build docker-push
	gcloud run deploy $(SERVICE_NAME) \
		--image $(IMAGE_URI) \
		--region $(REGION) \
		--platform managed \
		--allow-unauthenticated \
		--port $(PORT) \
		--set-env-vars JWT_ALGORITMO=$(JWT_ALGORITMO),TOKEN_VALIDADE_MINUTOS=$(TOKEN_VALIDADE_MINUTOS),BQ_PROJETO=$(BQ_PROJETO),ARTEFATOS_PREDICAO_URI=$(ARTEFATOS_PREDICAO_URI) \
		--set-secrets API_CHAVE=$(API_CHAVE_SECRET)

# ============================
# Limpeza
# ============================

clean:
	rm -rf .venv