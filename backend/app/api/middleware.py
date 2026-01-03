"""
API 中间件
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import iterate_in_threadpool

from app.core.idempotency import IdempotencyStore

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """幂等性中间件 - 防止重复处理"""
    
    # 需要幂等保护的路径前缀
    PROTECTED_PATHS = [
        "/api/v1/chat/stream",
        "/api/v1/tasks",
        "/api/v1/plans",
    ]
    
    def __init__(self, app, store: IdempotencyStore):
        super().__init__(app)
        self.store = store
        self._max_cache_bytes = 2 * 1024 * 1024
        self._max_sse_cache_bytes = 1024 * 1024

    def _extract_user_id(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return None
        try:
            from app.core.security import decode_token
            payload = decode_token(token, expected_type="access")
            return payload.get("sub")
        except Exception:
            return None

    async def _stream_with_cache(
        self,
        body_iterator,
        cache_key: str,
        status_code: int,
        content_type: str,
        user_id: str | None,
    ):
        collected = bytearray()
        try:
            async for chunk in body_iterator:
                if isinstance(chunk, str):
                    chunk_bytes = chunk.encode("utf-8")
                else:
                    chunk_bytes = chunk
                if len(collected) < self._max_sse_cache_bytes:
                    remaining = self._max_sse_cache_bytes - len(collected)
                    collected.extend(chunk_bytes[:remaining])
                yield chunk
        finally:
            if collected:
                await self.store.set(
                    cache_key,
                    {
                        "body": collected.decode("utf-8", errors="replace"),
                        "status_code": status_code,
                        "content_type": content_type,
                        "user_id": user_id,
                    },
                    ttl=3600,
                )
            await self.store.unlock(cache_key)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 仅对 POST/PUT/PATCH 请求检查幂等性
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)
        
        # 检查是否是受保护的路径
        if not any(request.url.path.startswith(p) for p in self.PROTECTED_PATHS):
            return await call_next(request)
        
        # 获取幂等键
        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)  # 无幂等键，正常处理
        
        user_id = self._extract_user_id(request)
        cache_key = f"{user_id}:{idempotency_key}" if user_id else idempotency_key

        # 检查是否已处理
        cached = await self.store.get(cache_key)
        if cached:
            content_type = cached.get("content_type") or "application/json"
            # 构造响应
            return Response(
                content=cached["body"].encode("utf-8") if isinstance(cached["body"], str) else cached["body"],
                status_code=cached.get("status_code", 200),
                headers={"X-Idempotency-Replayed": "true", "Content-Type": content_type},
                media_type=content_type,
            )
        
        # 标记为处理中（防止并发）
        # 注意: 这里的 lock 逻辑对于分布式环境需要更严谨 (如 Redis SETNX)
        if not await self.store.lock(cache_key):
            return Response(
                content='{"error": "Request is being processed"}',
                status_code=409,
                media_type="application/json"
            )
        
        unlock_in_finally = True
        try:
            # 执行实际请求
            response = await call_next(request)
            
            # 缓存响应（仅成功响应，且是非流式的 JSON 响应）
            # 注意: 流式响应 (SSE) 很难缓存整个 body，除非我们收集它。
            # 对于 /chat/stream，通常我们不缓存流内容，或者我们需要特殊处理。
            # 文档中提到 /chat/stream 也在保护列表中。
            # 如果是流式响应，response.body_iterator 是一个 generator。
            # 我们需要 hook 它。
            
            if 200 <= response.status_code < 300:
                # 检查是否是流式响应
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    unlock_in_finally = False
                    response.body_iterator = self._stream_with_cache(
                        response.body_iterator,
                        cache_key,
                        response.status_code,
                        content_type,
                        user_id,
                    )
                    return response
                else:
                    # 普通 JSON 响应
                    response_body = [section async for section in response.body_iterator]
                    response.body_iterator = iterate_in_threadpool(iter(response_body))
                    body = b"".join(response_body)
                    if len(body) <= self._max_cache_bytes:
                        await self.store.set(
                            cache_key,
                            {
                                "body": body.decode("utf-8", errors="replace"),
                                "status_code": response.status_code,
                                "content_type": content_type or "application/json",
                                "user_id": user_id,
                            },
                            ttl=3600,
                        )
            
            return response
            
        finally:
            if unlock_in_finally:
                await self.store.unlock(cache_key)
