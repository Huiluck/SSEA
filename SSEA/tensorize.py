"""协议向量 → 张量。模型边界的唯一转换点。

**为什么单独一个模块**：``sse_protocols`` 约定 2 明确「向量用
``tuple[float, ...]``，不用 numpy/torch」——协议必须可序列化、可 diff、
可跨进程。但模型层（State Core / Action Decoder）收的是张量。

边界就在此处，且**只在此处**。这不是洁癖：若每个模型各自写一遍
``torch.tensor(value)``，"协议是接口、张量化发生在边界"这条约定就散落在
六个文件里，将来改协议表示（比如换成 ``array.array``）时要找六处。

不提供的转换
------------
- 不做归一化 / 裁剪。那是模型策略，不是边界职责。
- 不处理嵌套结构。协议向量都是扁平的 ``tuple[float, ...]``。
"""

from __future__ import annotations

from collections.abc import Sequence

import torch


def as_vector(
    value: Sequence[float] | torch.Tensor,
    *,
    expected: int | None = None,
    name: str = "vector",
) -> torch.Tensor:
    """协议向量或张量 → 1D float32 张量。

    参数
    ----
    value:
        协议原产物（``tuple[float, ...]``）或已是张量。两种都接受是有意的：
        测试里常直接传张量，而生产路径传协议对象。
    expected:
        期望长度。给出时长度不符立即报错——静默截断或补零会让
        "模型收到了错维度的输入"这种错误延迟到 GRU 内部才暴露，
        而那里的报错信息与真正的病因相距很远。
    name:
        报错信息里用的字段名。
    """

    if isinstance(value, torch.Tensor):
        out = value.reshape(-1).to(dtype=torch.float32)
    else:
        out = torch.tensor(tuple(value), dtype=torch.float32)

    if expected is not None and out.numel() != expected:
        raise ValueError(
            f"{name} 维度不符：得到 {out.numel()}，期望 {expected}"
        )
    return out
