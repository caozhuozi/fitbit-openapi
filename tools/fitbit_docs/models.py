from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Parameter(BaseModel):
    name: str
    location: str = "path"
    required: bool = False
    description: str = ""


class ResponseField(BaseModel):
    name: str
    description: str = ""


class Endpoint(BaseModel):
    domain: str
    title: str
    url: str
    method: str
    path: str
    description: str = ""
    scope: str | None = None
    parameters: list[Parameter] = Field(default_factory=list)
    response_fields: list[ResponseField] = Field(default_factory=list)
    example_response: Any | None = None


class CrawlIndex(BaseModel):
    domain: str
    source_url: str
    endpoints: list[dict[str, str]]
