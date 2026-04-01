import base64
import io
import os
import urllib.request
from urllib.parse import unquote
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
from pypdf import PdfReader, PdfWriter


app = FastAPI()


class MergeRequest(BaseModel):
    urls: list[str]
    passwords: dict[str, str] = {}


def _fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def _password_candidates(url: str, provided: dict[str, str]) -> list[str]:
    name = os.path.basename(unquote(url.split("?", 1)[0]))
    stem, _ = os.path.splitext(name)

    lowered = {k.lower(): v for k, v in provided.items()}
    candidates: list[str] = []

    for key in [name, stem, name.lower(), stem.lower()]:
        if not key:
            continue
        direct = provided.get(key)
        if direct:
            candidates.append(direct)
        mapped = lowered.get(key.lower())
        if mapped:
            candidates.append(mapped)

    for token in [name, stem]:
        if token:
            candidates.append(token[:10])
            candidates.append(token[:8])

    # Keep order, drop empties/duplicates.
    deduped: list[str] = []
    seen: set[str] = set()
    for pwd in candidates:
        if not pwd or pwd in seen:
            continue
        seen.add(pwd)
        deduped.append(pwd)
    return deduped


def _add_pdf_pages(writer: PdfWriter, data: bytes, passwords: list[str]) -> int:
    reader = PdfReader(io.BytesIO(data), strict=False)

    if reader.is_encrypted:
        if not passwords:
            raise ValueError("missing password")

        unlocked = False
        for password in passwords:
            try:
                decrypt_res = reader.decrypt(password)
            except Exception:  # noqa: BLE001
                continue
            if decrypt_res != 0:
                unlocked = True
                break

        if not unlocked:
            raise ValueError("invalid password")

    count = 0
    for page in reader.pages:
        writer.add_page(page)
        count += 1
    return count


def _check_auth(authorization: str | None) -> None:
    expected = os.getenv("DECRYPT_SERVICE_TOKEN", "").strip()
    if not expected:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    received = authorization[len("Bearer ") :].strip()
    if received != expected:
        raise HTTPException(status_code=403, detail="invalid bearer token")


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> dict[str, bool]:
    return {"ok": True}


@app.head("/")
def root_head() -> Response:
    return Response(status_code=200)


@app.post("/merge-locked")
def merge_locked(
    payload: MergeRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)

    if not payload.urls:
        raise HTTPException(status_code=400, detail="urls are required")

    writer = PdfWriter()
    pages_added = 0
    failures: list[str] = []

    for url in payload.urls:
        try:
            data = _fetch_bytes(url)
            if not data.startswith(b"%PDF"):
                failures.append(f"{url}: not a PDF payload")
                continue

            password_candidates = _password_candidates(url, payload.passwords)
            pages_added += _add_pdf_pages(writer, data, password_candidates)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{url}: {exc}")

    if pages_added == 0:
        return {
            "ok": False,
            "error": "No pages could be decrypted and merged",
            "failures": failures,
        }

    out = io.BytesIO()
    writer.write(out)

    return {
        "ok": True,
        "pagesAdded": pages_added,
        "pdfBase64": base64.b64encode(out.getvalue()).decode("ascii"),
        "failures": failures,
    }
