# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo orientation

ICE Data Workbench v3 — AI 数据工作流工作台. Stack: **FastAPI + SQLAlchemy + JWT/Aegis (backend)** and **React 18 + Vite + TypeScript + Zustand (frontend, named `react@19` in plans but installed as 18.3)**. The architectural rules of the project — what's a constraint vs. a default — live in [`design_decisions.md`](design_decisions.md) (133 decisions + 3 global constraints), [`requirements/SHARED.md`](requirements/SHARED.md), [`requirements/BACKEND.md`](requirements/BACKEND.md), [`requirements/FRONTEND.md`](requirements/FRONTEND.md). Read those before redesigning; the code embeds those decisions.

## Common commands

```bash
make install      # backend pip + frontend npm
make dev          # backend :8000 + frontend :5173 (proxy /api → 8000, ws:true)
make backend      # backend only
make frontend     # frontend only
make test         # cd backend && pytest -q
make seed         # one-shot seed bootstrap (admin user)
make fmt          # ruff --fix + eslint --fix
make prod         # build dist + uvicorn 0.0.0.0:$PROD_PORT (single port serves SPA + API + WS)
make pack         # → ice-workbench-YYYYMMDD.zip (includes .env + dist, excludes venv/node_modules/runtime data)
make reset-data   # wipe .cache/, users/<uuid>/, tasks/<uuid>/ — leaves seed templates
```

Single backend test: `cd backend && . .venv/bin/activate && pytest tests/test_auth.py::test_login_password -q`
Frontend typecheck only: `cd frontend && npx tsc --noEmit`
Rebuild SQLite cache index: `cd backend && . .venv/bin/activate && python scripts/rebuild_index.py`

`./deploy.sh` (no flag = install only; `--run` = dev; `--prod` = build + single-port). Honors `ICE_BIND_HOST` / `ICE_BIND_PORT`.

Default seeded login: `admin / admin123` (rotate `ICE_SECRET_KEY` and `MIFY_GATEWAY_API_KEY` before any non-local deploy).

## High-level architecture

### G3 · File-first storage (CRITICAL)

**The filesystem is source of truth. SQLite (`/.cache/index.db`) is only a derived index.** This is the single most important invariant in the codebase — `requirements/BACKEND.md §1`. Anything that contradicts it is a bug.

- All persistent data lives under top-level dirs at the repo root: [`agents/`](agents/), [`skills/`](skills/), [`files/`](files/), [`users/{uuid}/`](users/), [`tasks/{uuid}/`](tasks/).
- All path resolution goes through [`backend/app/core/storage/paths.py`](backend/app/core/storage/paths.py) — never `os.path.join` paths to user/task data inline.
- All multi-file writes go through [`file_transaction()`](backend/app/core/storage/transaction.py) (advisory locks via `portalocker`, atomic backup + rollback). Never write a JSON file directly without a lock.
- Append-heavy data (conversation messages, tool calls, audit logs) uses `*.jsonl`, not `*.json`, to avoid lock contention. See `paths.task_conversation`, `paths.task_tool_calls`, `paths.user_notifications`.
- The SQLite cache (`.cache/index.db`) is rebuildable from the filesystem at any time — `scripts/rebuild_index.py`. If the index is missing or row count diverges from filesystem at boot, it auto-rebuilds.
- `DATA_ROOT` defaults to the repo root and is auto-resolved by `Settings` so a packed zip is portable across machines without editing `.env`.

### Backend layout (`backend/app/`)

