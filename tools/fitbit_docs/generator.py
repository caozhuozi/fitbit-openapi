from __future__ import annotations

import json
import copy
import re
from pathlib import Path
from typing import Any

import yaml

from .models import Endpoint
from .crawler import API_DOMAINS
from .paths import COMPONENTS, PARSED, PATHS, ROOT, SCHEMAS, ensure_dirs


def load_parsed(domain: str) -> list[Endpoint]:
    parsed_dir = PARSED / domain
    endpoints: list[Endpoint] = []
    for path in sorted(parsed_dir.glob("*.json")):
        endpoints.append(Endpoint.model_validate_json(path.read_text(encoding="utf-8")))
    return endpoints


def generate(domain: str, version: str = "0.1.0") -> None:
    ensure_dirs()
    domains = API_DOMAINS if domain == "all" else [domain]
    write_security()
    schemas = write_sleep_schemas()
    paths: dict[str, Any] = {}
    seen_operations: set[tuple[str, str]] = set()
    for current_domain in domains:
        endpoints = load_parsed(current_domain)
        if not endpoints:
            continue
        domain_paths = write_domain_paths(current_domain, endpoints, seen_operations)
        merge_paths(paths, domain_paths)
    write_root_openapi(paths=paths, schemas=qualify_component_refs(schemas), version=version)


def write_root_openapi(
    paths: dict[str, Any] | None = None,
    schemas: dict[str, Any] | None = None,
    version: str = "0.1.0",
) -> None:
    root = {
        "openapi": "3.1.0",
        "info": {
            "title": "Fitbit Web API (Legacy)",
            "version": version,
            "license": {
                "name": "Fitbit API Terms",
                "url": "https://dev.fitbit.com/legal/platform-terms-of-service/",
            },
            "description": (
                "OpenAPI specification for the Fitbit Web API (Legacy). "
                "The official Fitbit documentation states that the Fitbit "
                "Web API (Legacy) will be deprecated in September 2026."
            ),
        },
        "servers": [{"url": "https://api.fitbit.com"}],
        "security": [{"fitbitOAuth": []}],
        "paths": paths or {},
        "components": {
            "securitySchemes": {
                "fitbitOAuth": {
                    "type": "oauth2",
                    "flows": {
                        "authorizationCode": {
                            "authorizationUrl": "https://www.fitbit.com/oauth2/authorize",
                            "tokenUrl": "https://api.fitbit.com/oauth2/token",
                            "scopes": {
                                "sleep": "Read and write sleep data",
                                "activity": "Read and write activity data",
                                "heartrate": "Read heart rate data",
                                "profile": "Read profile data",
                                "weight": "Read and write weight data",
                                "nutrition": "Read and write nutrition data",
                                "settings": "Read settings",
                                "social": "Read social data",
                                "respiratory_rate": "Read breathing rate data",
                                "temperature": "Read temperature data",
                                "oxygen_saturation": "Read oxygen saturation data",
                                "cardio_fitness": "Read cardio fitness data",
                                "electrocardiogram": "Read electrocardiogram data",
                                "irregular_rhythm_notifications": "Read irregular rhythm notifications data",
                            },
                        }
                    },
                }
            },
            "schemas": schemas or {},
        },
    }
    write_yaml(ROOT / "openapi.yaml", root)


def write_security() -> None:
    write_yaml(
        COMPONENTS / "security.yaml",
        {
            "fitbitOAuth": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://www.fitbit.com/oauth2/authorize",
                        "tokenUrl": "https://api.fitbit.com/oauth2/token",
                        "scopes": {
                            "sleep": "Read and write sleep data",
                            "activity": "Read and write activity data",
                            "heartrate": "Read heart rate data",
                            "profile": "Read profile data",
                            "weight": "Read and write weight data",
                            "nutrition": "Read and write nutrition data",
                            "settings": "Read settings",
                            "social": "Read social data",
                            "respiratory_rate": "Read breathing rate data",
                            "temperature": "Read temperature data",
                            "oxygen_saturation": "Read oxygen saturation data",
                            "cardio_fitness": "Read cardio fitness data",
                            "electrocardiogram": "Read electrocardiogram data",
                            "irregular_rhythm_notifications": "Read irregular rhythm notifications data",
                        },
                    }
                },
            }
        },
    )


