"""Typer CLI — management commands for DocSprint.

Commands:
    server  — Start the FastAPI development server
    worker  — Start the RQ document processing worker
    migrate — Run Alembic migrations
"""

from __future__ import annotations

import subprocess
import sys

import typer

app = typer.Typer(
    name="docsprint",
    help="DocSprint — AI Document Processing SaaS CLI",
)


@app.command()
def server(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
) -> None:
    """Start the FastAPI development server."""
    import uvicorn

    uvicorn.run(
        "docsprint.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def worker(
    url: str = typer.Option(None, help="Redis URL"),
    queues: str = typer.Option("doc-processing", help="Queue names (comma-separated)"),
) -> None:
    """Start the RQ document processing worker."""
    from docsprint.config import settings

    redis_url = url or settings.REDIS_URL
    typer.echo(f"Starting worker on queue '{queues}' at {redis_url}")
    typer.echo("Loading VL model on first job...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rq",
            "worker",
            *queues.split(","),
            "--url",
            redis_url,
        ],
        check=True,
    )


@app.command()
def migrate(
    message: str = typer.Option("auto", help="Migration message"),
    autogenerate: bool = typer.Option(True, help="Auto-generate from models"),
) -> None:
    """Run database migrations."""
    import os
    import subprocess


    # Determine alembic.ini location relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    alembic_ini = os.path.join(project_root, "alembic.ini")

    if autogenerate:
        typer.echo(f"Generating migration: {message}")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                alembic_ini,
                "revision",
                "--autogenerate",
                "-m",
                message,
            ],
            check=True,
        )

    typer.echo("Running migrations...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            alembic_ini,
            "upgrade",
            "head",
        ],
        check=True,
    )
    typer.echo("Migrations complete.")


@app.command()
def shell() -> None:
    """Open an interactive Python shell with the app context loaded."""
    import code

    banner = """
    DocSprint Interactive Shell
    Available:
      from docsprint.database import SyncSessionLocal
      from docsprint.models import User, Document, Job, UsageRecord
      from docsprint.config import settings
    """
    code.interact(banner=banner, local=globals())


if __name__ == "__main__":
    app()