.DEFAULT_GOAL := help
.PHONY: help finalize cleanup format lint typing copy

##@ General
help: ## Display this help section
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Workflow
finalize: format lint typing ## format, lint, and type check before building package

##@ Quality
format: ## format python files using ruff
	uv run ruff format

lint: ## lint python files using ruff
	uv run ruff check --fix

typing: ## type check python files using ty
	uv run ty check
