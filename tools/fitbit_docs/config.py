from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Credentials:
    client_id: str
    client_secret: str
    redirect_url: str
    refresh_token: str


ENV_KEYS = {
    "client_id": "FITBIT_CLIENT_ID",
    "client_secret": "FITBIT_CLIENT_SECRET",
    "redirect_url": "FITBIT_REDIRECT_URL",
    "refresh_token": "FITBIT_REFRESH_TOKEN",
}


def load_credentials(env_file: Path | None = None) -> Credentials:
    values = {}
    if env_file and env_file.exists():
        values.update(read_env_file(env_file))

    for key in ENV_KEYS.values():
        if os.environ.get(key):
            values[key] = os.environ[key]

    missing = [key for key in ENV_KEYS.values() if not values.get(key)]
    if missing:
        source = str(env_file) if env_file else "environment"
        raise ValueError(f"Missing required Fitbit config in {source}: {', '.join(missing)}")

    return Credentials(
        client_id=values[ENV_KEYS["client_id"]],
        client_secret=values[ENV_KEYS["client_secret"]],
        redirect_url=values[ENV_KEYS["redirect_url"]],
        refresh_token=values[ENV_KEYS["refresh_token"]],
    )


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = unquote(value.strip())
    return values


def save_refresh_token(env_file: Path | None, old_token: str, new_token: str) -> None:
    if not env_file or not new_token or new_token == old_token:
        return

    values = read_env_file(env_file) if env_file.exists() else {}
    values["FITBIT_REFRESH_TOKEN"] = new_token
    write_env_file(env_file, values)


def write_env_file(path: Path, values: dict[str, str]) -> None:
    ordered_keys = [
        "FITBIT_CLIENT_ID",
        "FITBIT_CLIENT_SECRET",
        "FITBIT_REDIRECT_URL",
        "FITBIT_REFRESH_TOKEN",
    ]
    lines = []
    for key in ordered_keys:
        if key in values:
            lines.append(f"{key}={quote(values[key])}")
    for key in sorted(k for k in values if k not in ordered_keys):
        lines.append(f"{key}={quote(values[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def quote(value: str) -> str:
    if any(ch.isspace() for ch in value) or "#" in value:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value
