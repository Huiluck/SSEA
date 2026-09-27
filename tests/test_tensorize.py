"""tensorize 测试 —— 协议向量与张量之间的唯一边界。"""

from __future__ import annotations

import pytest
import torch

from SSEA.tensorize import as_vector


class TestAcceptsBothForms:
    """协议原产物是 tuple，测试里常直接传张量——两种都收。"""

    def test_tuple_becomes_tensor(self) -> None:
        v = as_vector((0.1, 0.2, 0.3))
        assert isinstance(v, torch.Tensor)
        assert v.dtype == torch.float32
        assert v.shape == (3,)

    def test_list_becomes_tensor(self) -> None:
        v = as_vector([1, 2, 3, 4])
        assert v.shape == (4,)
        assert v.dtype == torch.float32

    def test_tensor_is_flattened(self) -> None:
        v = as_vector(torch.zeros(2, 3))
        assert v.shape == (6,)

    def test_int_tensor_is_cast_to_float(self) -> None:
        v = as_vector(torch.tensor([1, 2, 3]))
        assert v.dtype == torch.float32


class TestDimensionChecking:
    def test_correct_dim_passes(self) -> None:
        assert as_vector((0.1, 0.2), expected=2).numel() == 2

    def test_wrong_dim_raises_with_field_name(self) -> None:
        """报错必须指出是哪个字段——GRU 内部的维度错误离病因很远。"""

        with pytest.raises(ValueError, match="internal_drive 维度不符"):
            as_vector((0.1,), expected=4, name="internal_drive")

    def test_no_expected_means_no_check(self) -> None:
        assert as_vector((1.0, 2.0, 3.0, 4.0, 5.0)).numel() == 5


class TestNoHiddenTransforms:
    """边界只做类型转换，不做归一化 / 裁剪——那是模型策略。"""

    def test_values_pass_through_unchanged(self) -> None:
        raw = (-5.0, 0.0, 100.0)
        out = as_vector(raw)
        assert out.tolist() == list(raw)

    def test_out_of_range_values_are_not_clipped(self) -> None:
        out = as_vector((99.0, -99.0))
        assert out.abs().max() == pytest.approx(99.0)


class TestGradientPreservation:
    def test_tensor_keeps_its_graph(self) -> None:
        """传进来的张量若带梯度，不能被 detach 掉。"""

        t = torch.tensor([1.0, 2.0], requires_grad=True)
        out = as_vector(t)
        out.sum().backward()
        assert t.grad is not None
        assert torch.isfinite(t.grad).all()
