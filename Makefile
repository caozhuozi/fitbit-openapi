SHELL := /usr/bin/env bash

DOMAIN ?= all
ENV_FILE ?= .env
PYTHON ?= python3
VENV ?= .venv
PY := . $(VENV)/bin/activate && python

.PHONY: help install crawl parse generate validate-live validate-samples lint bundle validate release publish-github clean

help:
	@echo "Targets:"
	@echo "  install                         Install Python and Node dependencies"
	@echo "  crawl DOMAIN=all                Crawl official Fitbit docs"
	@echo "  parse DOMAIN=all                Parse crawled docs into endpoint JSON"
	@echo "  generate DOMAIN=all             Generate OpenAPI source files"
	@echo "  validate-live DOMAIN=all        Validate representative live API samples"
	@echo "  validate-samples DOMAIN=all     Validate sanitized live API samples"
	@echo "  lint                            Redocly lint openapi.yaml"
	@echo "  bundle                          Bundle dist/fitbit-openapi.yaml"
	@echo "  validate                        Run sample validation, lint, and bundle"
	@echo "  release VERSION=x.y.z           Build local release artifacts"
	@echo "  publish-github VERSION=x.y.z    Create GitHub release with artifacts"

install:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -e ".[dev]"
	npm install

crawl:
	$(PY) -m tools.fitbit_docs crawl --domain $(DOMAIN)

parse:
	$(PY) -m tools.fitbit_docs parse --domain $(DOMAIN)

generate:
	$(PY) -m tools.fitbit_docs generate --domain $(DOMAIN) --version $(VERSION)

validate-live:
	$(PY) -m tools.fitbit_docs validate-live --domain $(DOMAIN) --env-file $(ENV_FILE)

validate-samples:
	$(PY) -m tools.fitbit_docs validate-samples --domain $(DOMAIN)

lint:
	npm run lint

bundle:
	npm run bundle

validate: validate-samples lint bundle

release:
	@test -n "$(VERSION)" || (echo "VERSION is required. Usage: make release VERSION=0.1.0" >&2; exit 1)
	$(PY) -m tools.fitbit_docs generate --domain all --version $(VERSION)
	$(PY) -m tools.fitbit_docs validate-samples --domain all
	npm run lint
	npm run bundle
	mkdir -p release
	cp dist/fitbit-openapi.yaml release/fitbit-openapi-$(VERSION).yaml
	(cd release && shasum -a 256 fitbit-openapi-$(VERSION).yaml > fitbit-openapi-$(VERSION).yaml.sha256)

publish-github: release
	@test -n "$(VERSION)" || (echo "VERSION is required. Usage: make publish-github VERSION=0.1.0" >&2; exit 1)
	git tag v$(VERSION)
	git push origin v$(VERSION)
	gh release create v$(VERSION) \
		release/fitbit-openapi-$(VERSION).yaml \
		release/fitbit-openapi-$(VERSION).yaml.sha256 \
		--generate-notes

clean:
	rm -rf release
