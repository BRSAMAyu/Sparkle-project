import os
from typing import Iterable, Optional, Set

from fastapi import UploadFile, HTTPException, status

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB


def _normalize_extensions(allowed_extensions: Optional[Iterable[str]]) -> Set[str]:
    if not allowed_extensions:
        return set()
    return {ext.lower() for ext in allowed_extensions}


def _validate_upload(
    file: UploadFile,
    allowed_extensions: Optional[Iterable[str]] = None,
    allowed_content_types: Optional[Iterable[str]] = None,
) -> str:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")

    ext = os.path.splitext(file.filename)[1].lower()
    normalized_exts = _normalize_extensions(allowed_extensions)
    if normalized_exts and ext not in normalized_exts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file extension")

    if allowed_content_types:
        content_type = (file.content_type or "").lower()
        allowed_types = {ctype.lower() for ctype in allowed_content_types}
        if content_type not in allowed_types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type")

    return ext


async def save_upload_file(
    file: UploadFile,
    destination: str,
    max_size: int,
    allowed_extensions: Optional[Iterable[str]] = None,
    allowed_content_types: Optional[Iterable[str]] = None,
) -> int:
    _validate_upload(file, allowed_extensions, allowed_content_types)
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    size = 0
    try:
        with open(destination, "wb") as buffer:
            while True:
                chunk = await file.read(DEFAULT_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if max_size and size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File too large",
                    )
                buffer.write(chunk)
    except Exception:
        if os.path.exists(destination):
            os.remove(destination)
        raise
    finally:
        await file.close()

    return size


async def read_upload_file(
    file: UploadFile,
    max_size: int,
    allowed_extensions: Optional[Iterable[str]] = None,
    allowed_content_types: Optional[Iterable[str]] = None,
) -> bytes:
    _validate_upload(file, allowed_extensions, allowed_content_types)

    data = bytearray()
    while True:
        chunk = await file.read(DEFAULT_CHUNK_SIZE)
        if not chunk:
            break
        data.extend(chunk)
        if max_size and len(data) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large",
            )
    await file.close()
    return bytes(data)
