#!/usr/bin/env python3
import argparse
import asyncio
import mimetypes
import os
import sys
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.append(str(BACKEND_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 0 smoke test for file upload + document vectorization.")
    parser.add_argument("--file", required=True, help="Path to a test document (PDF/DOCX/PPTX).")
    parser.add_argument("--gateway-url", default=os.getenv("GATEWAY_URL", "http://localhost:8080"))
    parser.add_argument("--token", default=os.getenv("TOKEN", ""))
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--minio-health-url", default=os.getenv("MINIO_HEALTH_URL", "http://localhost:9000/minio/health/ready"))
    parser.add_argument("--skip-upload", action="store_true", help="Skip gateway upload flow.")
    parser.add_argument("--skip-vectorize", action="store_true", help="Skip document parse + embedding + pgvector insert.")
    parser.add_argument("--skip-minio-check", action="store_true", help="Skip MinIO health check.")
    parser.add_argument("--skip-pgvector-check", action="store_true", help="Skip pgvector extension check.")
    parser.add_argument("--visibility", default="private", help="Visibility for upload complete call.")
    parser.add_argument("--group-id", default="", help="Optional group id for upload complete.")
    return parser.parse_args()


def log(msg: str) -> None:
    print(msg, flush=True)


def load_file(file_path: str) -> tuple[Path, int, str]:
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    size = path.stat().st_size
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return path, size, mime


def check_minio(minio_health_url: str) -> None:
    log("1. Checking MinIO health...")
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(minio_health_url)
        resp.raise_for_status()
    log("   MinIO is healthy.")


def prepare_upload(client: httpx.Client, gateway_url: str, token: str, file_path: Path, file_size: int, mime: str) -> dict:
    log("2. Requesting upload credentials...")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"filename": file_path.name, "file_size": file_size, "mime_type": mime}
    resp = client.post(f"{gateway_url}/api/v1/files/upload/prepare", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "presigned_url" not in data or "upload_id" not in data:
        raise RuntimeError(f"Unexpected prepare response: {data}")
    log("   Upload credentials received.")
    return data


def upload_to_storage(presigned_url: str, fields: dict | None, file_path: Path, mime: str) -> None:
    log("3. Uploading file to object storage...")
    if fields:
        with file_path.open("rb") as handle:
            files = {"file": (file_path.name, handle, mime)}
            resp = httpx.post(presigned_url, data=fields, files=files, timeout=60.0)
    else:
        with file_path.open("rb") as handle:
            resp = httpx.put(presigned_url, content=handle, headers={"Content-Type": mime}, timeout=60.0)
    resp.raise_for_status()
    log("   Upload completed.")


def complete_upload(client: httpx.Client, gateway_url: str, token: str, upload_id: str, group_id: str, visibility: str) -> dict:
    log("4. Notifying gateway upload completion...")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "upload_id": upload_id,
        "visibility": visibility,
    }
    if group_id:
        payload["group_id"] = group_id
    resp = client.post(f"{gateway_url}/api/v1/files/upload/complete", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    log("   Upload completion acknowledged.")
    return data


async def check_pgvector(database_url: str) -> None:
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for pgvector check.")
    if database_url.startswith("sqlite"):
        raise RuntimeError("pgvector check requires PostgreSQL (DATABASE_URL must not be sqlite).")
    log("5. Checking pgvector extension...")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        if result.first() is None:
            raise RuntimeError("pgvector extension not found. Run: CREATE EXTENSION IF NOT EXISTS vector;")
    await engine.dispose()
    log("   pgvector extension is installed.")


def format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


async def vectorize_document(database_url: str, file_path: Path) -> None:
    log("6. Parsing document and generating embedding...")
    from app.core.ingestion.ingestion_service import ingestion_service
    from app.services.embedding_service import embedding_service

    chunks = ingestion_service.process_file(str(file_path))
    if not chunks:
        raise RuntimeError("No extractable text from document.")
    sample_text = chunks[0].text.strip()
    if not sample_text:
        raise RuntimeError("First chunk is empty.")
    sample_text = sample_text[:2000]

    embedding = await embedding_service.get_embedding(sample_text)
    if not embedding:
        raise RuntimeError("Embedding generation returned empty result.")

    log("   Inserting embedding into smoke_document_vectors...")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    vector_literal = format_vector(embedding)
    dim = len(embedding)
    row_id = str(uuid.uuid4())
    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS smoke_document_vectors (
                id UUID PRIMARY KEY,
                file_name TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding VECTOR({dim}) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            INSERT INTO smoke_document_vectors (id, file_name, chunk_text, embedding)
            VALUES (:id, :file_name, :chunk_text, :embedding::vector)
        """), {
            "id": row_id,
            "file_name": file_path.name,
            "chunk_text": sample_text,
            "embedding": vector_literal,
        })
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM smoke_document_vectors WHERE id = :id
        """), {"id": row_id})
        count = result.scalar_one()
        if count != 1:
            raise RuntimeError("Failed to verify vector insert.")
    await engine.dispose()
    log("   Vector insert verified.")


async def run() -> int:
    args = parse_args()
    file_path, file_size, mime = load_file(args.file)

    if not args.skip_minio_check:
        check_minio(args.minio_health_url)

    if not args.skip_upload:
        with httpx.Client(timeout=20.0) as client:
            prepare = prepare_upload(client, args.gateway_url, args.token, file_path, file_size, mime)
            upload_to_storage(prepare["presigned_url"], prepare.get("fields"), file_path, mime)
            complete_upload(client, args.gateway_url, args.token, prepare["upload_id"], args.group_id, args.visibility)

    if not args.skip_pgvector_check:
        await check_pgvector(args.database_url)

    if not args.skip_vectorize:
        if not args.database_url:
            raise RuntimeError("DATABASE_URL is required for vectorization.")
        await vectorize_document(args.database_url, file_path)

    log("Stage 0 smoke test completed.")
    return 0


def main() -> None:
    try:
        start = time.time()
        code = asyncio.run(run())
        elapsed = time.time() - start
        log(f"Done in {elapsed:.2f}s.")
        raise SystemExit(code)
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
