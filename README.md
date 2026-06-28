# Fitbit OpenAPI

OpenAPI 3.1 specification project for the Fitbit Web API (Legacy).

The source of truth is the official Fitbit Web API documentation:

```text
https://dev.fitbit.com/build/reference/web-api/
```

This project crawls the official documentation, stores auditable intermediate data, generates modular OpenAPI YAML, and validates generated schemas against live Fitbit API responses where credentials and scopes are available.

Fitbit's documentation currently notes that the Fitbit Web API (Legacy) will be deprecated in September 2026. This specification describes that legacy API surface.

## Quick Start

```bash
make install
make crawl
make parse
make generate
cp .env.example .env
make validate-live
make validate
```

## Layout

```text
openapi.yaml             Main OpenAPI entrypoint
paths/                   Modular OpenAPI path files
components/              Reusable OpenAPI components
dist/                    Bundled OpenAPI output
data/raw/                Raw official documentation HTML
data/parsed/             Parsed endpoint JSON
data/samples/sanitized/  Sanitized live API samples
tools/fitbit_docs/       Maintenance tools: crawler, parser, generator, validators
```

## Using the Specification

If you only want the OpenAPI file, use the bundled spec:

```text
dist/fitbit-openapi.yaml
```

The root `openapi.yaml`, `paths/`, and `components/` files are the modular source form used for maintenance. The `dist/` file is the single-file bundle intended for tools that expect one OpenAPI document.

For stable versions, GitHub Releases are a good place to attach the bundled file as a release asset. The committed `dist/fitbit-openapi.yaml` can represent the latest version on the main branch, while releases can preserve versioned snapshots.

## Release

Create a local release artifact with:

```bash
make release VERSION=0.1.0
```

`VERSION` is required for release targets.

This target generates the OpenAPI files with the requested spec version, validates samples, runs Redocly lint and bundle, then writes:

```text
release/fitbit-openapi-0.1.0.yaml
release/fitbit-openapi-0.1.0.yaml.sha256
```

Attach the YAML and checksum files to the corresponding GitHub Release.

If the GitHub CLI is installed and authenticated, publish a GitHub Release with:

```bash
make publish-github VERSION=0.1.0
```

## Credentials

Live validation reads Fitbit OAuth credentials from `.env` by default:

```text
FITBIT_CLIENT_ID=...
FITBIT_CLIENT_SECRET=...
FITBIT_REDIRECT_URL=http://localhost
FITBIT_REFRESH_TOKEN=...
```

The `.env` file is private and ignored by Git. Use `.env.example` as the template. If Fitbit rotates the refresh token during validation, the tool updates `FITBIT_REFRESH_TOKEN` in the `.env` file.

## Scope

The crawler/parser/generator covers the Fitbit Web API domains listed in the official reference sidebar. Sleep has a detailed response schema and schema validation against live samples. Other domains currently use permissive response schemas while preserving official request paths, parameters, scopes, descriptions, examples, and source URLs.
