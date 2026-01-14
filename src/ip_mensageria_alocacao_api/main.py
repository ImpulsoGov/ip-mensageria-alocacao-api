from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from ip_mensageria_alocacao_api import routes
from ip_mensageria_alocacao_api.core.classificadores import carregar_classificadores


def create_app() -> FastAPI:
    """Create a FastAPI application."""

    app = FastAPI()

    # Set all CORS enabled origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Carregar classificadores na inicialização para evitar timeouts
    app.state.classificadores = carregar_classificadores()

    app.include_router(routes.router)
    return app


app = create_app()
