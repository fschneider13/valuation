"""Lightweight Pydantic compatibility layer for offline environments."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type, TypeVar


T = TypeVar("T", bound="BaseModel")


class ValidationError(Exception):
    pass


@dataclass
class FieldInfo:
    default: Any = ...
    default_factory: Optional[Callable[[], Any]] = None
    description: Optional[str] = None


def Field(
    default: Any = ...,
    *,
    default_factory: Optional[Callable[[], Any]] = None,
    description: str | None = None,
    **_: Any,
) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory, description=description)


def _identity(type_: Any) -> Any:
    return type_


def conint(**_: Any) -> Type[int]:
    return int


def confloat(**_: Any) -> Type[float]:
    return float


class BaseModelMeta(type):
    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: Dict[str, Any]):
        annotations: Dict[str, Any] = {}
        field_infos: Dict[str, FieldInfo] = {}
        for base in bases:
            annotations.update(getattr(base, "__annotations__", {}))
            if hasattr(base, "_field_infos"):
                field_infos.update(getattr(base, "_field_infos"))
        annotations.update(namespace.get("__annotations__", {}))
        annotations = {k: v for k, v in annotations.items() if not k.startswith("_")}
        raw_defaults: Dict[str, Any] = {}
        for key, value in list(namespace.items()):
            if isinstance(value, FieldInfo):
                field_infos[key] = value
                namespace.pop(key)
            elif key in annotations:
                field_infos[key] = FieldInfo(default=value)
                raw_defaults[key] = value
        for key, annotation in annotations.items():
            field_infos.setdefault(key, FieldInfo())
        namespace["__annotations__"] = annotations
        namespace["_field_infos"] = field_infos
        cls = super().__new__(mcls, name, bases, namespace)
        return cls


class BaseModel(metaclass=BaseModelMeta):
    _field_infos: Dict[str, FieldInfo]

    def __init__(self, **data: Any) -> None:
        values: Dict[str, Any] = {}
        for name, info in self._field_infos.items():
            if name in data:
                values[name] = data[name]
            elif info.default is not ...:
                values[name] = info.default
            elif info.default_factory is not None:
                values[name] = info.default_factory()
            else:
                raise ValidationError(f"Field '{name}' is required for {self.__class__.__name__}")
        extra_keys = set(data.keys()) - set(self._field_infos.keys())
        for key in extra_keys:
            values[key] = data[key]
        for key, value in values.items():
            setattr(self, key, value)

    def copy(self: T, *, update: Optional[Dict[str, Any]] = None) -> T:
        values = {name: getattr(self, name) for name in self._field_infos.keys()}
        if update:
            values.update(update)
        return self.__class__(**values)

    def model_dump(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in self._field_infos.keys()}

    def __repr__(self) -> str:
        values = ", ".join(f"{name}={getattr(self, name)!r}" for name in self._field_infos.keys())
        return f"{self.__class__.__name__}({values})"