def write_sleep_schemas() -> dict[str, Any]:
    schemas = {
        "SleepResponse": {
            "type": "object",
            "properties": {
                "sleep": {"type": "array", "items": {"$ref": "#/SleepRecord"}},
                "summary": {"$ref": "#/SleepSummary"},
                "meta": {"type": "object", "additionalProperties": True},
            },
            "additionalProperties": True,
        },
        "SleepRecord": {
            "type": "object",
            "properties": {
                "dateOfSleep": {"type": "string", "format": "date"},
                "duration": {"type": "integer"},
                "efficiency": {"type": "integer"},
                "endTime": {"type": "string"},
                "infoCode": {"type": "integer"},
                "isMainSleep": {"type": "boolean"},
                "levels": {"$ref": "#/SleepLevels"},
                "logId": {"type": "integer"},
                "logType": {"type": "string"},
                "minutesAfterWakeup": {"type": "integer"},
                "minutesAsleep": {"type": "integer"},
                "minutesAwake": {"type": "integer"},
                "minutesToFallAsleep": {"type": "integer"},
                "startTime": {"type": "string"},
                "timeInBed": {"type": "integer"},
                "type": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "SleepLevels": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "items": {"$ref": "#/SleepLevelData"}},
                "shortData": {"type": "array", "items": {"$ref": "#/SleepLevelData"}},
                "summary": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/SleepStageSummary"},
                },
            },
            "additionalProperties": True,
        },
        "SleepLevelData": {
            "type": "object",
            "properties": {
                "dateTime": {"type": "string"},
                "level": {"type": "string"},
                "seconds": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "SleepStageSummary": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "minutes": {"type": "integer"},
                "thirtyDayAvgMinutes": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "SleepSummary": {
            "type": "object",
            "properties": {
                "stages": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
                "totalMinutesAsleep": {"type": "integer"},
                "totalSleepRecords": {"type": "integer"},
                "totalTimeInBed": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "FitbitErrorResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "errors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "errorType": {"type": "string"},
                            "fieldName": {"type": "string"},
                            "message": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                },
            },
            "additionalProperties": True,
        },
    }
    write_yaml(SCHEMAS / "sleep.yaml", schemas)
    return schemas


def write_domain_paths(domain: str, endpoints: list[Endpoint], seen_operations: set[tuple[str, str]] | None = None) -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for endpoint in endpoints:
        normalized = normalized_path_shape(endpoint.path)
        key = (endpoint.method, normalized)
        if seen_operations is not None and key in seen_operations:
            continue
        if seen_operations is not None:
            seen_operations.add(key)

        operation: dict[str, Any] = {
            "operationId": operation_id(endpoint),
            "summary": endpoint.title,
            "description": endpoint.description or endpoint.title,
            "tags": [domain.title()],
            "x-fitbit-doc-url": endpoint.url,
            "parameters": operation_parameters(endpoint),
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": response_schema_for(endpoint),
                        }
                    },
                },
                "400": {
                    "description": "Fitbit API error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/FitbitErrorResponse"}
                        }
                    },
                },
            },
        }
        if endpoint.scope:
            operation["security"] = [{"fitbitOAuth": [endpoint.scope]}]
        if endpoint.example_response is not None:
            operation["responses"]["200"]["content"]["application/json"]["example"] = endpoint.example_response

        paths.setdefault(endpoint.path, {})[endpoint.method] = operation

    write_yaml(PATHS / f"{domain}.yaml", paths)
    return paths


def merge_paths(target: dict[str, Any], source: dict[str, Any]) -> None:
    for path, operations in source.items():
        target.setdefault(path, {}).update(operations)


def normalized_path_shape(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def operation_parameters(endpoint: Endpoint) -> list[dict[str, Any]]:
    placeholders = re.findall(r"\{([^}]+)\}", endpoint.path)
    by_name = {parameter.name: parameter for parameter in endpoint.parameters}
    rendered: list[dict[str, Any]] = []

    for name in placeholders:
        parameter = by_name.get(name)
        description = parameter.description if parameter else ""
        rendered.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "description": description,
                "schema": parameter_schema(name),
            }
        )

    for parameter in endpoint.parameters:
        if parameter.location == "path":
            continue
        rendered.append(parameter_to_openapi(parameter))

    return rendered


def parameter_to_openapi(parameter) -> dict[str, Any]:
    schema = parameter_schema(parameter.name)
    return {
        "name": parameter.name,
        "in": parameter.location,
        "required": parameter.required or parameter.location == "path",
        "description": parameter.description,
        "schema": schema,
    }


def parameter_schema(name: str) -> dict[str, str]:
    schema = {"type": "string"}
    if "date" in name.lower():
        schema["format"] = "date"
    return schema


def response_schema_for(endpoint: Endpoint) -> dict[str, Any]:
    if endpoint.domain == "sleep":
        if "goal" in endpoint.path or (endpoint.method == "post" and endpoint.path.endswith("/sleep.json")):
            return {}
        return {"$ref": "#/components/schemas/SleepResponse"}
    return {}


def qualify_component_refs(value: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(value)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/") and not ref.startswith("#/components/"):
                node["$ref"] = "#/components/schemas/" + ref.removeprefix("#/")
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(copied)
    return copied


def operation_id(endpoint: Endpoint) -> str:
    raw = f"{endpoint.domain} {endpoint.method} {endpoint.title} {endpoint.path}"
    words = "".join(ch if ch.isalnum() else " " for ch in raw).title().replace(" ", "")
    if not words:
        words = endpoint.method.title()
    return words[0].lower() + words[1:]


def write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_schema(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
