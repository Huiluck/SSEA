"""协议序列化 —— JSON 往返。

**验收依据**：docs/07-ssea-v0.3.1-charter.md §11 Milestone 1
「所有接口可序列化为 JSON」。

编码规则
--------
===========================  ============================================
协议类型                     JSON 表示
===========================  ============================================
dataclass（有类型标注）       object（无标记）
dataclass（在无类型容器内）   ``{"__dataclass__": "<限定名>", ...字段}``
``bytes``                    ``{"__bytes__": "<base64>"}``
tuple / list                 array
Mapping                      object
None / str / int / float    原样
===========================  ============================================

两个设计选择
------------

**bytes 包一层**，不裸 base64。协议里有三处 bytes
（``GenePackage.core_weights`` / ``instinct_adapters`` / Structure Store 的
adapters），裸字符串会让"这本来是 bytes"这个信息丢失，反序列化时无法区分
"一个恰好长得像 base64 的 str" 与 "bytes"。

**编码器是类型导向的**，与解码器使用同一份类型信息。原因是协议里有**无类型
容器**：``SelfModificationProposal.payload``、Structure Store 的 ``rules`` /
``retrieval`` 都是裸 ``dict``，里面可能装着 ``Skill``。若无类型容器内的
dataclass 不带标记，反序列化只能还原成普通 dict，往返不再保真——
而这直接违背 Milestone 1 的验收第 1 条。故：有类型标注处用简洁形式，
无类型容器内用带标记形式。两者解码逻辑统一。

设计边界
--------
本模块只处理**协议对象**。它不做版本迁移——基因包的格式版本属于
Gene Manager（Milestone 4）的职责，不属于协议层。
"""

from __future__ import annotations

import base64
import collections.abc as abc
import dataclasses
import importlib
import typing
from typing import Any, get_type_hints

#: bytes 的 JSON 包装键。
BYTES_KEY = "__bytes__"

#: 无类型容器内 dataclass 的标记键。
DATACLASS_KEY = "__dataclass__"


# ----------------------------------------------------------------------
#  编码：协议对象 → JSON 可序列化结构
# ----------------------------------------------------------------------


def to_json_dict(obj: Any) -> Any:
    """把协议对象转为可 ``json.dumps`` 的结构。

    入口传入对象自身类型作 hint，故顶层是**无标记**的简洁形式；
    只有无类型容器（如 ``payload``）内的 dataclass 才带标记。
    """

    return _encode(obj, type(obj))


def _encode(value: Any, hint: Any) -> Any:
    """按字段类型标注编码 value。hint 为 Any 时进入"无类型容器"分支。"""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (bytes, bytearray)):
        return {BYTES_KEY: base64.b64encode(bytes(value)).decode("ascii")}

    hint = _unwrap_optional(hint)

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        # 有类型标注：简洁形式。无类型标注：带标记形式。
        tagged = not (dataclasses.is_dataclass(hint) and hint is type(value))
        out: dict[str, Any] = {}
        if tagged:
            out[DATACLASS_KEY] = _qualname(type(value))
        hints = get_type_hints(type(value))
        for f in dataclasses.fields(value):
            out[f.name] = _encode(getattr(value, f.name), hints.get(f.name, Any))
        return out

    origin = typing.get_origin(hint)
    args = typing.get_args(hint)

    # **比的是 collections.abc.Mapping，不是 typing.Mapping。**
    # 这里曾写 ``origin in (dict, typing.Mapping)``，而那句对 Mapping 永远为假：
    # ``typing.get_origin(Mapping[str, Any])`` 返回的是
    # ``collections.abc.Mapping``，与 ``typing.Mapping`` 既不 ``is`` 也不 ``==``。
    # 于是这个分支对**带 Mapping 标注的字段从来没生效过**，实际生效的是下面
    # 「无类型容器」那条 ``isinstance(value, dict)``——它拿 ``Any`` 当值的 hint，
    # **把标注里的值类型静默丢掉了**（``Mapping[str, Skill]`` 被当成
    # ``Mapping[str, Any]`` 编码）。2026-09-28 给快照字段包 ``MappingProxyType``
    # 时暴露出来：``isinstance(mappingproxy, dict)`` 为假，序列化直接 TypeError，
    # 撞坏了 07 §11「所有接口可序列化为 JSON」。两处一并修。
    if origin in (dict, abc.Mapping) or hint in (dict, abc.Mapping):
        val_hint = args[1] if len(args) == 2 else Any
        return {str(k): _encode(v, val_hint) for k, v in value.items()}

    if origin in (tuple, list) or hint in (tuple, list):
        item_hint = args[0] if args else Any
        return [_encode(v, item_hint) for v in value]

    # 无类型容器。**认 Mapping 而不是 dict**：协议层的契约是「可序列化」，
    # 不该因为调用方用了 Mapping 的别的实现（如 MappingProxyType）就报错。
    if isinstance(value, abc.Mapping):
        return {str(k): _encode(v, Any) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_encode(v, Any) for v in value]

    raise TypeError(f"协议层无法序列化类型 {type(value).__name__}: {value!r}")


