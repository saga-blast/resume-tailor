import base64

import httpx

from app.config import get_settings

settings = get_settings()


class CompileResult:
    def __init__(self, status: str, pdf_bytes: bytes | None, log: str, message: str | None) -> None:
        self.status = status
        self.pdf_bytes = pdf_bytes
        self.log = log
        self.message = message


async def compile_tex(tex_source: str, job_id: str | None = None) -> CompileResult:
    try:
        # Exceeds the compile-service's own 120s timeout so we never give up
        # on a request it's still legitimately working on (e.g. tectonic's
        # first-run bundle download).
        async with httpx.AsyncClient(timeout=130.0) as client:
            response = await client.post(
                f"{settings.compile_service_url}/compile",
                json={"tex_source": tex_source, "job_id": job_id},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError:
        return CompileResult(
            status="error",
            pdf_bytes=None,
            log="",
            message=(
                "Could not reach the LaTeX compile service at "
                f"{settings.compile_service_url}. Is it running? (docker compose up)"
            ),
        )
    except httpx.HTTPError as exc:
        return CompileResult(
            status="error",
            pdf_bytes=None,
            log="",
            message=f"Compile service request failed: {exc}",
        )

    pdf_bytes = base64.b64decode(data["pdf_base64"]) if data.get("pdf_base64") else None
    return CompileResult(
        status=data["status"],
        pdf_bytes=pdf_bytes,
        log=data.get("log", ""),
        message=data.get("message"),
    )
