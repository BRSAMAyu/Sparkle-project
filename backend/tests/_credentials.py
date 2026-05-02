"""Centralized mock credentials for tests — never use real keys in test code.

Import from this module instead of hardcoding string literals, so that
credential values can be updated in a single place.
"""

# Internal API authentication
TEST_INTERNAL_API_KEY = "test-internal-api-key"

# LLM / OCR / STT provider mock keys
TEST_ZHIPU_API_KEY = "test-zhipu-api-key"
TEST_SF_API_KEY = "test-sf-api-key"
TEST_HY_API_KEY = "test-hy-api-key"
TEST_XUNFEI_API_KEY = "test-xunfei-api-key"
TEST_XUNFEI_API_SECRET = "test-xunfei-api-secret"

# Hashed password placeholder for User fixtures
TEST_HASHED_PASSWORD = "hashed"