- `main.py` — FastAPI app + lifespan (boots `seed.runner.bootstrap()` and starts `scheduler_svc`'s 20s scan loop). In prod, mounts `frontend/dist/` for single-port SPA serving with `Cache-Control: no-cache` on `index.html`.
- `api/v1/` — one router module per resource group (auth, tasks, conversations, agents, skills, files, kb, notifications, scheduled, templates, experience_cards, invitations, search, system_config, ws, admin*, guide). All registered in [`api/v1/__init__.py`](backend/app/api/v1/__init__.py) under prefix `/api/v1`.
- `services/` — business logic. **All filesystem I/O goes through `services/`, not the API layer.** Notable: [`agent_runtime.py`](backend/app/services/agent_runtime.py) (bounded ReAct loop for sub-agents/bg jobs), [`tool_runner.py`](backend/app/services/tool_runner.py) (built-in tool dispatch + skill execution), [`llm_gateway.py`](backend/app/services/llm_gateway.py) (model-prefix-routed protocol adapter), [`compaction_svc.py`](backend/app/services/compaction_svc.py), [`scheduler_svc.py`](backend/app/services/scheduler_svc.py).
- `core/storage/` — paths, jsonio, advisory locks, file_transaction, SQLite index. Treat as a single internal module: import from `app.core.storage`, not the submodules.
- `core/deps.py` — **dual auth**: `X-Proxy-UserDetail` (Aegis/米盾, RSA-verified) OR `Authorization: Bearer <jwt>`. WebSocket auth additionally accepts subprotocol `["bearer", "<token>"]` and (legacy) `?token=`. `AEGIS_DEV_BYPASS_EMAIL` requires opt-in `X-Dev-Bypass: 1` header — must be inert without it.
- `core/aegis.py` — RSA-verifies `X-Proxy-UserDetail`. Multiple keys supported (comma-separated rotation).
- `seed/runner.py` — boot seed for admin/test users + bundled agents/skills.

### Frontend layout (`frontend/src/`)

- `App.tsx` — routes. Login + Introduce + Feishu callback are eager; everything else is lazy. Admin pages share `AdminLayout`.
- `pages/` — one folder per route, named by domain (`dashboard`, `workspace`, `create_task`, `scheduled`, `agent_detail`, `guide`, `admin/*`).
- `components/` — `chat/` (streaming chat UI), `task/`, `markdown/` (`react-markdown` + DOMPurify), `feedback/` (Toast/Skeleton/ErrorState), `guards/` (`AuthGuard`/`AdminGuard`), `shell/` (`TopNav`/`MobileBottomBar`/`InviteInbox`).
- `stores/` — Zustand: `authStore` (current user + tokens), `uiStore` (theme, modals).
- `api/` — `client.ts` (axios with interceptors) + `endpoints.ts` (typed endpoint URLs).
- Path alias `@/` → `frontend/src/`. Vite proxy forwards `/api` (HTTP and WS) to `:8000` in dev; in prod the backend serves the SPA itself.
- Vendor chunking (`vite.config.ts`): only React core split out; everything else in one `vendor` chunk on purpose — splitting markdown/refractor produced circular ESM imports and white-screen.

### LLM gateway routing

`llm_gateway.py` routes by model-id prefix to one of four protocols. All four emit the same internal event protocol (`text` / `tool_use_delta` / `message_done`) so consumers in `api/v1/ws.py` and `agent_runtime` are protocol-agnostic.

| Prefix              | Protocol                                  |
|---------------------|-------------------------------------------|
| `ppio/pa/claude-*`  | Anthropic native (`/anthropic/v1/messages`) — **preferred for Claude, supports tool_use streaming** |
| `azure_openai/*`    | OpenAI Responses API (`/v1/responses`)    |
| `vertex_ai/*` / `xiaomi/*` / other `/`-containing | OpenAI Chat-Completions (`/v1/chat/completions`) |
| no `/`              | Legacy native Anthropic SDK via `ANTHROPIC_BASE_URL` |

Mify gateway (`MIFY_GATEWAY_*`) is preferred; `ANTHROPIC_API_KEY` is only the fallback. `settings.llm_enabled` is True if either path is configured; `/ws` returns `LLM_KEY_MISSING` otherwise.

### Tool calling / agent runtime

- 5-round bounded tool-calling loop (`MAX_TOOL_ROUNDS=5`, `TOOL_TIMEOUT_SEC=30` in `llm_gateway.py`). Main streaming path: `api/v1/ws.py`. Non-streaming sub-agent / bg-task path: `agent_runtime.run_agent_turn`.
- Built-in tools (always available regardless of agent): `now`, `echo`, `kyuubi_query` (xiaomi-kyuubi-cli SELECT), `feishu_publish` (`feishu` CLI), `feishu_upload_image` (PNG → docx), `write_file` (drops to `tasks/{tid}/files/output/`), `execute_python` (sandboxed; data-analysis agent only — see below).
- External CLI tools degrade to error codes (`KYUUBI_NOT_CONFIGURED`, `FEISHU_CLI_NOT_INSTALLED`) when the CLI is missing — they don't block boot.
- `execute_python` runs user-generated Python in `backend/.venv-sandbox/` (bootstrap once via `make install-sandbox`) — separate venv with whitelisted analytics packages (pandas/numpy/scipy/sklearn/statsmodels/prophet/ruptures/matplotlib/seaborn/pyarrow). Sandbox enforces: CPU 60s, memory 1GB (Linux RLIMIT_AS), file size 50MB, no network (socket monkey-patched), no service credentials in env, cwd=`<task_workspace>/files/output/`. Stateless — every call is a fresh process. See `backend/app/services/sandbox/`.
- Inflight guard in `ws.py`: `(task_id, conv_id)` → running task. WS disconnect during a turn does **not** cancel; only explicit `abort` messages flip the cancel event. A second message while a turn is running returns `CONVERSATION_INFLIGHT`.
- v2 runtime mechanisms (TodoList, sub-agents, plan mode, parallel tools, compaction, bg tasks) are env-gated — see `ICE_*_ENABLED` flags in `.env.example`. **Compaction defaults on**; everything else defaults off so conversations are bit-stable on upgrade.

### Auth & roles (G2)

Three-level role: `super_admin` / `admin` / `user`. Permissions matrix in [`requirements/SHARED.md §2`](requirements/SHARED.md). Constraints in code:

- super_admin **must** Feishu-OAuth — password login returns `SUPER_ADMIN_REQUIRES_FEISHU`.
- super_admin cannot demote self; system always preserves ≥1 super_admin.
- Dual auth in `core/deps.py` (Aegis OR JWT); both produce the same user-dict shape so handlers don't branch on auth path.
- Feishu first-login auto-creates a `user` (toggleable via `enable_feishu_auto_register`); `enable_feishu_strict_whitelist` is the mutually-exclusive opposite.

### WebSocket protocol

`/api/v1/ws/conversations/{cid}?task_id=...` — see `requirements/SHARED.md §5`. JWT auth via subprotocol `["bearer", "<token>"]` (preferred) or `?token=` (legacy). In prod with Aegis, the proxy header carries auth; WS still upgrades through the same `/api` path and Vite proxy has `ws:true`.

## Behavioral conventions for this repo

- **Error envelope** is uniform: `{code, message, error_code, data}`. Server-side raises `APIError(status, ErrorCode.X, msg)` from `core/errors.py`; FastAPI exception handlers in `main.py` convert everything (including `StarletteHTTPException` and unhandled `Exception`) to this shape. Don't return `HTTPException` directly — use `APIError`.
- **External-CLI degradation**: every integration that depends on an external binary (`kyuubi`, `feishu`, Mify) checks at runtime and returns a `*_NOT_CONFIGURED` / `*_NOT_INSTALLED` error code instead of crashing. Preserve this on new integrations.
- **Index ↔ filesystem consistency**: when you write a `users/`/`tasks/` JSON, you must also update the SQLite cache row in the same `file_transaction`. Reads can hit the index for listings but must source content from files.
- **No mock data on user-facing pages** (G1). Mock UI is allowed only in admin demo states and `design_v3/`.
- **Atomic unit is 任务 (task), not 笔记本.** Borrow notebook-style UI patterns when useful, but don't rename `task_id` / `task_dir` / `tasks/` to anything notebook-flavored. (Memory: `feedback_naming.md`.)
- **「重设计 UI」 default scope** = visual reskin only: tokens.css / global.css / fonts. Don't restructure layouts/IA/component naming unless explicitly asked. (Memory: `feedback_redesign_scope.md`.) **Mobile adaptation is the explicit exception** — mobile fixes may rewrite layout/IA. (Memory: `feedback_mobile_layout.md`.)
- **Hot-update preservation**: any redeploy on a live machine must preserve `users/`, `tasks/`, `files/`, `backend/.venv/`, `.env`. The `pack` Makefile target encodes this — don't widen its include-list to runtime data, and don't add deploy steps that wipe it. (Memory: `feedback_hot_update.md`.)
- **Frontend code references**: use markdown links `[file.tsx:42](path/file.tsx#L42)` in chat output, not backticks.
