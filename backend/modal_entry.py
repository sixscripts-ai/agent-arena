from pathlib import Path

import modal

_BASE_DIR = Path(__file__).resolve().parent.parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_pyproject(str(Path(__file__).resolve().parent / "pyproject.toml"))
    .add_local_python_source("agent_arena")
)

app = modal.App("agent-arena-backend", image=image)


@app.function(
    secrets=[modal.Secret.from_dotenv(str(_BASE_DIR / ".env"))],
    min_containers=1,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    from agent_arena.main import app as fastapi_application

    return fastapi_application
