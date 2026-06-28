from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .crawler import BASE_URL, slug_from_url
from .models import Endpoint, Parameter, ResponseField
from .paths import PARSED, RAW, ensure_dirs


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_domain(domain: str) -> list[Endpoint]:
    ensure_dirs()
    raw_dir = RAW / domain
    endpoints: list[Endpoint] = []
    for path in sorted(raw_dir.glob("*.html")):
        if path.stem == domain:
            continue
        endpoint = parse_endpoint_file(domain, path)
        if endpoint.method and endpoint.path:
            endpoints.append(endpoint)

    out_dir = PARSED / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    for endpoint in endpoints:
        out = out_dir / f"{slug_from_url(endpoint.url)}.json"
        out.write_text(endpoint.model_dump_json(indent=2), encoding="utf-8")
    return endpoints


def parse_endpoint_file(domain: str, path: Path) -> Endpoint:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    canonical = soup.select_one('meta[property="og:url"]')
    url = canonical.get("content", "") if canonical else urljoin(BASE_URL, f"/build/reference/web-api/{domain}/{path.stem}/")

    title = clean_text(soup.find("h1").get_text(" ", strip=True)) if soup.find("h1") else path.stem
    article = soup.find("article") or soup

    description = first_description(article)
    scope = parse_scope(article)
    method, api_path = parse_request_line(article)
    parameters = parse_parameters(article)
    response_fields = parse_response_fields(article)
    example = parse_example_response(article)

    return Endpoint(
        domain=domain,
        title=title,
        url=url,
        method=method,
        path=api_path,
        description=description,
        scope=scope,
        parameters=parameters,
        response_fields=response_fields,
        example_response=example,
    )


def first_description(article: Tag) -> str:
    parts: list[str] = []
    for node in article.find_all(["p", "hr"], recursive=False):
        if node.name == "hr":
            break
        text = clean_text(node.get_text(" ", strip=True))
        if text and not text.lower().startswith("scope:"):
            parts.append(text)
    return "\n\n".join(parts)


def parse_scope(article: Tag) -> str | None:
    text = article.get_text(" ", strip=True)
    match = re.search(r"Scope:\s*([a-zA-Z0-9_ -]+)", text)
    if not match:
        return None
    return clean_text(match.group(1)).split()[0]


def parse_request_line(article: Tag) -> tuple[str, str]:
    request_heading = article.find(id="Request")
    if not request_heading:
        return "", ""

    table = request_heading.find_next("table")
    if not table:
        return "", ""

    cells = [clean_text(cell.get_text(" ", strip=True)) for cell in table.find_all("td")]
    methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    method = next((cell for cell in cells if cell in methods), "")
    path = next((cell for cell in cells if cell.startswith("/")), "")
    match = re.search(r"(/\S+?\.json)", path)
    if match:
        path = match.group(1)
    path = path.replace("[user-id]", "{user-id}")
    path = re.sub(r"\[([A-Za-z0-9_-]+)\]", r"{\1}", path)
    return method.lower(), path


def parse_parameters(article: Tag) -> list[Parameter]:
    parameters: list[Parameter] = []
    for label in article.find_all(string=re.compile(r"URI Arguments|Query Parameters|Body Parameters")):
        table = label.find_parent().find_next("table") if label.find_parent() else None
        if not table:
            continue
        location = "path" if "URI" in str(label) else "query"
        for row in table.find_all("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
            if len(cells) < 3 or cells[0].lower() in {"name", "parameter"}:
                continue
            parameters.append(
                Parameter(
                    name=cells[0],
                    location=location,
                    required="required" in cells[1].lower(),
                    description=cells[2],
                )
            )
    return parameters


def parse_response_fields(article: Tag) -> list[ResponseField]:
    heading = article.find(id="Response")
    if not heading:
        return []
    fields: list[ResponseField] = []
    for table in heading.find_all_next("table"):
        previous_heading = table.find_previous(["h2", "h3"])
        if previous_heading and previous_heading.get("id") == "Additional-Information":
            break
        for row in table.find_all("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
            if len(cells) == 2 and ":" in cells[0]:
                fields.append(ResponseField(name=cells[0], description=cells[1]))
    return fields


def parse_example_response(article: Tag):
    response_heading = article.find(id="Response")
    if not response_heading:
        return None
    pre = response_heading.find_next("pre")
    if not pre:
        return None
    text = html.unescape(pre.get_text("\n", strip=False))
    text = text.replace("\u00a0", " ")
    text = re.sub(r"^\s*\.\s*", "", text, flags=re.MULTILINE)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
