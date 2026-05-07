import os
from collections.abc import Iterable

from fastapi import HTTPException, UploadFile, status

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB


def _normalize_extensions(allowed_extensions: Iterable[str] | None) -> set[str]:
    if not allowed_extensions:
        return set()
    return {ext.lower() for ext in allowed_extensions}


def _validate_upload(
    file: UploadFile,
    allowed_extensions: Iterable[str] | None = None,
    allowed_content_types: Iterable[str] | None = None,
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

    # TODO: Add magic-byte validation (e.g. python-magic or imghdr) to verify the
    # actual file content matches the declared extension / content_type. Currently
    # only the client-declared extension and Content-Type header are checked.
    return ext


async def save_upload_file(
    file: UploadFile,
    destination: str,
    max_size: int,
    allowed_extensions: Iterable[str] | None = None,
    allowed_content_types: Iterable[str] | None = None,
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
    allowed_extensions: Iterable[str] | None = None,
    allowed_content_types: Iterable[str] | None = None,
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
