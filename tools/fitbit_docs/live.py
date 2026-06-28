from __future__ import annotations

import base64
import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml
from jsonschema import Draft202012Validator, RefResolver, ValidationError

from .config import load_credentials, save_refresh_token
from .generator import dump_json
from .paths import ROOT, SAMPLES, ensure_dirs


TOKEN_URL = "https://api.fitbit.com/oauth2/token"
API_BASE = "https://api.fitbit.com"
SAMPLE_DATE = "2026-06-23"


@dataclass(frozen=True)
class LiveCall:
    domain: str
    name: str
    url: str
    method: str
    openapi_path: str


LIVE_CALLS = [
    LiveCall("user", "user-profile", f"{API_BASE}/1/user/-/profile.json", "get", "/1/user/{user-id}/profile.json"),
    LiveCall("user", "user-badges", f"{API_BASE}/1/user/-/badges.json", "get", "/1/user/{user-id}/badges.json"),
    LiveCall("devices", "devices", f"{API_BASE}/1/user/-/devices.json", "get", "/1/user/{user-id}/devices.json"),
    LiveCall("activity", "activity-daily-summary", f"{API_BASE}/1/user/-/activities/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/activities/date/{date}.json"),
    LiveCall("activity", "activity-goals-daily", f"{API_BASE}/1/user/-/activities/goals/daily.json", "get", "/1/user/{user-id}/activities/goals/daily.json"),
    LiveCall("heartrate-timeseries", "heart-rate-timeseries", f"{API_BASE}/1/user/-/activities/heart/date/{SAMPLE_DATE}/1d.json", "get", "/1/user/{user-id}/activities/heart/date/{date}/1d.json"),
    LiveCall("body", "body-weight-log", f"{API_BASE}/1/user/-/body/log/weight/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/body/log/weight/date/{date}.json"),
    LiveCall("body", "body-fat-log", f"{API_BASE}/1/user/-/body/log/fat/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/body/log/fat/date/{date}.json"),
    LiveCall("breathing-rate", "breathing-rate", f"{API_BASE}/1/user/-/br/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/br/date/{date}.json"),
    LiveCall("spo2", "spo2", f"{API_BASE}/1/user/-/spo2/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/spo2/date/{date}.json"),
    LiveCall("temperature", "temperature-core", f"{API_BASE}/1/user/-/temp/core/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/temp/core/date/{date}.json"),
    LiveCall("temperature", "temperature-skin", f"{API_BASE}/1/user/-/temp/skin/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/temp/skin/date/{date}.json"),
    LiveCall("cardio-fitness-score", "cardio-fitness-score", f"{API_BASE}/1/user/-/cardioscore/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/cardioscore/date/{date}.json"),
    LiveCall("nutrition", "nutrition-food-log", f"{API_BASE}/1/user/-/foods/log/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/foods/log/date/{date}.json"),
    LiveCall("nutrition", "nutrition-water-log", f"{API_BASE}/1/user/-/foods/log/water/date/{SAMPLE_DATE}.json", "get", "/1/user/{user-id}/foods/log/water/date/{date}.json"),
    LiveCall("sleep", "sleep-date-range", f"{API_BASE}/1.2/user/-/sleep/date/2026-06-01/{SAMPLE_DATE}.json", "get", "/1.2/user/{user-id}/sleep/date/{base-date}/{end-date}.json"),
    LiveCall("sleep", "sleep-single-date", f"{API_BASE}/1.2/user/-/sleep/date/{SAMPLE_DATE}.json", "get", "/1.2/user/{user-id}/sleep/date/{date}.json"),
    LiveCall("sleep", "sleep-log-list", f"{API_BASE}/1.2/user/-/sleep/list.json?beforeDate=2026-06-28&sort=desc&offset=0&limit=10", "get", "/1.2/user/{user-id}/sleep/list.json"),
    LiveCall("sleep", "sleep-goal", f"{API_BASE}/1.2/user/-/sleep/goal.json", "get", "/1.2/user/{user-id}/sleep/goal.json"),
]


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


def validate_live(domain: str, env_file: Path | None) -> list[Path]:
    ensure_dirs()
    access_token = refresh_access_token(env_file)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    calls = live_calls_for_domain(domain)
    validators = response_validators(calls)

    written: list[Path] = []
    for call in calls:
        response = requests.get(call.url, headers=headers, timeout=30)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.status_code in {401, 403}:
            response.raise_for_status()

        sanitized = sanitize({"status": response.status_code, "body": payload})
        out = SAMPLES / f"{call.name}.json"
        dump_json(out, sanitized)
        written.append(out)

        validator = validators.get(call.name)
        if validator is not None and 200 <= response.status_code < 300:
            validate_response_payload(validator, sanitized["body"])

    return written


def validate_samples(domain: str) -> list[Path]:
    calls = live_calls_for_domain(domain)
    validators = response_validators(calls)

    validated: list[Path] = []
    for call in calls:
        path = SAMPLES / f"{call.name}.json"
        if not path.exists():
            continue
        validator = validators.get(call.name)
        if validator is None:
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        body = payload.get("body", payload) if isinstance(payload, dict) else payload
        validate_response_payload(validator, body)
        validated.append(path)
    return validated


def validate_response_payload(validator: Draft202012Validator, payload: Any) -> None:
    try:
        validator.validate(payload)
    except ValidationError as error:
        if isinstance(payload, list):
            for item in payload:
                validator.validate(item)
            return
        raise error


def live_calls_for_domain(domain: str) -> list[LiveCall]:
    if domain == "all":
        return LIVE_CALLS
    calls = [call for call in LIVE_CALLS if call.domain == domain]
    if not calls:
        supported = ", ".join(sorted({call.domain for call in LIVE_CALLS}))
        raise ValueError(f"live validation has no representative calls for domain {domain!r}; supported domains: all, {supported}")
    return calls


def response_validators(calls: list[LiveCall]) -> dict[str, Draft202012Validator]:
    openapi = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))
    resolver = RefResolver.from_schema(openapi)
    validators: dict[str, Draft202012Validator] = {}
    for call in calls:
        media_type = (
            openapi.get("paths", {})
            .get(call.openapi_path, {})
            .get(call.method, {})
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
        )
        schema = media_type.get("schema")
        if schema:
            validators[call.name] = Draft202012Validator(schema, resolver=resolver)
    return validators


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
                "id",
                "mac",
                "serialnumber",
            }:
                value[key] = "<redacted>"
            elif lowered in {"logid", "log_id"}:
                value[key] = 0
            elif isinstance(value[key], dict):
                scrub(value[key])
            elif isinstance(value[key], list):
                scrub(value[key])
            else:
                value[key] = sanitized_scalar(lowered, value[key])
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, (dict, list)):
                scrub(item)
            else:
                value[index] = sanitized_scalar("", item)


def sanitized_scalar(key: str, value: Any) -> Any:
    if key == "status" and isinstance(value, int):
        return value
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    if isinstance(value, str):
        if "date" in key and "time" not in key:
            return "2026-01-01"
        if "time" in key:
            return "2026-01-01T00:00:00.000"
        return "<redacted>"
    return None
