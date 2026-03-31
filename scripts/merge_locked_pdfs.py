import base64
import io
import json
import os
import sys
import urllib.request
from typing import Any


def _load_pypdf():
    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore

        return PdfReader, PdfWriter
    except Exception as exc:
        return None, exc


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


def _password_for(url: str, provided: dict[str, str]) -> str:
    name = os.path.basename(url.split("?", 1)[0])
    if not name:
        return ""
    return provided.get(name, name[:10])


def _add_pdf_pages(writer: Any, reader_cls: Any, data: bytes, password: str) -> int:
    reader = reader_cls(io.BytesIO(data), strict=False)

    if reader.is_encrypted:
        if not password:
            raise ValueError("missing password")
        decrypt_res = reader.decrypt(password)
        if decrypt_res == 0:
            raise ValueError("invalid password")

    count = 0
    for page in reader.pages:
        writer.add_page(page)
        count += 1
    return count


def main() -> int:
    reader_cls, writer_cls_or_error = _load_pypdf()
    if reader_cls is None:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"pypdf is not available: {writer_cls_or_error}",
                }
            )
        )
        return 0

    raw = sys.stdin.read() or "{}"
    payload: dict[str, Any] = json.loads(raw)

    urls = payload.get("urls") or []
    if not isinstance(urls, list) or not urls:
        print(json.dumps({"ok": False, "error": "urls are required"}))
        return 1

    provided_pw = payload.get("passwords") or {}
    if not isinstance(provided_pw, dict):
        provided_pw = {}

    writer = writer_cls_or_error()
    pages_added = 0
    failures: list[str] = []

    for url in urls:
        try:
            url_str = str(url)
            data = _fetch_bytes(url_str)
            if not data.startswith(b"%PDF"):
                failures.append(f"{url_str}: not a PDF payload")
                continue

            pw = _password_for(url_str, provided_pw)
            pages_added += _add_pdf_pages(writer, reader_cls, data, pw)
        except Exception as exc:
            failures.append(f"{url}: {exc}")

    if pages_added == 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "No pages could be decrypted and merged",
                    "failures": failures,
                }
            )
        )
        return 0

    out = io.BytesIO()
    writer.write(out)
    out_b64 = base64.b64encode(out.getvalue()).decode("ascii")

    print(
        json.dumps(
            {
                "ok": True,
                "pagesAdded": pages_added,
                "pdfBase64": out_b64,
                "failures": failures,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
