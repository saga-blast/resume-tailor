# Resume Tailor

A personal web app that takes a job description, compares it against your resume/profile, asks you about any skill gaps it can't resolve on its own (remembering your answers so it never asks twice), and produces an updated, JD-highlighted LaTeX resume you can review in a live split-pane editor and export to PDF.

See the implementation plan for full architecture/design rationale.

## Status: M1 complete and verified

M1 proves the riskiest piece of the stack end-to-end with **no LLM involved yet**: a Docker-hosted LaTeX compile service, a backend that proxies to it, and a split-pane Monaco/PDF editor in the frontend. This has been built and verified for real — login, job creation, a real `titlesec`/`enumitem` resume compiling to a valid PDF through the full backend → compile-service path, and the error panel showing a real LaTeX error message for broken input. Later milestones (M2–M5) add JD parsing, requirement matching, the preference-memory Q&A loop, and highlight generation via Claude.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker Desktop** (WSL2 backend, on Windows) — required for the LaTeX compile service.

> The `compile-service/Dockerfile` installs [tectonic](https://tectonic-typesetting.github.io/) via its official installer script and pre-warms its package cache (including the babel hyphenation-pattern bundle every LaTeX format build fetches) at image-build time. **First build takes ~5 minutes** for that warmup step alone — this is expected, not a hang. After that, compiles typically take well under 10s.

## First-time setup

### 1. Compile service (Docker)

```bash
docker compose up --build
```

This builds and starts the LaTeX compile microservice on `http://localhost:8100`. Check it's healthy:

```bash
curl http://localhost:8100/health
```

### 2. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # already has working local defaults; edit if you want your own seed login
uvicorn app.main:app --reload --port 8000 
```

This creates `backend/storage/app.db` (SQLite) on first run and seeds one login user from `.env` (`SEED_USER_EMAIL` / `SEED_USER_PASSWORD`, default `you@example.com` / `change-me`).

### 3. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — it redirects to a fresh demo job pre-loaded with a sample resume.

## Using the M1 editor

1. Edit the LaTeX in the left pane (Monaco).
2. Click **Compile** — the backend forwards your `.tex` to the compile service; the right pane shows the resulting PDF.
3. Break the LaTeX on purpose (e.g. delete a `\end{itemize}`) and compile again — you should see a red error log panel instead of a silent failure, and the *previous* successful PDF should stay visible rather than blanking out.
4. **Save** persists the current `.tex` to the job record without compiling. **Download PDF** saves the last compiled PDF.

## Project layout

```
resume-tailor/
├── backend/            # FastAPI: auth, DB, job records, proxies to compile-service
├── compile-service/    # Dockerized tectonic + thin FastAPI wrapper (POST /compile)
├── frontend/           # Vite + React: split-pane LaTeX editor / PDF preview
└── docker-compose.yml  # wires up compile-service
```

The backend runs natively during dev (`uvicorn --reload`) for fast iteration; only the compile service needs Docker, since it needs the LaTeX toolchain.

## Troubleshooting

- **`docker compose build` fails partway through pulling the base image** (e.g. `failed to compute cache key: short read: ... unexpected EOF`) — this is a transient network hiccup truncating a layer download, not a Dockerfile problem. Just retry `docker compose build compile-service`; Docker resumes from what it already has cached.
- **`docker compose up --build` fails on the tectonic install step** — the installer script at `https://drop-sh.fullyjustified.net` may have changed its interface, or network access from the build step may be blocked. As a fallback, swap the relevant `RUN` lines in `compile-service/Dockerfile` for either `conda install -c conda-forge tectonic` (via a miniconda base image) or a full `texlive/texlive` base image running `latexmk` instead of `tectonic` (the rest of `app.py` only needs the `tectonic` subprocess call swapped for `latexmk -pdf -interaction=nonstopmode`).
- **Compile always returns "tectonic binary not found on PATH"** — the image built but the installer didn't place the binary at `/usr/local/bin/tectonic`; `docker compose exec compile-service which tectonic` to check where it actually landed and adjust the Dockerfile's `mv` line.
- **Compile fails with `error while loading shared libraries: lib....so`** — tectonic's prebuilt binary needs `libgraphite2-3` from apt (already included in the Dockerfile); if a different missing library ever shows up, run `docker compose run --rm compile-service ldd /usr/local/bin/tectonic` to see exactly what's unresolved, then add the matching apt package.
- **First-ever compile after a fresh volume takes minutes and eventually times out** — this shouldn't happen since the image now pre-warms the cache at build time (Docker copies that pre-populated cache into the `tectonic-cache` volume the first time it's mounted), but if you ever see it: it means tectonic is re-downloading the babel hyphenation-pattern bundle from scratch, which took ~3 minutes over a normal connection when this was last measured. `COMPILE_TIMEOUT_SECONDS` in `compile-service/app.py` is set to 120s to comfortably cover a normal compile; raise it further if needed.
- **CORS errors in the browser console** — make sure the backend is running on port 8000 and the frontend on 5173; `backend/app/main.py` only allows `http://localhost:5173` as an origin.
- **Backend crashes on startup with a `bcrypt`/`passlib` error** — `passlib` 1.7.4 is incompatible with modern `bcrypt` releases (a known upstream break); `app/security.py` already hashes passwords with `bcrypt` directly instead of through `passlib` for this reason, so this shouldn't recur, but it's worth knowing if you ever see `AttributeError: module 'bcrypt' has no attribute '__about__'`.
