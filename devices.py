# -*- coding: utf-8 -*-
"""PEQ 设备元数据单一数据源。

目的
----
将 12 设备 6 品类 6 字段（name / device_type / category / brand / model / hi_res_capable）
集中到独立模块，与 peq_common 的"通用工具"职责分离：

  devices.py     →  设备元数据 + 查询函数（THIS）
  peq_common.py  →  通用常量 + 路径 + I/O（并 re-export 本模块 API）

设计原则
--------
- **单一来源**：12 设备的 6 字段只在此处定义一次；5 脚本通过 re-export 间接访问
- **向后兼容**：通过 peq_common.py 的 re-export，5 脚本保持 `from peq_common import DEVICE_REGISTRY`
  原写法不变，避免破坏性变更
- **最小迁移**：本模块只承担 6 字段 + 查询函数；版本业务字段（v1 r1/r2/r3、v2 filters、
  v3 pain/direction、v4 stream/unified、v5 新参数）保留在各版本脚本中
  - 原因：5 脚本 schema 差异大（v1 三轮迭代 / v2 滤波器组 / v3 痛点文本 / v4 音源变体 /
    v5 综合调优），统一成本 > 收益
  - 例外：v4 的 `hi_res_capable` 字段已迁入本模块（13 行 → 1 行调用 `hi_res_capable_of`）

字段说明
--------
- name          : 设备显示名（5 脚本档案名以此为基准；与 v3 设备名前缀匹配）
- device_type   : 设备类型（iem_dynamic / iem_hybrid / portable_speaker / ...）
- category      : 5 品类（IEM / Headphone / ANC / Portable / Phone / Car）
- brand         : 品牌（声学依据来源，引用 声学特点.txt 对应章节）
- model         : 型号（细分型号 / 形态描述）
- hi_res_capable: 是否支持 Hi-Res 解析（有线 IEM/HP 默认 True；蓝牙/手机/便携/车载 False）

依赖
----
不依赖 peq_common 或 peq_engine；标准库 only
被 peq_common re-export，被 design_*.py 间接使用
"""

from __future__ import annotations

from typing import Tuple


# ============================================================================
# 设备元数据（12 设备 × 6 字段）
# ============================================================================

DEVICE_REGISTRY: dict = {
    # ==================== 入耳式 IEM ====================
    "IE900复刻版": {
        "device_type": "iem_dynamic",
        "category": "IEM",
        "brand": "Sennheiser复刻",
        "model": "IE900 style（7mm 动圈 / 32Ω / 5Hz-48kHz / 123dB）",
        "hi_res_capable": True,
    },
    "BGVP Scale Pro": {
        "device_type": "iem_hybrid",
        "category": "IEM",
        "brand": "BGVP",
        "model": "Scale Pro（1DD+1BA HVEK / 17Ω / 113dB/mW）",
        "hi_res_capable": True,
    },
    "1圈14铁耳机": {
        "device_type": "iem_hybrid",
        "category": "IEM",
        "brand": "qdc风格",
        "model": "1DD+14BA+EST / 12-20Ω / 105-108dB/mW",
        "hi_res_capable": True,
    },
    # ==================== 头戴式耳机 ====================
    "HD800耳机": {
        "device_type": "open_headphone",
        "category": "Headphone",
        "brand": "Sennheiser",
        "model": "HD800（56mm 环形动圈 / 300Ω / 102dB/Vrms）",
        "hi_res_capable": True,
    },
    "Sony MDR-1ABT": {
        "device_type": "bluetooth_headphone",
        "category": "Headphone",
        "brand": "Sony",
        "model": "MDR-1ABT（40mm 镀铝 LCP / 24Ω / 98dB）",
        "hi_res_capable": False,  # BT 4.0 LDAC 上限 96k/24bit
    },
    "Bose QC 45": {
        "device_type": "bluetooth_headphone",
        "category": "ANC",
        "brand": "Bose",
        "model": "QC 45（BT 5.1 + ANC）",
        "hi_res_capable": False,  # BT + ANC 物理/算法双重上限
    },
    # ==================== 便携音箱 ====================
    "Sony XB12双音箱组合": {
        "device_type": "portable_speaker",
        "category": "Portable",
        "brand": "Sony",
        "model": "SRS-XB12 x2 立体声配对（46mm + 被动辐射器）",
        "hi_res_capable": False,
    },
    # ==================== 手机扬声器 ====================
    "Samsung S25 Plus手机扬声器": {
        "device_type": "phone_speaker",
        "category": "Phone",
        "brand": "Samsung",
        "model": "Galaxy S25+（AKG调校立体声 / 超薄机身）",
        "hi_res_capable": False,
    },
    "OPPO A5 4G手机扬声器": {
        "device_type": "phone_speaker",
        "category": "Phone",
        "brand": "OPPO",
        "model": "A5 4G（底部主扬声器）",
        "hi_res_capable": False,
    },
    # ==================== 蓝牙降噪耳机 ====================
    "Ugreen Hitune T8降噪耳机": {
        "device_type": "bluetooth_headphone",
        "category": "ANC",
        "brand": "Ugreen",
        "model": "Hitune T8（12.4mm 镀钛振膜 / ANC -55dB）",
        "hi_res_capable": False,  # BT 带宽限制
    },
    # ==================== 车载音响 ====================
    "Micra K13车载音响": {
        "device_type": "car_audio",
        "category": "Car",
        "brand": "Nissan",
        "model": "Micra K13 原厂 4 全频扬声器（4Ω / 90-93dB）",
        "hi_res_capable": False,
    },
    "Nissan X-Trail车载音响": {
        "device_type": "car_audio",
        "category": "Car",
        "brand": "Nissan",
        "model": "X-Trail 原厂 6 扬声器（被动 2 分频 / 20W 额定）",
        "hi_res_capable": False,
    },
}


