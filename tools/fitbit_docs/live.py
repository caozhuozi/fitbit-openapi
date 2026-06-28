from __future__ import annotations

import base64
import copy
from pathlib import Path
from typing import Any

import requests
import yaml
from jsonschema import Draft202012Validator, RefResolver

from .config import load_credentials, save_refresh_token
from .generator import dump_json
from .paths import SAMPLES, SCHEMAS, ensure_dirs


TOKEN_URL = "https://api.fitbit.com/oauth2/token"
API_BASE = "https://api.fitbit.com"


def refresh_access_token(env_file: Path | None) -> str:
    creds = load_credentials(env_file)
    basic = base64.b64encode(f"{creds.client_id}:{creds.client_secret}".encode()).decode()
    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": creds.refresh_token},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    save_refresh_token(env_file, creds.refresh_token, payload.get("refresh_token", ""))
    return payload["access_token"]


def validate_sleep_live(env_file: Path | None) -> list[Path]:
    ensure_dirs()
    access_token = refresh_access_token(env_file)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    calls = {
        "sleep-date-range": f"{API_BASE}/1.2/user/-/sleep/date/2026-06-01/2026-06-23.json",
        "sleep-single-date": f"{API_BASE}/1.2/user/-/sleep/date/2026-06-23.json",
        "sleep-log-list": f"{API_BASE}/1.2/user/-/sleep/list.json?beforeDate=2026-06-28&sort=desc&offset=0&limit=10",
        "sleep-goal": f"{API_BASE}/1.2/user/-/sleep/goal.json",
    }

    schema_doc = yaml.safe_load((SCHEMAS / "sleep.yaml").read_text(encoding="utf-8"))
    sleep_schema = schema_doc["SleepResponse"]
    resolver = RefResolver.from_schema(schema_doc)
    validator = Draft202012Validator(sleep_schema, resolver=resolver)

    written: list[Path] = []
    for name, url in calls.items():
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        sanitized = sanitize(payload)
        out = SAMPLES / f"{name}.json"
        dump_json(out, sanitized)
        written.append(out)

        if name.startswith("sleep-") and name != "sleep-goal":
            validator.validate(sanitized)

    return written


def validate_all_live(env_file: Path | None) -> list[Path]:
    ensure_dirs()
    access_token = refresh_access_token(env_file)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    date = "2026-06-23"

    calls = {
        "user-profile": f"{API_BASE}/1/user/-/profile.json",
        "user-badges": f"{API_BASE}/1/user/-/badges.json",
        "devices": f"{API_BASE}/1/user/-/devices.json",
        "activity-daily-summary": f"{API_BASE}/1/user/-/activities/date/{date}.json",
        "activity-goals-daily": f"{API_BASE}/1/user/-/activities/goals/daily.json",
        "heart-rate-timeseries": f"{API_BASE}/1/user/-/activities/heart/date/{date}/1d.json",
        "body-weight-log": f"{API_BASE}/1/user/-/body/log/weight/date/{date}.json",
        "body-fat-log": f"{API_BASE}/1/user/-/body/log/fat/date/{date}.json",
        "breathing-rate": f"{API_BASE}/1/user/-/br/date/{date}.json",
        "spo2": f"{API_BASE}/1/user/-/spo2/date/{date}.json",
        "temperature-core": f"{API_BASE}/1/user/-/temp/core/date/{date}.json",
        "temperature-skin": f"{API_BASE}/1/user/-/temp/skin/date/{date}.json",
        "cardio-fitness-score": f"{API_BASE}/1/user/-/cardioscore/date/{date}.json",
        "nutrition-food-log": f"{API_BASE}/1/user/-/foods/log/date/{date}.json",
        "nutrition-water-log": f"{API_BASE}/1/user/-/foods/log/water/date/{date}.json",
    }

    written: list[Path] = []
    for name, url in calls.items():
        response = requests.get(url, headers=headers, timeout=30)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        sanitized = sanitize({"status": response.status_code, "body": payload})
        out = SAMPLES / f"{name}.json"
        dump_json(out, sanitized)
        written.append(out)

        if response.status_code in {401, 403}:
            response.raise_for_status()

    return written


def validate_sleep_samples() -> list[Path]:
    schema_doc = yaml.safe_load((SCHEMAS / "sleep.yaml").read_text(encoding="utf-8"))
    sleep_schema = schema_doc["SleepResponse"]
    resolver = RefResolver.from_schema(schema_doc)
    validator = Draft202012Validator(sleep_schema, resolver=resolver)

    validated: list[Path] = []
    for path in sorted(SAMPLES.glob("sleep-*.json")):
        if path.stem == "sleep-goal":
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        validator.validate(payload)
        validated.append(path)
    return validated


def sanitize(value: Any) -> Any:
    copied = copy.deepcopy(value)
    scrub(copied)
    return copied


def scrub(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value.keys()):
            lowered = key.lower()
            if lowered in {
                "access_token",
                "refresh_token",
                "token",
                "userid",
                "user_id",
                "encodedid",
                "fullname",
                "firstname",
                "lastname",
                "displayname",
                "avatar",
                "avatar150",
                "email",
            }:
                value[key] = "<redacted>"
            elif lowered in {"logid", "log_id"}:
                value[key] = 0
            else:
                scrub(value[key])
    elif isinstance(value, list):
        for item in value:
            scrub(item)
