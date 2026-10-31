UV ?= uv

.DEFAULT_GOAL := help

.PHONY: help
help: ## Lista todos os targets disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

.PHONY: install
install: ## Instala o Python do .python-version e as dependências (precisa do uv)
	@command -v $(UV) >/dev/null || { echo "uv não encontrado: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	$(UV) sync --locked

.PHONY: test
test: ## Roda os testes
	$(UV) run pytest

.PHONY: lint
lint: ## Confere estilo e formatação (ruff)
	$(UV) run ruff check .
	$(UV) run ruff format --check .

.PHONY: format
format: ## Corrige estilo e formatação (ruff)
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

.PHONY: mutate
mutate: ## Testes de mutação (mutmut) em src/; MODULE=cases restringe a um módulo
	rm -rf mutants
	PYTHONDONTWRITEBYTECODE=1 $(UV) run mutmut run $(if $(MODULE),"agent_eval_kit.$(MODULE).*")
	$(UV) run mutmut results

.PHONY: verify
verify: lint test ## Gates do CI: lint e testes
