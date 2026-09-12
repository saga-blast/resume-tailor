import base64
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="resume-tailor-compile-service")

# Generous on purpose: tectonic downloads its package bundle over the network
# on first use (cached in the tectonic-cache volume afterwards), which alone
# can take well over 30s. Subsequent compiles are much faster.
COMPILE_TIMEOUT_SECONDS = 120


def _decode(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class CompileRequest(BaseModel):
    tex_source: str
    job_id: str | None = None


class CompileResponse(BaseModel):
    status: str  # "success" | "error"
    pdf_base64: str | None = None
    log: str
    message: str | None = None


def _extract_first_error(log: str) -> str | None:
    for line in log.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("error:"):
            return stripped
    return None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/compile", response_model=CompileResponse)
def compile_tex(req: CompileRequest) -> CompileResponse:
    work_id = req.job_id or uuid.uuid4().hex
    work_dir = Path(tempfile.gettempdir()) / "compile" / work_id
    out_dir = work_dir / "out"
    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = work_dir / "main.tex"

    try:
        tex_path.write_text(req.tex_source, encoding="utf-8")

        try:
            result = subprocess.run(
                ["tectonic", "main.tex", "--outdir", str(out_dir)],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=COMPILE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            log = _decode(exc.stdout) + _decode(exc.stderr)
            return CompileResponse(status="error", log=log, message="Compile timed out")
        except FileNotFoundError:
            return CompileResponse(
                status="error",
                log="",
                message="tectonic binary not found on PATH inside the compile-service container",
            )

        log = (result.stdout or "") + (result.stderr or "")

        if result.returncode != 0:
            return CompileResponse(
                status="error",
                log=log,
                message=_extract_first_error(log) or "LaTeX compilation failed",
            )

        pdf_path = out_dir / "main.pdf"
        if not pdf_path.exists():
            return CompileResponse(
                status="error",
                log=log,
                message="Compiler reported success but no PDF was produced",
            )

        pdf_bytes = pdf_path.read_bytes()
        return CompileResponse(
            status="success",
            pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
            log=log,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
