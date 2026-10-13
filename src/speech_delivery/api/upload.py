"""Receiving an upload without trusting it or holding it in memory."""

import contextlib
import re
import shutil
import tempfile
from pathlib import Path

from fastapi import UploadFile
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

UPLOAD_NAME = "upload"
CHUNK_BYTES = 1024 * 1024
FORM_OVERHEAD_BYTES = 64 * 1024
_SAFE_SUFFIX = re.compile(r"\.[a-z0-9]{1,8}")


class UploadTooLarge(Exception):
    pass


def safe_suffix(filename: str | None) -> str:
    """The file's extension if it is short and alphanumeric, so ffmpeg can sniff, else none."""
    suffix = Path(filename or "").suffix.lower()
    return suffix if _SAFE_SUFFIX.fullmatch(suffix) else ""


def save_upload(upload: UploadFile, limit: int) -> tuple[Path, Path]:
    """Copy the upload into a fresh temp directory under a fixed name.

    Returns the directory and the file. Raises UploadTooLarge, removing the directory first.
    """
    directory = Path(tempfile.mkdtemp(prefix="speech-delivery-"))
    path = directory / f"{UPLOAD_NAME}{safe_suffix(upload.filename)}"
    written = 0
    try:
        with path.open("wb") as out:
            while chunk := upload.file.read(CHUNK_BYTES):
                written += len(chunk)
                if written > limit:
                    raise UploadTooLarge
                out.write(chunk)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return directory, path


class BodyLimit:
    """Answers 413 to POST /api/jobs once the request body passes the limit.

    The multipart parser would otherwise spool an arbitrarily large body to disk first.
    """

    def __init__(self, app: ASGIApp, *, path: str, limit: int) -> None:
        self._app = app
        self._path = path
        self._limit = limit + FORM_OVERHEAD_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self._path:
            await self._app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"0")
        if declared.isdigit() and int(declared) > self._limit:
            await self._reject(scope, receive, send)
            return
        received = 0
        exceeded = False

        async def limited() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._limit:
                    exceeded = True
                    raise UploadTooLarge
            return message

        async def guarded(message: Message) -> None:
            # FastAPI turns any body-parsing exception into its own 400. Drop that response.
            if not exceeded:
                await send(message)

        with contextlib.suppress(UploadTooLarge):
            await self._app(scope, limited, guarded)
        if exceeded:
            await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse({"detail": "The upload is too large."}, status_code=413)
        await response(scope, receive, send)
