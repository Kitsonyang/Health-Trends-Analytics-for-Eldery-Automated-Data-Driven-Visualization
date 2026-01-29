from dataclasses import dataclass
from typing import Optional
import os

try:
    # Prefer loading .env from project root (if exists)
    from dotenv import load_dotenv  # type: ignore

    # Try loading .env from project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(project_root, '.env')

    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded environment from: {env_file}")
    else:
        load_dotenv()  # Fallback to current directory
        print("No .env file found in project root, using current directory")
except Exception as e:
    # If module is unavailable, continue with environment variables only
    print(f"Warning: Could not load .env file: {e}")
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def load_db_config() -> DBConfig:
    host = _require_env("DB_HOST")
    port_raw = _require_env("DB_PORT")
    user = _require_env("DB_USER")
    password = _require_env("DB_PASSWORD")
    database = _require_env("DB_NAME")
    try:
        port = int(port_raw)
    except Exception as e:
        raise RuntimeError(f"Invalid DB_PORT: {port_raw}") from e
    return DBConfig(host=host, port=port, user=user, password=password, database=database)


@dataclass
class PowerBIConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    workspace_id: str
    dataset_id: Optional[str] = None
    embed_url: Optional[str] = None


def load_powerbi_config() -> PowerBIConfig:
    tenant_id = _require_env("PBI_TENANT_ID")
    client_id = _require_env("PBI_CLIENT_ID")
    client_secret = _require_env("PBI_CLIENT_SECRET")
    workspace_id = _require_env("PBI_WORKSPACE_ID")
    dataset_id = os.getenv("PBI_DATASET_ID") or None
    embed_url = os.getenv("PBI_EMBED_URL") or os.getenv("VITE_PBI_EMBED_URL") or None

    print(f"PBI_TENANT_ID: {tenant_id}")
    print(f"PBI_CLIENT_ID: {client_id}")
    print(f"PBI_CLIENT_SECRET: {client_secret}")
    print(f"PBI_WORKSPACE_ID: {workspace_id}")
    print(f"PBI_DATASET_ID: {dataset_id}")

    return PowerBIConfig(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        embed_url=embed_url,
    )


