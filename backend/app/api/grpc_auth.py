"""
gRPC Auth Interceptors
"""
from __future__ import annotations

import contextvars
import secrets

import grpc
from loguru import logger

from app.core.security import decode_token

# Context variable to track auth type for the current gRPC call
_grpc_auth_type: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_grpc_auth_type", default="none"
)
_grpc_verified_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_grpc_verified_user_id", default=None
)


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """
    gRPC Server Interceptor for JWT Authentication
    Handles both string and bytes metadata keys/values

    Security: Validates user-id metadata against JWT token sub claim
    to prevent user impersonation attacks.
    """

    async def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        if "grpc.reflection" in method:
            return await continuation(handler_call_details)

        # Normalize metadata to string keys and values
        metadata = {}
        for k, v in handler_call_details.invocation_metadata:
            key = k.decode('utf-8') if isinstance(k, bytes) else k
            val = v.decode('utf-8') if isinstance(v, bytes) else v
            metadata[key.lower()] = val

        auth_header = metadata.get("authorization")
        meta_user_id = metadata.get("user-id")

        # Allow internal service-to-service communication with INTERNAL_API_KEY
        internal_api_key = metadata.get("x-internal-api-key")

        # Check for Internal API Key (Service-to-Service)
        if internal_api_key:
            from app.config import settings
            # Security: Use constant-time comparison to prevent timing attacks
            if settings.INTERNAL_API_KEY and secrets.compare_digest(
                internal_api_key, settings.INTERNAL_API_KEY
            ):
                # Internal service-to-service: skip user-id validation
                # (internal services are trusted)
                _grpc_auth_type.set("s2s")
                _grpc_verified_user_id.set(meta_user_id)
                return await continuation(handler_call_details)
            else:
                logger.warning(f"INVALID INTERNAL KEY in gRPC call to {method}")
                return self._abort(grpc.StatusCode.UNAUTHENTICATED, "内部API密钥无效")

        # Fallback to User Token Authentication
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"UNAUTHORIZED gRPC call to {method} - Missing or invalid header")
            return self._abort(grpc.StatusCode.UNAUTHENTICATED, "缺少或无效的授权头信息")

        token = auth_header.split(" ")[1]
        try:
            # Decode token and extract user_id (sub claim)
            payload = await decode_token(token, expected_type="access")
            token_user_id = payload.get("sub")

            # Security: Validate metadata user-id matches JWT sub claim
            # This prevents user impersonation attacks where a malicious client
            # could set user-id metadata to impersonate another user
            if meta_user_id and token_user_id and meta_user_id != token_user_id:
                logger.warning(
                    f"SECURITY: User-ID mismatch in gRPC call to {method} - "
                    f"metadata user-id={meta_user_id} does not match token sub={token_user_id}"
                )
                return self._abort(grpc.StatusCode.PERMISSION_DENIED, "用户身份验证失败")

            _grpc_auth_type.set("user")
            _grpc_verified_user_id.set(token_user_id or meta_user_id)
            return await continuation(handler_call_details)
        except Exception as e:
            logger.warning(f"INVALID TOKEN in gRPC call to {method}: {e}")
            return self._abort(grpc.StatusCode.UNAUTHENTICATED, "令牌无效或已过期")

    def _abort(self, code, details):
        async def abort_call(request, context):
            await context.abort(code, details)
        return grpc.unary_unary_rpc_method_handler(abort_call)


def get_verified_user_id(metadata: dict[str, str]) -> str | None:
    """
    Get the verified user ID from request.

    Returns the JWT-verified user_id for user-authenticated calls.
    For S2S calls, returns metadata user-id (set by trusted internal service).
    Use get_grpc_auth_type() to distinguish the trust level.
    """
    verified = _grpc_verified_user_id.get()
    if verified is not None:
        return verified
    return metadata.get("user-id")


def get_grpc_auth_type() -> str:
    """Return 'user' for JWT-authenticated calls, 's2s' for internal, 'none' otherwise."""
    return _grpc_auth_type.get()
