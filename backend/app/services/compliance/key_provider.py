import base64
import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger


class MasterKeyProvider(ABC):
    @abstractmethod
    def get_master_key(self) -> bytes:
        pass


class LocalKeyProvider(MasterKeyProvider):
    def get_master_key(self) -> bytes:
        raw = os.getenv("PERSONA_MASTER_KEY", "insecure-dev-key")
        return hashlib.sha256(raw.encode("utf-8")).digest()


class AwsKmsKeyProvider(MasterKeyProvider):
    def __init__(self):
        self.ciphertext = os.getenv("PERSONA_MASTER_KEY_CIPHERTEXT")
        self.region = os.getenv("AWS_REGION")

    def get_master_key(self) -> bytes:
        if not self.ciphertext:
            raise ValueError("PERSONA_MASTER_KEY_CIPHERTEXT is required for aws_kms provider")
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for aws_kms provider") from exc

        client = boto3.client("kms", region_name=self.region)
        blob = base64.b64decode(self.ciphertext.encode("ascii"))
        response = client.decrypt(CiphertextBlob=blob)
        return response["Plaintext"]


class VaultKeyProvider(MasterKeyProvider):
    def __init__(self):
        self.addr = os.getenv("VAULT_ADDR")
        self.token = os.getenv("VAULT_TOKEN")
        self.secret_path = os.getenv("VAULT_SECRET_PATH", "secret/data/persona")
        self.secret_key = os.getenv("VAULT_SECRET_KEY", "persona_master_key")

    def get_master_key(self) -> bytes:
        if not self.addr or not self.token:
            raise ValueError("VAULT_ADDR and VAULT_TOKEN are required for vault provider")
        try:
            import hvac
        except ImportError as exc:
            raise RuntimeError("hvac is required for vault provider") from exc

        client = hvac.Client(url=self.addr, token=self.token)
        secret = client.secrets.kv.v2.read_secret_version(path=self.secret_path)
        value = secret["data"]["data"].get(self.secret_key)
        if not value:
            raise ValueError("Vault secret key not found")
        return hashlib.sha256(value.encode("utf-8")).digest()


def get_master_key_provider() -> MasterKeyProvider:
    provider = os.getenv("PERSONA_KEY_PROVIDER", "local").lower()
    if provider == "aws_kms":
        logger.info("Using AWS KMS master key provider")
        return AwsKmsKeyProvider()
    if provider == "vault":
        logger.info("Using Vault master key provider")
        return VaultKeyProvider()
    return LocalKeyProvider()
