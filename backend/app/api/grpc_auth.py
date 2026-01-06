"""
gRPC Auth Interceptors
"""
import grpc
from loguru import logger
from app.core.security import decode_token

class AuthInterceptor(grpc.aio.ServerInterceptor):
    """
    gRPC Server Interceptor for JWT Authentication
    Handles both string and bytes metadata keys/values
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

        # Allow internal service-to-service communication with INTERNAL_API_KEY
        internal_api_key = metadata.get("x-internal-api-key")
        
        # Check for Internal API Key (Service-to-Service)
        if internal_api_key:
            from app.config import settings
            if internal_api_key == settings.INTERNAL_API_KEY:
                return await continuation(handler_call_details)
            else:
                 logger.warning(f"INVALID INTERNAL KEY in gRPC call to {method}")
                 return self._abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid internal API key")

        # Fallback to User Token Authentication
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"UNAUTHORIZED gRPC call to {method} - Missing or invalid header")
            return self._abort(grpc.StatusCode.UNAUTHENTICATED, "Missing or invalid authorization header")

        token = auth_header.split(" ")[1]
        try:
            decode_token(token, expected_type="access")
            return await continuation(handler_call_details)
        except Exception as e:
            logger.warning(f"INVALID TOKEN in gRPC call to {method}: {e}")
            return self._abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired token")

    def _abort(self, code, details):
        async def abort_call(request, context):
            await context.abort(code, details)
        return grpc.unary_unary_rpc_method_handler(abort_call)
