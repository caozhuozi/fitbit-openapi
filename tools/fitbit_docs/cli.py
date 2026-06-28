from __future__ import annotations

import argparse
from pathlib import Path

from .crawler import API_DOMAINS, crawl_domain
from .generator import generate
from .live import validate_live, validate_samples
from .parser import parse_domain
from .paths import ensure_dirs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fitbit-openapi")
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl = subparsers.add_parser("crawl")
    crawl.add_argument("--domain", default="sleep")

    parse = subparsers.add_parser("parse")
    parse.add_argument("--domain", default="sleep")

    generate_cmd = subparsers.add_parser("generate")
    generate_cmd.add_argument("--domain", default="sleep")
    generate_cmd.add_argument("--version", default="0.1.0")

    validate = subparsers.add_parser("validate-live")
    validate.add_argument("--domain", default="sleep")
    validate.add_argument("--env-file", type=Path, default=Path(".env"))

    validate_samples_cmd = subparsers.add_parser("validate-samples")
    validate_samples_cmd.add_argument("--domain", default="sleep")

    all_cmd = subparsers.add_parser("all")
    all_cmd.add_argument("--domain", default="sleep")
    all_cmd.add_argument("--env-file", type=Path, default=Path(".env"))
    all_cmd.add_argument("--version", default="0.1.0")

    args = parser.parse_args(argv)
    ensure_dirs()

    if args.command == "crawl":
        domains = API_DOMAINS if args.domain == "all" else [args.domain]
        for domain in domains:
            index = crawl_domain(domain)
            print(f"crawled {len(index.endpoints)} endpoints for {domain}")
        return 0

    if args.command == "parse":
        domains = API_DOMAINS if args.domain == "all" else [args.domain]
        for domain in domains:
            endpoints = parse_domain(domain)
            print(f"parsed {len(endpoints)} endpoints for {domain}")
        return 0

    if args.command == "generate":
        generate(args.domain, version=args.version)
        print(f"generated OpenAPI files for {args.domain}")
        return 0

    if args.command == "validate-live":
        written = validate_live(args.domain, args.env_file)
        print(f"validated live representative API responses for {args.domain} and wrote {len(written)} samples")
        return 0

    if args.command == "validate-samples":
        validated = validate_samples(args.domain)
        print(f"validated {len(validated)} sanitized samples for {args.domain}")
        return 0

    if args.command == "all":
        domains = API_DOMAINS if args.domain == "all" else [args.domain]
        for domain in domains:
            index = crawl_domain(domain)
            print(f"crawled {len(index.endpoints)} endpoints for {domain}")
            endpoints = parse_domain(domain)
            print(f"parsed {len(endpoints)} endpoints for {domain}")
        generate(args.domain, version=args.version)
        print(f"generated OpenAPI files for {args.domain}")
        if args.env_file:
            written = validate_live(args.domain, args.env_file)
            print(f"validated live representative API responses for {args.domain} and wrote {len(written)} samples")
        return 0

    return 1