def _qualname(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


# ----------------------------------------------------------------------
#  解码：JSON 结构 → 协议对象
# ----------------------------------------------------------------------


def _is_bytes_wrapper(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {BYTES_KEY}
        and isinstance(value[BYTES_KEY], str)
    )


def _is_tagged_dataclass(value: Any) -> bool:
    return isinstance(value, dict) and DATACLASS_KEY in value


def _resolve_class(qualname: str) -> type:
    module_name, _, cls_name = qualname.rpartition(".")
    module = importlib.import_module(module_name)
    cls = getattr(module, cls_name, None)
    if cls is None or not dataclasses.is_dataclass(cls):
        raise TypeError(f"标记指向的类不存在或不是 dataclass: {qualname}")
    return cls


def _unwrap_optional(hint: Any) -> Any:
    """``X | None`` → ``X``。非 Optional 原样返回。"""

    args = typing.get_args(hint)
    if args and type(None) in args:
        return next(a for a in args if a is not type(None))
    return hint


def _decode(value: Any, hint: Any) -> Any:
    """按字段类型标注还原 value。"""

    if value is None:
        return None
    if _is_bytes_wrapper(value):
        return base64.b64decode(value[BYTES_KEY])

    hint = _unwrap_optional(hint)

    # 带标记的 dataclass：类型来自标记本身，覆盖 hint
    if _is_tagged_dataclass(value):
        cls = _resolve_class(value[DATACLASS_KEY])
        return _decode_dataclass(cls, value)

    origin = typing.get_origin(hint)
    args = typing.get_args(hint)

    # Mapping[str, X] / dict[str, X]
    if origin in (dict, typing.Mapping) or hint in (dict, typing.Mapping):
        val_hint = args[1] if len(args) == 2 else Any
        return {str(k): _decode(v, val_hint) for k, v in value.items()}

    # tuple[X, ...] / list[X]
    if origin in (tuple, list) or hint in (tuple, list):
        item_hint = args[0] if args else Any
        return tuple(_decode(v, item_hint) for v in value)

    # 有类型标注的 dataclass：简洁形式
    if dataclasses.is_dataclass(hint) and isinstance(value, dict):
        return _decode_dataclass(hint, value)

    # 无类型容器
    if isinstance(value, dict):
        return {k: _decode(v, Any) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v, Any) for v in value]
    return value


def _decode_dataclass(cls: type, data: dict[str, Any]) -> Any:
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        kwargs[f.name] = _decode(data[f.name], hints.get(f.name, Any))
    return cls(**kwargs)


def from_json_dict(cls: type, data: dict[str, Any]) -> Any:
    """把 ``json.loads`` 的结果还原为 ``cls`` 实例。"""

    if not dataclasses.is_dataclass(cls):
        raise TypeError(f"{cls.__name__} 不是 dataclass")
    if _is_tagged_dataclass(data):
        return _decode_dataclass(_resolve_class(data[DATACLASS_KEY]), data)
    return _decode_dataclass(cls, data)


# ----------------------------------------------------------------------
#  往返自检
# ----------------------------------------------------------------------


def roundtrip(obj: Any) -> Any:
    """obj → JSON → 同类型新对象。用于测试。"""
    import json

    return from_json_dict(type(obj), json.loads(json.dumps(to_json_dict(obj))))
