"""
API 中间件
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import iterate_in_threadpool
import json

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
        
        # 检查是否已处理
        cached = await self.store.get(idempotency_key)
        if cached:
            # 构造响应
            return Response(
                content=cached["body"].encode() if isinstance(cached["body"], str) else cached["body"],
                status_code=cached["status_code"],
                headers={"X-Idempotency-Replayed": "true", "Content-Type": "application/json"},
                media_type="application/json"
            )
        
        # 标记为处理中（防止并发）
        # 注意: 这里的 lock 逻辑对于分布式环境需要更严谨 (如 Redis SETNX)
        if not await self.store.lock(idempotency_key):
            return Response(
                content='{"error": "Request is being processed"}',
                status_code=409,
                media_type="application/json"
            )
        
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
                    # 流式响应暂不缓存 body (或者需要更复杂的逻辑)
                    # 仅标记为处理完成?
                    # 文档示例代码: 
                    # async for chunk in response.body_iterator:
                    #    body += chunk
                    # 这意味着它会消耗流，导致流无法传给客户端，除非重新构造流。
                    # 或者 call_next 返回的 response 还没开始发送?
                    # Starlette 的 response.body_iterator 一旦消耗就没了。
                    # 我们需要 iterate 并且 yield back。
                    
                    async def body_iterator_wrapper():
                        full_body = b""
                        async for chunk in response.body_iterator:
                            full_body += chunk
                            yield chunk
                        
                        # 只有在完整接收后才 set (但流式是实时的，这会延迟吗? 不会，因为我们是 yield chunk)
                        # 但 set 是 async 的，这里是在 generator 里。
                        # 我们可以在后台任务中 set? 
                        # 或者我们只是不缓存流式响应体，只防并发?
                        
                        # 文档代码示例确实读取了 body。
                        # "async for chunk in response.body_iterator: body += chunk"
                        # 这会阻塞流直到结束吗? 是的，如果是在 return Response 之前。
                        # 但这里是 return Response(content=body...)，这会变成非流式!
                        # 对于 SSE，这绝对不行。
                        pass

                    # 如果是 SSE，我们跳过缓存 body? 或者我们需要一种机制来"旁路"记录。
                    # 鉴于 SSE 是为了实时性，把整个 body 读完再发给客户端就失去了 SSE 的意义。
                    # 文档中的示例代码可能主要针对普通 API。
                    # 针对 SSE，我们可能只需要 lock 防并发，或者仅缓存"Done"状态?
                    # 
                    # 让我们先对非流式做完整缓存。
                    # 对 SSE，我们可能跳过缓存 body，或者需要特殊处理。
                    
                    # 简单起见，如果是 event-stream，我们先不缓存 body，只 unlock。
                    pass
                else:
                    # 普通 JSON 响应
                    response_body = [section async for section in response.body_iterator]
                    response.body_iterator = iterate_in_threadpool(iter(response_body))
                    body = b"".join(response_body)
                    
                    await self.store.set(
                        idempotency_key,
                        {"body": body.decode("utf-8"), "status_code": response.status_code},
                        ttl=3600  # 1小时过期
                    )
            
            return response
            
        finally:
            await self.store.unlock(idempotency_key)
