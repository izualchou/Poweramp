# -*- coding: utf-8 -*-
"""PEQ 公共逻辑集中模块。

目的
----
消除 5 个 design_*.py 脚本（v1 / v2 / v3 / v4 / v5）之间的重复代码与硬编码常量，
统一接口以便扩展与维护。

包含三组内容
------------
1. 共享常量：FREQS / GRID_Q / PROFILE_DIR / EXPORT_DIR / 时间戳工具
2. 共享路径工厂：export_dir_for(version) / report_path_for(version, sub)
3. 共享 I/O 工具：write_json / write_text / ensure_dir
4. 设备元数据 re-export（来自 devices.py，保持向后兼容）

设计原则
--------
- 零行为变化：所有 v1-v5 脚本重构后输出必须 byte-identical
- 渐进迁移：各脚本可独立切换 import，未切换的脚本继续工作
- 单一来源：13 设备的元数据定义已抽到 devices.py（本模块 re-export 保持向后兼容）
- 扩展边界：版本业务字段（v1 r1/r2/r3、v2 filters、v3 pain/direction、v4 stream/unified、
  v5 新参数）仍保留在各版本脚本中（schema 差异过大，统一成本 > 收益）

依赖
----
pathlib / json / datetime（标准库）+ devices（设备元数据）
不依赖 peq_engine；本模块与 peq_engine 并列，被 design_*.py 引用
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================================
# 一、共享常量
# ============================================================================

# 1/3 倍频程 31 段 ISO 频栅（20Hz - 20kHz，标准中心频率）
# 严格对齐 GB/T 3241-2010 / IEC 61260-1（参见 skill references/freq-grids.md）
FREQS: list = [
    20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
    200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000,
]

# 1/3 倍频程本征 Q（Q = 1/(2^(1/6)-2^(-1/6)) ≈ 4.32）
# 各段近似独立、增益即滑条值（所见即所得）
GRID_Q: float = 4.32
DEFAULT_Q: float = GRID_Q  # 向后兼容别名

# 标准预增益裕度（dB）
PREAMP_MARGIN_DB: float = 0.5

# 标准路径
PROFILE_DIR: Path = Path("peq-profiles")
EXPORT_DIR: Path = Path("exports")


# ============================================================================
# 二、共享路径工厂
# ============================================================================

def export_dir_for(version: str) -> Path:
    """返回版本化导出目录。

    Args:
        version: 版本标识，如 "v1" / "v2" / "v3" / "v4" / "v5" / "31band"

    Returns:
        exports/<version>（v4 特有的流媒体/统一无损子结构由调用方处理）
    """
    return EXPORT_DIR / version


def report_path_for(version: str, sub: str) -> Path:
    """返回报告输出路径。

    Args:
        version: 版本标识
        sub: 子主题，如 "声学重设计" / "31段精细化" / "音源适配" / "综合调优"

    Returns:
        PEQ优化方案<version>-<sub>.md
    """
    return Path(f"PEQ优化方案{version}-{sub}.md")


# ============================================================================
# 三、共享 I/O 工具
# ============================================================================

def now_iso() -> str:
    """返回当前时间 ISO 字符串（秒级精度）。

    各脚本之前都是 `datetime.now().isoformat(timespec="seconds")`。
    """
    return datetime.now().isoformat(timespec="seconds")


def ensure_dir(path: Path) -> Path:
    """确保目录存在（递归创建），返回路径本身便于链式调用。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any, *, indent: int = 2, ensure_ascii: bool = False) -> Path:
    """统一 JSON 写入（ensure_ascii=False + 末尾换行）。

    原各脚本均使用：
        Path.write_text(json.dumps(..., ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    """
    path.write_text(
        json.dumps(data, ensure_ascii=ensure_ascii, indent=indent) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, content: str, *, newline: str = "\n") -> Path:
    """统一文本写入。"""
    path.write_text(content, encoding="utf-8", newline=newline)
    return path


# ============================================================================
# 四、设备元数据 re-export（保持向后兼容）
# ----------------------------------------------------------------------------
# 设备元数据已抽到独立 devices.py；本模块通过 re-export 让 5 脚本保持
# `from peq_common import DEVICE_REGISTRY, ...` 原写法不变（零破坏性变更）。
#
# 字段说明（详见 devices.py 文档字符串）
# --------
#   name          : 设备显示名
#   device_type   : 设备类型（iem_dynamic / iem_hybrid / portable_speaker / ...）
#   category      : 5 品类分类（IEM / Headphone / ANC / Portable / Phone / Car）
#   brand         : 品牌
#   model         : 型号 / 形态描述
#   hi_res_capable: 是否支持 Hi-Res 解析
#
# 衍生元数据（v1-v5 版本相关字段）保留在各版本脚本内：
#   v1: r1/r2/r3 调整 + narrow + analysis
#   v2: filters (PK/LSC/HSC) + why/fx
#   v3: pain/direction 文本
#   v4: target_stream/diff_stream/target_unified/diff_unified/conditions
#   v5: frontend_z_max_ohm/limiter/crossover_note/delay/compressor 等
# ============================================================================

# ruff: noqa: F401  （re-export 是有意为之）
from devices import (  # noqa: F401
    DEVICE_REGISTRY,
    CATEGORY_ORDER,
    DEVICE_TYPE_TO_CATEGORY,
    EXPECTED_DEVICE_COUNT,
    device_names,
    get_device,
    device_type_of,
    category_of,
    hi_res_capable_of,
    validate_device_coverage,
)
