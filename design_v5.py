# -*- coding: utf-8 -*-
"""v5：12 设备综合调优（PEQ + 分频 + 增益 + 延迟 + 动态处理）。

以 v4统一无损 31 段 PEQ 为基础（继承），新增 4 维度：

1. **分频 (crossover)**：多驱动扬声器的分频点 / 斜率 / 物理位置 / EQ 补偿方式
2. **增益 (gain)**：通道平衡 + 前端输出阻抗建议 + 驱动单元电平匹配
3. **延迟 (delay)**：多驱动单元的时间对齐（毫秒级，主用于车载）
4. **动态 (dynamics)**：压缩器 (compressor) + 限幅器 (limiter)；按单元裕量差异化

适用场景：
  - 车载音响（K13 / X-Trail）：分频延迟动态全用，重点升级
  - 便携音箱 / 复刻 IEM：仅限幅器（保护）
  - 单驱动 HP：所有新参数 N/A 或仅前端建议
  - 手机扬声器：硬件边界决定，EQ 不可修

输出：
  peq-profiles/<设备名>v5.json  （12 个，comprehensive tuning config）
  exports/v5/<设备名>v5-Poweramp.txt / .json  （12 组，Poweramp 导入用）
  PEQ优化方案v5-综合调优.md  （v3→v5 升级总览 + 逐项变更与声学依据）

依赖：peq_common（共享常量/路径/IO）+ peq_engine（确定性计算/校验/渲染）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\izual\.codebuddy\skills\poweramp-peq-tuner\scripts")
from peq_common import (  # noqa: E402
    PROFILE_DIR, now_iso, ensure_dir, write_json, write_text, export_dir_for,
    DEVICE_REGISTRY, device_names,
)
from peq_engine import (  # noqa: E402
    compute_preamp,
    render_equalizer_json,
    render_poweramp_txt,
    validate_preset,
)

EXPORT_V5 = export_dir_for("v5")
REPORT = Path("PEQ优化方案v5-综合调优.md")

# 各设备新增参数（紧凑格式：仅写非默认项；默认值由 build_v5_profile 填充）
# why 字段直接引用 声学特点.txt 的对应章节，便于追溯
V5_NEW_PARAMS = {
    # ==================== 入耳式 IEM ====================
    "IE900复刻版": {
        "frontend_z_max_ohm": 4,
        "frontend_z_basis": "32Ω 复刻品；建议前端输出阻抗 ≤ 1/8 阻抗（4Ω），防频响偏移",
        "limiter": {
            "ceiling_db": -3.0, "release_ms": 50,
            "why": "复刻品 THD 可达 3%（原版 <0.05%），limiter 防失真恶化"
        },
    },
    "BGVP Scale Pro": {
        "frontend_z_max_ohm": 2,
        "frontend_z_basis": "17Ω 极低阻抗 + 113dB 高灵敏；前端输出阻抗 ≤ 2Ω 防频响偏移与底噪放大",
    },
    "1圈14铁耳机": {
        "crossover_note": {
            "type": "passive_4way",
            "internal": "Multitube 多路滤波专利（4 分频 / 4 独立声孔）",
            "compensation_eq": "350Hz / 3000Hz 双分频点相位补偿（v3 PEQ 已含）",
        },
        "channel_match_db": 2,
        "channel_match_basis": "多单元声道匹配通常 < 2dB；超出需厂家调校",
    },
    # ==================== 头戴式耳机 ====================
    "HD800耳机": {
        "frontend_z_max_ohm": 10,
        "frontend_z_basis": "300Ω 标称 + 110Hz 650Ω 谐振峰；建议前端输出阻抗 ≤ 10Ω 提供阻尼",
    },
    "Sony MDR-1ABT": {
        "frontend_z_max_ohm": 3,
        "frontend_z_basis": "24Ω 标称；建议前端输出阻抗 ≤ 1/8 阻抗（3Ω）",
    },
    "Bose QC 45": {
        "app_interlock": {
            "app_name": "Bose Music",
            "action": "must_disable_eq",
            "why": "Bose Music App 内置 EQ 必须关闭，避免与 Poweramp EQ 串联失真"
        },
        "bose_native_dynamics": "Bose 自研动态音质均衡已含主动保护；外部 EQ 叠加边际收益小",
    },
    "Ugreen Hitune T8降噪耳机": {
        "codec_recommendation": {
            "primary": "LDAC 990kbps",
            "fallback": "aptX HD 576kbps",
            "why": "LDAC 模式最大化 Hi-Res 优势；aptX HD 仅 48k/24bit"
        },
        "tws_native_dynamics": "TWS 内部已有动态处理；外部叠加无增益",
    },
    # ==================== 便携音箱 ====================
    "Sony XB12双音箱组合": {
        "stereo_setup": {
            "per_speaker_balance": "manual_independent",
            "why": "双音箱组合需独立控制每只音量（电平匹配）；蓝牙声道已自动映射"
        },
        "limiter": {
            "ceiling_db": -3.0, "release_ms": 100,
            "why": "5-6W 小单元；limiter 防振膜过度位移"
        },
    },
    # ==================== 手机扬声器 ====================
    "Samsung S25 Plus手机扬声器": {
        "channel_balance_action": {
            "where": "Android 系统 Dolby Atmos 声道平衡",
            "why": "顶部扬声器声压级低于底部；声像偏下需系统设置（全局 EQ 不可修）"
        },
        "irreversible_hardware": [
            "低频 -3dB 截止 > 100Hz（超薄机身限制）",
            "2-16kHz 线性度偏差 15-17%（单元物理缺陷）"
        ],
    },
    "OPPO A5 4G手机扬声器": {
        "channel_balance_action": {
            "where": "Android 系统 Dolby Atmos 声道平衡",
            "why": "底部扬声器音量显著大于顶部；系统设置可改善"
        },
        "irreversible_hardware": [
            "左右声道音量差（顶部偏小）",
            "超薄机身物理频响边界"
        ],
    },
    # ==================== 车载音响 ====================
    "Micra K13车载音响": {
        "crossover_note": {
            "type": "full_range_no_xover",
            "note": "4 全频扬声器无独立高音单元；分频 = 无（被动物理结构）"
        },
        "delay": {
            "per_driver_ms": {"rear_left": 0.5, "rear_right": 0.5},
            "why": "后门全频单元到驾驶位约多 0.17m（343m/s = 0.5ms）；无 DSP 不可实现"
        },
        "compressor": {
            "threshold_db": -6.0, "ratio": 3.0, "attack_ms": 30, "release_ms": 250,
            "why": "无外置功放；4Ω/90-93dB 单元功率余量小；压缩保护免受热压缩失真"
        },
        "limiter": {
            "ceiling_db": -0.5, "release_ms": 80,
            "why": "原厂 4 全频单元功率小；limiter 防单元损坏"
        },
        "dsp_note": "无外置 DSP 功放不可实现本配置；外置 DSP（如 Helix DSP Mini）参考方案",
    },
    "Nissan X-Trail车载音响": {
        "crossover_note": {
            "type": "passive_2way",
            "frequencies_hz": {"mid_low_pass": 3000, "tweeter_high_pass": 3000},
            "slopes_db_oct": [12, 12],
            "physical_location": {"tweeter": "仪表台顶部", "mid_woofer": "前门下部"},
            "path_difference_m": 0.5,
            "compensation_eq": "3kHz +1.5dB 补分频点相位干涉；8kHz +1.5dB 补高音指向性"
        },
        "delay": {
            "per_driver_ms": {"tweeter_dash": 0, "mid_door": 1.5, "rear_full": 0.5},
            "why": "车门中低音比仪表台高音远约 0.5m → 1.5ms 延迟；后门到驾驶位 0.5ms"
        },
        "compressor": {
            "threshold_db": -10.0, "ratio": 4.0, "attack_ms": 20, "release_ms": 200,
            "why": "20W 额定功率动态余量小；压缩保护免受热压缩失真"
        },
        "limiter": {
            "ceiling_db": -1.0, "release_ms": 50,
            "why": "40W 最大功率封顶；limiter 防单元烧毁"
        },
        "dsp_note": "无外置 DSP 功放不可实现本配置；外置 DSP（如 Helix DSP Mini）参考方案",
    },
}


def _defaults_for_unused(dev_type: str) -> dict:
    """非车载 / 非便携设备的默认 '无需求' 配置。"""
    return {
        "crossover_note": {
            "type": "none",
            "note": "单驱动单元或单元内部分频已完成"
        },
        "delay": {"per_driver_ms": {}, "left_ms": 0, "right_ms": 0, "note": "单驱动或单元内对齐已完成"},
        "compressor": {"enabled": False, "rationale": "单元裕量充足 / 厂商内置保护"},
        "limiter": {"enabled": False, "rationale": "单元裕量充足 / 厂商内置保护"},
    }


def build_v5_profile(name: str, dtype: str, v4: dict, v5_new: dict, now: str) -> dict:
    """从 v4统一无损 + v5 新增参数构造 v5 综合配置。"""
    eq = v4["preset"]
    preamp = eq["preamp"]
    bands = eq["bands"]
    warnings = validate_preset(eq)

    defaults = _defaults_for_unused(dtype)

    # 增益部分
    gain_section = {
        "preamp_db": preamp,
        "per_channel_db": {"left": 0.0, "right": 0.0},
        "rationale": "PEQ 基准 preamp；通道平衡默认 0dB（按需调整）",
    }
    if "frontend_z_max_ohm" in v5_new:
        gain_section["frontend_output_z_max_ohm"] = v5_new["frontend_z_max_ohm"]
        gain_section["frontend_output_z_basis"] = v5_new["frontend_z_basis"]
    if "channel_match_db" in v5_new:
        gain_section["driver_channel_match_max_db"] = v5_new["channel_match_db"]
        gain_section["driver_channel_match_basis"] = v5_new["channel_match_basis"]
    if "stereo_setup" in v5_new:
        gain_section["stereo_setup"] = v5_new["stereo_setup"]
    if "channel_balance_action" in v5_new:
        gain_section["channel_balance_action"] = v5_new["channel_balance_action"]
    if "irreversible_hardware" in v5_new:
        gain_section["irreversible_hardware"] = v5_new["irreversible_hardware"]

    # 动态部分
    if "compressor" in v5_new:
        comp = dict(v5_new["compressor"])
        comp["enabled"] = True
        comp["rationale"] = comp.get("why", "声学依据详见 why 字段")
        compressor_section = comp
    else:
        compressor_section = defaults["compressor"]
    if "limiter" in v5_new:
        lim = dict(v5_new["limiter"])
        lim["enabled"] = True
        lim["rationale"] = lim.get("why", "声学依据详见 why 字段")
        limiter_section = lim
    else:
        limiter_section = defaults["limiter"]
    dynamics_section = {
        "compressor": compressor_section,
        "limiter": limiter_section,
        "rationale": "单元裕量评估后配置；详见各子项 why",
    }
    if "bose_native_dynamics" in v5_new:
        dynamics_section["native_dynamic_eq"] = v5_new["bose_native_dynamics"]
    if "tws_native_dynamics" in v5_new:
        dynamics_section["native_dynamic_eq"] = v5_new["tws_native_dynamics"]

    profile = {
        "name": f"{name}v5",
        "device_type": dtype,
        "version": "5.0",
        "created_at": now, "updated_at": now,
        "locked": True, "active": False,
        "preference": f"custom_v5", "intensity": 1.0,
        "base": f"{name}v4统一无损",
        "acoustic_reference": "声学特点.txt",
        # 1. 均衡（继承 v4统一无损）
        "equalizer": {
            "preamp_db": preamp,
            "parametric": True,
            "bands": bands,
            "warnings": warnings,
            "note": "继承 v4统一无损 31 段 PEQ；v5 升级不修改 EQ 本身"
        },
        # 2. 分频
        "crossover": v5_new.get("crossover_note", defaults["crossover_note"]),
        # 3. 增益
        "gain": gain_section,
        # 4. 延迟
        "delay": v5_new.get("delay", defaults["delay"]),
        # 5. 动态
        "dynamics": dynamics_section,
        # 6. 附加配置（应用互锁 / 编解码建议 / DSP 备注）
        "extras": {
            k: v for k, v in v5_new.items()
            if k not in ("crossover_note", "delay", "compressor", "limiter",
                         "frontend_z_max_ohm", "frontend_z_basis",
                         "channel_match_db", "channel_match_basis",
                         "stereo_setup", "channel_balance_action",
                         "irreversible_hardware",
                         "bose_native_dynamics", "tws_native_dynamics")
        },
    }
    return profile


def _fmt_freq(f: int) -> str:
    return f"{f/1000:g}kHz" if f >= 1000 else f"{f}Hz"


def main() -> int:
    now = now_iso()
    ensure_dir(EXPORT_V5)

    v4_files = sorted(PROFILE_DIR.glob("*v4统一无损.json"))
    assert len(v4_files) == 12, f"应找到 12 个 v4统一无损 档案，实际 {len(v4_files)}"

    # 报告初始化
    report = [
        "# PEQ 优化方案 v5 —— 综合调优（PEQ + 分频 + 增益 + 延迟 + 动态处理）",
        "",
        f"生成时间：{now}　|　基准：v4统一无损 31 段 PEQ"
        f"　|　声学参考：声学特点.txt　|　计算引擎：poweramp-peq-tuner",
        "",
        "## 升级定位",
        "",
        "v5 在 v4统一无损 31 段 PEQ 基础上，**新增 4 类综合调优参数**，覆盖完整调优链路：",
        "",
        "| 维度 | 新增内容 | 主要适用设备 | Poweramp 是否直接支持 |",
        "|---|---|---|---|",
        "| **均衡 (equalizer)** | 继承 v4统一无损 PEQ（无改动）| 12 设备 | ✓ 直接导入 |",
        "| **分频 (crossover)** | 物理分频点 / 斜率 / 位置 / EQ 补偿 | X-Trail（K13 是 full-range）| ✗ 需外置 DSP |",
        "| **增益 (gain)** | 通道平衡 + 前端输出阻抗建议 + 单元电平匹配 | 12 设备差异化 | △ 部分（前端阻抗为建议）|",
        "| **延迟 (delay)** | 多驱动单元时间对齐 | K13 / X-Trail | ✗ 需外置 DSP |",
        "| **动态 (dynamics)** | 压缩器 (compressor) + 限幅器 (limiter) | IE900 复刻 / XB12 / 车载 | ✗ 需外置 DSP（Poweramp 无动态）|",
        "",
        "## v3 → v5 升级总览（12 设备）",
        "",
        "| 设备 | EQ | 分频 | 增益新增 | 延迟 | 动态 | 主要升级点 |",
        "|---|---|---|---|---|---|---|",
    ]

    upgrade_summary = {
        "IE900复刻版": ("继承 v4统一无损", "none", "前端 ≤ 4Ω", "none", "+limiter", "复刻 THD 3% 保护"),
        "BGVP Scale Pro": ("继承 v4统一无损", "none", "前端 ≤ 2Ω", "none", "无", "底噪敏感防护"),
        "1圈14铁耳机": ("继承 v4统一无损", "passive_4way", "声道匹配 < 2dB", "none", "无", "分频点相位记录"),
        "HD800耳机": ("继承 v4统一无损", "none", "前端 ≤ 10Ω", "none", "无", "110Hz 谐振峰前端建议"),
        "Sony MDR-1ABT": ("继承 v4统一无损", "none", "前端 ≤ 3Ω", "none", "无", "BT 链路记录"),
        "Bose QC 45": ("继承 v4统一无损", "none", "Bose App EQ 必须关", "none", "Bose 自研", "应用互锁 + 动态 EQ 联动"),
        "Ugreen Hitune T8降噪耳机": ("继承 v4统一无损", "none", "LDAC 推荐", "none", "TWS 内置", "编解码建议"),
        "Sony XB12双音箱组合": ("继承 v4统一无损", "none", "独立音量", "none", "+limiter", "小单元保护"),
        "Samsung S25 Plus手机扬声器": ("继承 v4统一无损", "none", "系统声道平衡", "none", "手机 DSP", "硬件不可修项记录"),
        "OPPO A5 4G手机扬声器": ("继承 v4统一无损", "none", "系统声道平衡", "none", "手机 DSP", "硬件不可修项记录"),
        "Micra K13车载音响": ("继承 v4统一无损", "full_range", "原厂无电平匹配", "后门 +0.5ms", "+compressor +limiter", "车载综合升级"),
        "Nissan X-Trail车载音响": ("继承 v4统一无损", "passive_2way", "原厂分频器已匹配", "中低音 +1.5ms / 后门 +0.5ms", "+compressor +limiter", "2 路被动分频 + 时间对齐"),
    }
    for dev, summary in upgrade_summary.items():
        report.append(f"| {dev} | {' | '.join(summary)} |")

    report += [
        "",
        "## 通用调优原则",
        "",
        "1. **均衡**：v3 已针对每设备单元特性优化；v5 不修改 EQ 本身，继承 v4统一无损 即可",
        "2. **分频**：EQ **不可改变物理分频**；EQ 只能补偿分频点附近的声学问题（如相位干涉、指向性）",
        "3. **增益**：",
        "   - 前端输出阻抗 ≤ 1/8 单元阻抗（低音偏移防抖）",
        "   - 300Ω 大阻单元（HD800）建议 ≤ 10Ω 阻尼（控制 110Hz 谐振峰）",
        "   - 多单元声道匹配 < 2dB 为正常",
        "4. **延迟**：仅多驱动单元需要；单驱动单元 0ms；时间对齐 = (远端距离 - 近端距离) / 343 m/s × 1000",
        "5. **动态**：",
        "   - 压缩器：保护单元免受热压缩失真（单元功率余量小时启用）",
        "   - 限幅器：封顶防单元烧毁（单元最大功率时启用）",
        "   - 已被厂商内置的设备（Bose QC 45 / TWS）不需外部配置",
        "6. **应用互锁**：Bose QC 45 的 Bose Music App EQ 必须关闭（与 Poweramp EQ 串联失真）",
        "",
        "---",
        "",
        "## 各设备 v5 详细配置",
        "",
    ]

    total = 0
    for p in v4_files:
        v4 = json.loads(p.read_text(encoding="utf-8"))
        name = v4["name"].replace("v4统一无损", "")
        dtype = v4["device_type"]
        v5_new = V5_NEW_PARAMS.get(name, {})

        # 构造 v5 profile
        profile = build_v5_profile(name, dtype, v4, v5_new, now)
        write_json(PROFILE_DIR / f"{name}v5.json", profile)

        # 导出 Poweramp 兼容的 EQ 文件
        preset = {
            "name": f"{name} v5 综合调优（基准 {name}v4统一无损）",
            "preamp": profile["equalizer"]["preamp_db"],
            "parametric": True,
            "bands": profile["equalizer"]["bands"],
        }
        write_text(EXPORT_V5 / f"{name}v5-Poweramp.txt", render_poweramp_txt(preset))
        # render_equalizer_json() 返回预序列化字符串（已含 \n 转义），用 write_text
        write_text(EXPORT_V5 / f"{name}v5-PowerampEQ.json", render_equalizer_json(preset))
        total += 1

        # 报告设备小节
        eq = profile["equalizer"]
        co = profile["crossover"]
        ga = profile["gain"]
        de = profile["delay"]
        dy = profile["dynamics"]

        report += [
            f"### {name}（{dtype}）",
            "",
            f"**基准档案**：`{name}v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）",
            "",
            "#### 1. 均衡（继承 v4统一无损）",
            "",
            f"- preamp: **{eq['preamp_db']:+.1f} dB**",
            f"- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）",
            f"- 详见 base 档案：`peq-profiles/{name}v4统一无损.json`",
            "",
            "#### 2. 分频",
            "",
            f"- 类型：**{co.get('type', 'none')}**",
        ]
        if co.get("frequencies_hz"):
            fr = co["frequencies_hz"]
            report.append(f"- 分频点：{fr}")
        if co.get("slopes_db_oct"):
            report.append(f"- 斜率：{co['slopes_db_oct']} dB/oct")
        if co.get("physical_location"):
            report.append(f"- 物理位置：{co['physical_location']}")
        if co.get("path_difference_m"):
            report.append(f"- 路径差：{co['path_difference_m']} m（高音 vs 中低音）")
        if co.get("compensation_eq"):
            report.append(f"- EQ 补偿：{co['compensation_eq']}")
        if co.get("internal"):
            report.append(f"- 内部结构：{co['internal']}")
        report += [f"- 声学依据：{co.get('note', '')}", ""]

        report += [
            "#### 3. 增益",
            "",
            f"- preamp：{ga['preamp_db']:+.1f} dB（与均衡共享）",
            f"- 通道平衡：左 {ga['per_channel_db']['left']:+.1f} dB / 右 {ga['per_channel_db']['right']:+.1f} dB",
        ]
        if "frontend_output_z_max_ohm" in ga:
            report += [
                f"- 前端输出阻抗建议：≤ **{ga['frontend_output_z_max_ohm']} Ω**",
                f"- 声学依据：{ga['frontend_output_z_basis']}",
            ]
        if "driver_channel_match_max_db" in ga:
            report += [
                f"- 单元声道匹配：< {ga['driver_channel_match_max_db']} dB（厂家调校基准）",
                f"- 声学依据：{ga['driver_channel_match_basis']}",
            ]
        if "stereo_setup" in ga:
            report += [f"- 双音箱配置：{ga['stereo_setup']['per_speaker_balance']}",
                       f"- 声学依据：{ga['stereo_setup']['why']}"]
        if "channel_balance_action" in ga:
            report += [f"- 通道平衡需通过：{ga['channel_balance_action']['where']}",
                       f"- 声学依据：{ga['channel_balance_action']['why']}"]
        if "irreversible_hardware" in ga:
            report += ["- 硬件不可修项（EQ 不可改善）："]
            for item in ga["irreversible_hardware"]:
                report.append(f"  - {item}")
        report += [
            "",
            "#### 4. 延迟",
            "",
            f"- 左/右：{de.get('left_ms', 0)} ms / {de.get('right_ms', 0)} ms",
        ]
        if de.get("per_driver_ms"):
            report.append(f"- 按驱动单元：{de['per_driver_ms']}")
        if de.get("why"):
            report.append(f"- 声学依据：{de['why']}")
        report += [f"- 备注：{de.get('note', '无')}", ""]

        report += [
            "#### 5. 动态",
            "",
            f"- 压缩器：{'启用' if dy['compressor'].get('enabled') else '未启用'}",
        ]
        if dy["compressor"].get("enabled"):
            c = dy["compressor"]
            report += [
                f"  - threshold: {c['threshold_db']} dB / ratio: {c['ratio']} / "
                f"attack: {c['attack_ms']} ms / release: {c['release_ms']} ms",
                f"  - 声学依据：{c.get('why', '')}",
            ]
        report += [
            f"- 限幅器：{'启用' if dy['limiter'].get('enabled') else '未启用'}",
        ]
        if dy["limiter"].get("enabled"):
            li = dy["limiter"]
            report += [
                f"  - ceiling: {li['ceiling_db']} dB / release: {li.get('release_ms', '?')} ms",
                f"  - 声学依据：{li.get('why', '')}",
            ]
        if "native_dynamic_eq" in dy:
            report += [f"- 厂商内置动态：{dy['native_dynamic_eq']}"]
        if v5_new.get("app_interlock"):
            ai = v5_new["app_interlock"]
            report += [f"- 应用互锁：{ai['app_name']} → {ai['action']}", f"  - 声学依据：{ai['why']}"]
        if v5_new.get("codec_recommendation"):
            cr = v5_new["codec_recommendation"]
            report += [f"- 编解码推荐：{cr['primary']}（备选 {cr['fallback']}）", f"  - 声学依据：{cr['why']}"]
        if v5_new.get("dsp_note"):
            report += [f"- **DSP 备注**：{v5_new['dsp_note']}"]
        report += [
            "",
            f"**导出**：`exports/v5/{name}v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）",
            f"**完整配置**：`peq-profiles/{name}v5.json`（含分频/增益/延迟/动态）",
            "",
            "---",
            "",
        ]

    # 跨设备升级统计
    report += [
        "## 跨设备新参数启用统计",
        "",
        "| 设备 | 均衡 | 分频 | 增益新增 | 延迟 | 动态 |",
        "|---|---|---|---|---|---|",
    ]
    for name in V5_NEW_PARAMS.keys():
        v5_new = V5_NEW_PARAMS[name]
        eq_status = "继承 v4统一无损"
        xover = "non-trivial" if v5_new.get("crossover_note", {}).get("type") not in ("none", None) else "—"
        gain = []
        if v5_new.get("frontend_z_max_ohm"): gain.append("前端输出阻抗")
        if v5_new.get("channel_match_db"): gain.append("声道匹配")
        if v5_new.get("stereo_setup"): gain.append("双音箱")
        if v5_new.get("channel_balance_action"): gain.append("系统声道平衡")
        if v5_new.get("irreversible_hardware"): gain.append("硬件不可修项")
        if v5_new.get("app_interlock"): gain.append("应用互锁")
        if v5_new.get("codec_recommendation"): gain.append("编解码")
        gain_str = " / ".join(gain) if gain else "—"
        delay = "—" if not v5_new.get("delay", {}).get("per_driver_ms") else "✓"
        dyn = []
        if v5_new.get("compressor", {}).get("enabled"): dyn.append("compressor")
        if v5_new.get("limiter", {}).get("enabled"): dyn.append("limiter")
        if v5_new.get("bose_native_dynamics"): dyn.append("Bose 内置")
        if v5_new.get("tws_native_dynamics"): dyn.append("TWS 内置")
        dyn_str = " / ".join(dyn) if dyn else "—"
        report.append(f"| {name} | {eq_status} | {xover} | {gain_str} | {delay} | {dyn_str} |")

    report += [
        "",
        "## 实施步骤",
        "",
        "### 场景 A：仅 Poweramp 导入（最常用）",
        "",
        "1. 从 `exports/v5/<设备名>v5-Poweramp.txt` 或 `.json` 导入 Poweramp Equalizer",
        "2. `equalizer` 部分的 31 段 PEQ + preamp 完整保留 v4统一无损 调音",
        "3. `分频 / 延迟 / 动态` 参数作为后续硬件升级（外置 DSP）参考",
        "",
        "### 场景 B：Poweramp + 外置 DSP（车载 / 高级玩家）",
        "",
        "1. **Poweramp**：导入 v5 PEQ（场景 A 步骤）",
        "2. **外置 DSP**（如 Helix DSP Mini / Audison bit One / miniDSP）：",
        "   - 分频：按 `crossover.frequencies_hz` 设置分频点 / 斜率",
        "   - 延迟：按 `delay.per_driver_ms` 设置时间对齐",
        "   - 动态：按 `dynamics.compressor` / `dynamics.limiter` 设置压缩限幅",
        "   - 增益：按 `gain.frontend_output_z_max_ohm` 设置输入阻抗（若支持）",
        "3. **系统连接**：手机 / 主机 → 外置 DSP → 功放 → 扬声器",
        "",
        "### 场景 C：Bose QC 45 / TWS 等智能设备",
        "",
        "1. **关闭厂商 App 内置 EQ**（Bose Music / Ugreen App），避免与 Poweramp 串联",
        "2. **开启 LDAC / aptX HD**（开发者选项 / App 内设置）",
        "3. 导入 v5 PEQ 到 Poweramp",
        "4. 厂商动态 EQ 仍在工作（与 Poweramp 静态 EQ 互补）",
        "",
        "## 后续维护建议",
        "",
        "1. **声学特点.txt 更新时**：复核 V5_NEW_PARAMS 是否仍准确（特别是前端输出阻抗建议）",
        "2. **新设备加入时**：按 8 维度 + 4 新维度扩展 V5_NEW_PARAMS 字典",
        "3. **PEQ 调整时**：修改 v3 / v4统一无损 后重跑本脚本（v5 自动继承）",
        "4. **跨设备对比**：用 `peq_cli.py list-profiles` 配合 `extras` 字段做横向对比",
        "",
    ]

    REPORT.write_text("\n".join(report), encoding="utf-8", newline="\n")
    print(f"完成：{total} 个 v5 综合配置（12 设备）")
    print(f"档案 -> {PROFILE_DIR}；预设 -> {EXPORT_V5}；报告 -> {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
