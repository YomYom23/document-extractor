"""Read one key from the repo's git-ignored .env, for the billed live scripts.

The value goes into the environment, where the SDKs read it; it is never printed.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def load_key_from_dotenv(key_name: str) -> None:
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.exists():
        raise SystemExit(f"No .env in the repo root: add {key_name}=... there.")
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == key_name:
            os.environ[key_name] = value.strip().strip('"')
    if not os.environ.get(key_name):
        raise SystemExit(f"{key_name} is missing or empty in .env.")