# 品类排序（IEM → Headphone → ANC → Portable → Phone → Car）
CATEGORY_ORDER: dict = {
    "IEM": 0, "Headphone": 1, "ANC": 2, "Portable": 3, "Phone": 4, "Car": 5,
}


# 设备类型 → 品类反查（来自 skill references/device-profiles.md）
DEVICE_TYPE_TO_CATEGORY: dict = {
    "iem_dynamic": "IEM",
    "iem_hybrid": "IEM",
    "open_headphone": "Headphone",
    "closed_headphone": "Headphone",
    "bluetooth_headphone": "ANC",  # 蓝牙耳机默认归 ANC 类（含非 ANC 的 TWS）
    "portable_speaker": "Portable",
    "phone_speaker": "Phone",
    "car_audio": "Car",
}


# 设备总数（用于交叉验证 v1-v5 脚本）
EXPECTED_DEVICE_COUNT: int = 12


# ============================================================================
# 查询函数
# ============================================================================

def device_names(sort_by_category: bool = True) -> list:
    """返回 12 设备名列表。

    Args:
        sort_by_category: True 按品类排序（IEM→Headphone→ANC→Portable→Phone→Car），
                         False 按字典序
    """
    if not sort_by_category:
        return list(DEVICE_REGISTRY.keys())
    return sorted(
        DEVICE_REGISTRY.keys(),
        key=lambda n: (CATEGORY_ORDER.get(DEVICE_REGISTRY[n]["category"], 99), n),
    )


def get_device(name: str) -> dict:
    """查表返回设备元数据；不存在时抛 KeyError。"""
    return DEVICE_REGISTRY[name]


def device_type_of(name: str) -> str:
    """便捷方法：返回设备的 device_type。"""
    return DEVICE_REGISTRY[name]["device_type"]


def category_of(name: str) -> str:
    """便捷方法：返回设备的 category。"""
    return DEVICE_REGISTRY[name]["category"]


def hi_res_capable_of(name: str) -> bool:
    """便捷方法：返回设备是否支持 Hi-Res 解析。"""
    return bool(DEVICE_REGISTRY[name]["hi_res_capable"])


def validate_device_coverage(claimed_names: list) -> Tuple[list, list]:
    """验证 claimed_names 是否覆盖全部 12 设备。

    Args:
        claimed_names: 5 脚本中声明的设备名清单

    Returns:
        (missing, extra) - claimed 中缺失的设备 + 多出的设备
    """
    expected = set(DEVICE_REGISTRY.keys())
    actual = set(claimed_names)
    return sorted(expected - actual), sorted(actual - expected)


__all__ = [
    "DEVICE_REGISTRY",
    "CATEGORY_ORDER",
    "DEVICE_TYPE_TO_CATEGORY",
    "EXPECTED_DEVICE_COUNT",
    "device_names",
    "get_device",
    "device_type_of",
    "category_of",
    "hi_res_capable_of",
    "validate_device_coverage",
]
