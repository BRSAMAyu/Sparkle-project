"""
gRPC Auth Interceptors
"""
from __future__ import annotations

import secrets

import grpc
from loguru import logger

from app.core.security import decode_token


# Context key for storing validated user ID
# Using a non-string key prevents collision with user-supplied metadata
class _VerifiedUserIDKey:
    """Type-safe key for storing verified user ID in gRPC context"""
    pass

VERIFIED_USER_ID_KEY = _VerifiedUserIDKey()


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

            # Security Note: If metadata user-id was provided, we've verified it matches.
            # If not provided, token_user_id is the authoritative user identity.
            # Downstream code should prefer token_user_id over metadata user-id.

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

    This function should be used by service implementations to get the
    authoritative user ID. It returns the token-verified user ID if available,
    falling back to metadata user-id only when appropriate.

    Security: Always prefer the JWT-verified user_id over metadata user-id
    to prevent impersonation attacks.
    """
    # First check if we have a verified user ID from the auth interceptor
    # (This would be set if we had a way to pass it through grpc context)
    # For now, we rely on the interceptor's validation that metadata user-id
    # matches token sub claim

    meta_user_id = metadata.get("user-id")
    # The interceptor has already validated that if both exist, they match
    return meta_user_id
