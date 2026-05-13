import os
from pathlib import Path


def load_env_file(path=None):
    env_path = Path(path) if path else Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    with env_path.open(encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def check_password(pw: str, env_name: str = "ADMIN_EXIT_PASSWORD") -> bool:
    expected = os.getenv(env_name)
    return bool(expected) and pw == expected


def check_management_password(pw: str) -> bool:
    return check_password(pw, "UI_ADMIN_PASSWORD")
