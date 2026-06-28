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

The crawler/parser/generator covers the Fitbit Web API domains listed in the official reference sidebar. It preserves official request paths, parameters, scopes, descriptions, examples, and source URLs.

Response schemas are generated from official example responses when examples are available. Endpoints without official examples are still included with an open response schema.

Schema coverage by domain:

| Domain | Endpoints | Generated response schemas | Open response schemas |
| --- | ---: | ---: | ---: |
| active-zone-minutes-timeseries | 2 | 2 | 0 |
| activity | 16 | 8 | 8 |
| activity-timeseries | 2 | 2 | 0 |
| authorization | 5 | 1 | 4 |
| blood-glucose | 1 | 0 | 1 |
| body | 9 | 5 | 4 |
| body-timeseries | 6 | 6 | 0 |
| breathing-rate | 2 | 2 | 0 |
| cardio-fitness-score | 2 | 2 | 0 |
| devices | 5 | 4 | 1 |
| electrocardiogram | 1 | 0 | 1 |
| friends | 2 | 0 | 2 |
| heartrate-timeseries | 2 | 2 | 0 |
| heartrate-variability | 2 | 2 | 0 |
| intraday | 12 | 5 | 7 |
| irregular-rhythm-notifications | 2 | 1 | 1 |
| nutrition | 28 | 17 | 11 |
| nutrition-timeseries | 2 | 2 | 0 |
| sleep | 7 | 5 | 2 |
| spo2 | 2 | 1 | 1 |
| subscription | 3 | 2 | 1 |
| temperature | 4 | 1 | 3 |
| user | 3 | 0 | 3 |

Totals: 120 parsed endpoints, 61 generated response schemas, and 59 open response schemas.

## Schema Sources

The generated response schemas are inferred from the official example response payloads published in Fitbit's documentation. They are intentionally structural: object properties, arrays, scalar JSON types, and permissive `additionalProperties: true`.

The generator does not currently turn the prose response field tables into strict schemas. Those field descriptions are preserved in `data/parsed/`, but the OpenAPI response schema follows the example payload when both are present.

Known documentation differences:

| Area | Difference | Current handling |
| --- | --- | --- |
| Devices | The official `Get Devices` example is a single device object, while the live API returns an array of device objects. | The schema is generated from the official example. Live validation accepts an array by validating each item against the generated object schema. |
| Dynamic time-series keys | Some docs describe placeholders such as `activities-<resource>` or `body-<resource>`, while examples use concrete keys such as `activities-steps` or `body-weight`. | The generated schema follows the concrete official example key. |
| Response field tables vs examples | Several field tables list fields not present in the paired example, or examples include top-level fields not listed in the field table. This appears in areas such as daily activity summary, intraday data, nutrition logs, sleep goal/date responses, and SpO2 summary. | The generated schema follows the example. The field table text remains available in parsed endpoint JSON for future manual refinement. |
| Ambiguous intraday paths | Redocly reports two ambiguous OpenAPI paths where Fitbit documents both a generic activity intraday path and more specific AZM/heart intraday paths. | The spec preserves the official paths and accepts the Redocly warnings. |

Representative live validation currently covers 19 API calls across user, devices, activity, heart rate, body, breathing rate, SpO2, temperature, cardio fitness, nutrition, and sleep. Live samples are sanitized before being written to `data/samples/sanitized/`.
