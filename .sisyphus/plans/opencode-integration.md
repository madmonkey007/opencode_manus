# Plan: OpenCode AI Infrastructure Integration (Finalized)

## TL;DR

> **Quick Summary**: Optimize the Docker environment for a GUI-enabled sandbox and integrate the official `opencode-ai` CLI as the backend kernel. This replaces custom LLM logic with a production-grade agentic loop.
> 
> **Deliverables**:
> - Multi-layered Dockerfile supporting Bun, Node 20, and GUI tools (xvfb/fluxbox).
> - Kernel-bridged `app/main.py` with full SSE support for `opencode run` streaming.
> - `app/start.sh` automation for `oh-my-opencode` and workspace prep.
> - `static/opencode.js` enhancement for real-time file system feedback.
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Dockerfix -> Kernel Integration

---

## Context

### Original Request
Fix failing Docker builds (missing `unzip`) and integrate official kernel/plugins for `opencode-ai`.

### Interview Summary
- **Docker Issue**: `RUN` command failure due to missing `unzip` (required by Bun) and network timeouts.
- **Kernel Strategy**: Transition from `llm.ask_tool` to `opencode run [prompt]` CLI usage for better tool support and reliability.
- **SSE Requirement**: Real-time streaming of kernel thoughts, tool activations, and file updates.

---

## Work Objectives

### Core Objective
Deliver a stable, isolated sandbox environment that leverages the full power of the OpenCode ecosystem.

### Concrete Deliverables
- `Dockerfile`: Layered for cache efficiency; installs `unzip`, `ca-certificates`, Node 20, Bun, and `opencode-ai`.
- `app/main.py`: FastApi endpoint `run_sse` rewritten to manage `subprocess.Popen` lifecycle and SSE mapping.
- `app/start.sh`: Handles `bunx oh-my-opencode install` and host-to-container skill sync.
- `static/opencode.js`: Event listener for `file_update` to auto-refresh the file tree.

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: Manual-only (Visual/CLI verification)
- **QA approach**: Automated Docker build check + Manual SSE stream inspection.

### Automated Verification (Agent-Executable)

**1. Docker Infrastructure:**
```bash
docker build --no-cache -t opencode-test .
```

**2. SSE Kernel Loop:**
```bash
# Verify kernel process start and SSE output
curl -v "http://localhost:8000/opencode/run_sse?prompt=write+hello.py&sid=test_verify"
```

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
├── Task 1: Dockerfile Fix & Optimization
└── Task 2: Frontend & SSE Logic Prep

Wave 2 (After Wave 1):
├── Task 3: app/main.py Kernel Implementation
└── Task 4: app/start.sh Configuration

---

## TODOs

- [ ] 1. Dockerfile Fix & Optimization
  **What to do**:
  - Split current massive `RUN` into:
    1. Base packages (`unzip`, `git`, `curl`, `ca-certificates`, `wget`).
    2. GUI Support (`xvfb`, `fluxbox`, `novnc`, etc.).
    3. Node.js 20.x setup via Nodesource.
    4. Bun installation.
  - Install `opencode-ai` globally via `npm install -g opencode-ai`.
  
  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: [bash]
  
  **Acceptance Criteria**:
  - [ ] `docker build` succeeds without `unzip` errors.
  - [ ] `opencode --version` works inside the container.

- [ ] 2. Kernel Bridging (app/main.py)
  **What to do**:
  - Rewrite `run_agent` to use `asyncio.create_subprocess_exec`.
  - Command: `opencode run "[prompt]" --session [sid]`.
  - Parse stdout lines:
    - `[Thought] ...` -> SSE `thought`
    - `[Tool] ...` -> SSE `activate`
    - `[FileUpdate]` -> SSE `file_update`
  - Map final response to SSE `answer_chunk`.

  **Recommended Agent Profile**:
  - **Category**: ultrabrain
  - **Skills**: [native-data-fetching] (for SSE logic)

  **Acceptance Criteria**:
  - [ ] `sid` creates corresponding `workspace/{sid}` folder.
  - [ ] SSE stream correctly reflects agent progress.

- [ ] 3. Startup & Plugin Logic (app/start.sh)
  **What to do**:
  - Add `bunx oh-my-opencode install --gemini=yes --opencode-zen=yes`.
  - Add logic to symlink `/app/skills` to `/root/.opencode/skills`.

- [ ] 4. Real-time Refresh (static/opencode.js)
  **What to do**:
  - Ensure `file_update` event handler calls `renderFiles()`.

---

## Commit Strategy
- `feat(docker): fix bun install and optimize layers`
- `feat(kernel): bridge app/main.py to opencode cli`
- `feat(ui): real-time file list refresh`
