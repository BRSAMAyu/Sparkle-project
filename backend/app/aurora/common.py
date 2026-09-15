"""Shared Aurora schema utilities and enum helpers."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict

EnumT = TypeVar("EnumT", bound=Enum)


class AuroraSchemaBase(BaseModel):
    """Base model for frozen Aurora schemas."""

    model_config = ConfigDict(extra="ignore", frozen=True)


def enum_values(enum_cls: type[EnumT]) -> list[str]:
    """Return the serialized values for an enum in declaration order."""

    return [member.value for member in enum_cls]


def enum_names(enum_cls: type[EnumT]) -> list[str]:
    """Return the member names for an enum in declaration order."""

    return [member.name for member in enum_cls]


def model_dump_json_safe(model: BaseModel) -> dict[str, Any]:
    """Dump a Pydantic model using JSON-safe values."""

    return model.model_dump(mode="json")
