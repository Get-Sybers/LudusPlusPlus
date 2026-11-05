# LudusPlusPlus — developer and CI entry points. Run `make help`.
SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= python3
TOOLS ?= $(CURDIR)/.tools
ACTIONLINT_VERSION ?= 1.7.12
ACTIONLINT_IMAGE ?= rhysd/actionlint:$(ACTIONLINT_VERSION)
export LUDUS_CI_TOOLS := $(TOOLS)
export PATH := $(TOOLS)/bin:$(PATH)
export PACKER_PLUGIN_PATH := $(TOOLS)/packer-plugins
export ANSIBLE_COLLECTIONS_PATH := $(TOOLS)/ansible-collections

.DEFAULT_GOAL := help
.PHONY: help deps ansible-deps lint lint-source lint-yaml lint-ansible lint-shell lint-actions packer-tools packer-fmt packer-validate test check-reference update-reference ci

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

deps: ## Install the Python tooling (requirements-ci.txt)
	$(PYTHON) -m pip install -r requirements-ci.txt

ansible-deps: ## Install the collections the Ludus server ships + this source's collections into .tools/ (for ansible-lint)
	scripts/install_ansible_deps.sh "$(TOOLS)"

lint: lint-source lint-yaml lint-ansible lint-shell lint-actions ## Run every linter

lint-source: ## Ludus source structure, template and blueprint rules (scripts/ludus_source_lint.py)
	$(PYTHON) scripts/ludus_source_lint.py --root .

lint-yaml: ## yamllint over the repository
	yamllint .

lint-ansible: ## ansible-lint over the Ansible content and template playbooks (run `make ansible-deps` once first)
	ansible-lint

lint-shell: ## shellcheck the scripts
	shellcheck scripts/*.sh

lint-actions: ## actionlint the GitHub workflows (binary on PATH or in .tools/bin, else `go run`, else the pinned docker image)
	@if command -v actionlint >/dev/null 2>&1; then actionlint; \
	elif [ -x "$(TOOLS)/bin/actionlint" ]; then "$(TOOLS)/bin/actionlint"; \
	elif command -v go >/dev/null 2>&1; then go run github.com/rhysd/actionlint/cmd/actionlint@v$(ACTIONLINT_VERSION); \
	else docker run --rm -v "$(CURDIR):/repo" --workdir /repo $(ACTIONLINT_IMAGE) -color; fi

packer-tools: ## Install Packer and plugins at the Ludus-pinned versions into .tools/
	scripts/install_ludus_packer.sh "$(TOOLS)"

packer-fmt: ## Rewrite the templates with packer fmt
	packer fmt -recursive templates

packer-validate: ## packer fmt -check + packer validate every template the way the Ludus server builds it
	scripts/packer_smoke.sh

test: ## Linter self-tests
	$(PYTHON) -m pytest -q tests

check-reference: ## Fail if upstream Ludus main drifted from ludus-reference/
	$(PYTHON) scripts/update_ludus_reference.py --check

update-reference: ## Regenerate ludus-reference/ from upstream Ludus main
	$(PYTHON) scripts/update_ludus_reference.py

ci: lint test packer-validate ## Everything the CI workflow runs
