.DEFAULT_GOAL := help
SHELL := /bin/bash
PROD_PORT ?= 8000

.PHONY: help install backend-install frontend-install dev backend frontend test fmt typecheck prod seed clean

help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: backend-install frontend-install ## 安装后端(pip) + 前端(npm)

backend-install: ## 后端：创建 venv 并安装依赖
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

frontend-install: ## 前端：npm install
	cd frontend && npm install

dev: ## 同时起后端(:8000) + 前端(:5173)（请在两个终端分别 make backend / make frontend）
	@echo "请分别运行：make backend   和   make frontend"

backend: ## 仅起后端 uvicorn :8000
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend: ## 仅起前端 vite :5173
	cd frontend && npm run dev

test: ## 后端 pytest
	cd backend && . .venv/bin/activate && pytest -q

typecheck: ## 前端 tsc --noEmit
	cd frontend && npx tsc --noEmit

fmt: ## 后端 ruff --fix + 前端 eslint --fix
	cd backend && . .venv/bin/activate && ruff check --fix . || true
	cd frontend && npm run lint -- --fix || true

prod: ## 构建前端并单端口伺服 SPA+API
	cd frontend && npm run build
	cd backend && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port $(PROD_PORT)

seed: ## 种子化（管理员 + 测试团队/项目）
	cd backend && . .venv/bin/activate && python -m app.seed.runner

clean: ## 清运行时缓存（保留 G3 数据与 .gitkeep）
	rm -rf backend/.venv frontend/node_modules .cache backend/__pycache__
