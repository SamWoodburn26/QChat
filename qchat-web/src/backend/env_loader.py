from pathlib import Path

from dotenv import load_dotenv


def load_backend_env() -> None:
    """Load project-level .env files for local Azure Functions runs."""
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent.parent

    candidates = [
        project_root / '.env',
        project_root / '.env.local',
        backend_dir / '.env',
        backend_dir / '.env.local',
    ]

    for env_path in candidates:
        if env_path.is_file():
            load_dotenv(env_path, override=False)


load_backend_env()
