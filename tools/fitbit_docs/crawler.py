from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import CrawlIndex
from .paths import RAW, ensure_dirs


BASE_URL = "https://dev.fitbit.com"
WEB_API_URL = f"{BASE_URL}/build/reference/web-api/"

API_DOMAINS = [
    "active-zone-minutes-timeseries",
    "activity",
    "activity-timeseries",
    "authorization",
    "blood-glucose",
    "body",
    "body-timeseries",
    "breathing-rate",
    "cardio-fitness-score",
    "devices",
    "electrocardiogram",
    "friends",
    "heartrate-timeseries",
    "heartrate-variability",
    "intraday",
    "irregular-rhythm-notifications",
    "nutrition",
    "nutrition-timeseries",
    "sleep",
    "spo2",
    "subscription",
    "temperature",
    "user",
]


@dataclass(frozen=True)
class Page:
    url: str
    html: str


def slug_from_url(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-")


def fetch(url: str) -> Page:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return Page(url=response.url, html=response.text)


def save_raw(domain: str, url: str, html: str) -> Path:
    ensure_dirs()
    domain_dir = RAW / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    path = domain_dir / f"{slug_from_url(url)}.html"
    path.write_text(html, encoding="utf-8")
    return path


def discover_domain_endpoints(domain: str) -> CrawlIndex:
    domain_url = urljoin(WEB_API_URL, f"{domain}/")
    page = fetch(domain_url)
    save_raw(domain, domain_url, page.html)

    soup = BeautifulSoup(page.html, "html.parser")
    prefix = f"/build/reference/web-api/{domain}/"
    endpoints: list[dict[str, str]] = []
    seen: set[str] = set()

    for anchor in soup.select(f'a[href^="{prefix}"]'):
        href = anchor.get("href", "")
        if href.rstrip("/") == prefix.rstrip("/"):
            continue
        absolute = urljoin(BASE_URL, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        endpoints.append({"title": anchor.get_text(" ", strip=True), "url": absolute})

    return CrawlIndex(domain=domain, source_url=domain_url, endpoints=endpoints)


def crawl_domain(domain: str) -> CrawlIndex:
    index = discover_domain_endpoints(domain)
    for endpoint in index.endpoints:
        page = fetch(endpoint["url"])
        save_raw(domain, endpoint["url"], page.html)
    return index


def crawl_domains(domains: list[str]) -> list[CrawlIndex]:
    return [crawl_domain(domain) for domain in domains]
