# -*- coding: utf-8 -*-
"""v3：将 v2 声学重设计方案细化为 31 段频点精细 PEQ。

方法：把 v2 滤波器组（含搁架结构）的合成目标响应采样到 1/3 倍频程
31 段频栅（20Hz-20kHz）上，每段以 PK（Q=4.32，1/3 倍频程本征 Q）
实现——所见即所得，搁架结构由相邻频段的斜坡量化实现。

输出：
  peq-profiles/<设备名>v3.json
  exports/v3/<设备名>v3-Poweramp.txt / -PowerampEQ.json
  PEQ优化方案v3-31段精细化.md（痛点分析/优化方向/31 段全参数）

依赖：peq_common（共享常量/路径/IO）+ peq_engine（确定性计算/校验/渲染）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\izual\.codebuddy\skills\poweramp-peq-tuner\scripts")
from peq_common import (  # noqa: E402
    FREQS, GRID_Q, PROFILE_DIR, export_dir_for, now_iso, ensure_dir, write_json, write_text,
)
from peq_engine import (  # noqa: E402
    TYPE_PEAK,
    _band_gain_at,
    compute_preamp,
    render_equalizer_json,
    render_poweramp_txt,
    validate_preset,
)
from design_v2 import DEVICES as V2_DEVICES  # noqa: E402

EXPORT_DIR = export_dir_for("v3")
REPORT = Path("PEQ优化方案v3-31段精细化.md")

# 关键痛点与优化方向（综合 声学特点.txt + v1 用户反馈 + v2 数据修正三轮结论）
ANALYSIS = {
    "IE900复刻版": {
        "pain": ["Helmholtz 共振腔调校不足 → 100Hz 附近低频轰头、掩蔽中频",
                 "6kHz 陷波处理不当 → 中高频衔接断点、泛音不连贯",
                 "THD 标称 3%（原版 <0.05%）→ 大音量失真红线低",
                 "32Ω 对前端输出阻抗敏感 → 低频量随前端漂移"],
        "direction": ["100Hz 收敛 -3.5dB 降单元行程（间接压失真），45Hz 以下保留真实下潜",
                      "6kHz 架桥 +2dB 平滑陷波，3k 细节增益补 X3R 意图的揭示力",
                      "12kHz 高架补偿受限的高频延伸",
                      "增益幅度整体克制，规避 3% THD 红线"],
    },
    "Sony XB12双音箱组合": {
        "pain": ["被动辐射器过量低频 → 100-200Hz 隆起、浑浊",
                 "中频颗粒感/鼻音感（约 1kHz）",
                 "6-10kHz 嘶嘶声；极高频物理衰减",
                 "低电量/高温音量衰减（非 EQ 范畴，需余量防护）"],
        "direction": ["125Hz 收敛 -3dB 清理辐射器隆起；60Hz 低架 +1.5dB 保可用下潜",
                      "1kHz -1.5dB 收颗粒感；8kHz 窄带 -2dB 收嘶声",
                      "14kHz 轻补延伸（+1dB，物理极限内）",
                      "负 preamp 余量缓解低电量限幅破音"],
    },
    "1圈14铁耳机": {
        "pain": ["4 分频两个分频点（200-500Hz / 2-4kHz）相位抵消 → 声音脱节、结像模糊",
                 "标准线材人声偏薄（用户反馈）",
                 "12-20Ω 低阻抗 → 输出阻抗敏感"],
        "direction": ["350Hz 与 3000Hz 各 +1dB 宽 Q 补偿分频点能量",
                      "60Hz 低架 +1.5dB 强化动圈氛围；10kHz 高架衔接 EST 超高频",
                      "全部增益 ≤1.5dB，不劣化原厂匹配（<2dB）"],
    },
    "HD800耳机": {
        "pain": ["开放式 <100Hz 低频滚降 → 量感不足（最核心痛点）",
                 "6-7kHz 固有峰值 → 高频锐利/刺耳",
                 "110Hz 处 650Ω 阻抗谐振峰 → 高输出阻抗前端低频再隆起",
                 "300Ω 需耳放，驱动不足时劣化加剧"],
        "direction": ["110Hz 低架 +4dB 平台补量感（转角避开谐振峰激发）+40Hz +2dB 下潜",
                      "6500Hz 窄带 -2.5dB（Q4.32）+ 5k 肩部 -1dB 收锐利",
                      "10kHz +1dB 空气感保持声场通透",
                      "0.02% THD 余量支撑低频增益安全性"],
    },
    "Micra K13车载音响": {
        "pain": ["门腔驻波 → 160-500Hz 浑浊（'不怎么样'的主因）",
                 "无独立高音 + 离轴响应差 → 高频细节/空气感严重缺失",
                 "低频截止 60-80Hz、高频止于 15-20kHz 的物理边界",
                 "无外置功放 → 大音量失真与功率不足"],
        "direction": ["200/160Hz 双段收敛（-2.5/-1.5dB）清驻波",
                      "2500Hz +2dB 人声可懂度、6000Hz 高架 +2dB 补空气感（15-20kHz 极限内）",
                      "70Hz 低架 +1dB 维持可用低频；中低频负增益降低 4Ω 单元负担"],
    },
    "BGVP Scale Pro": {
        "pain": ["分频点 2-3kHz 相位未对齐 → 200Hz-2kHz 结像偏移",
                 "下潜不深（用户反馈）",
                 "113dB/mW 极高灵敏度 → 前端底噪/输出阻抗敏感",
                 "低阻前端下阻抗分压 → 低频自然增益（叠加需防过量）"],
        "direction": ["80Hz 低架 +2dB 保守补下潜（为前端自然增益留余量）",
                      "400Hz +1dB 人声厚度、2500Hz -1dB 稳固分频点结像",
                      "8000Hz +1dB 保持明亮不刺特质；整体增益 ≤2dB 守 THD<1%"],
    },
    "Samsung S25 Plus手机扬声器": {
        "pain": ["实测 100-315Hz 输出显著不足 → 声音'空洞'、鼓点无冲击力（Notebookcheck）",
                 "2-16kHz 线性度偏差 15-17% → 毛刺感",
                 "顶部扬声器声压低于底部 → 声像偏下（全局 EQ 不可修）",
                 "超薄机身 -3dB 截止 >100Hz"],
        "direction": ["200Hz +3dB 宽 Q 填补实测不足区（核心），125Hz +1.5dB 平滑下缘",
                      "3150Hz +1dB 平滑线性度毛刺、6300Hz -1dB 收易嘶频段",
                      "声像偏下交由系统 Dolby 声道平衡处理"],
    },
    "OPPO A5 4G手机扬声器": {
        "pain": ["底部音量显著大于顶部 → 声像轻微偏移",
                 "300% 软件增益易触发失真",
                 "外放本身饱满优秀 → 过度干预反而劣化"],
        "direction": ["±0.5dB 最小干预（800/3000Hz 微抬、250Hz 微收）",
                      "通道平衡交系统设置；软件增益建议 ≤200%",
                      "保留原厂'准旗舰'调音底子"],
    },
    "Ugreen Hitune T8降噪耳机": {
        "pain": ["ANC -55dB 主要作用 <1kHz、带宽仅 4kHz → 4kHz 以上瞬态噪声泄漏掩蔽高频",
                 "12.4mm 大单元小腔体 → 150Hz 低频肥感",
                 "ANC 佩戴后低频节奏感被削",
                 "腔体导管限制高频延伸"],
        "direction": ["2000Hz +1.5dB 主攻人声（ANC 有效区信噪比最佳）",
                      "5000Hz +1dB 补 ANC 带宽外泄漏、10000Hz 高架补导管限制的延伸",
                      "150Hz -1.5dB 收肥感、60Hz 低架 +1.5dB 维持节奏感",
                      "关/开 ANC 两次校准（ANC 开关改变频响）"],
    },
    "Nissan X-Trail车载音响": {
        "pain": ["高音（仪表台）与中低音（车门）声学路径差 → 2-4kHz 分频点相位干涉（凹陷/峰）",
                 "车门中低音腔体共鸣 → 160-630Hz 浑浊（'浑浊的六扬声器'）",
                 "20W 额定功率 → 大音量热压缩失真余量小",
                 "后门全频离轴 → 后排高频细节缺失"],
        "direction": ["3000Hz +1.5dB 补分频点相位凹陷（结像上移至仪表台）",
                      "200/400Hz 双段收敛（-2.5/-1.5dB）清浑浊",
                      "8000Hz 高架 +1.5dB 补高音指向性；1000Hz +1dB 人声密度",
                      "负 preamp + 收敛段保护 20W 动态余量；高速副本 1k/3k 各 +0.5dB"],
    },
    "Sony MDR-1ABT": {
        "pain": ["What Hi-Fi 评测直指'Recessed vocals'——1kHz 人声基频区被'万金油中正'调音压到靠后",
                 "'Lack get-up-and-go'——整体听感温吞不抓人（2kHz 上缘密度不足）",
                 "5kHz 乐器泛音与人声齿音下缘存在感偏弱（'均衡不突出'的另一面）",
                 "DSEE/LDAC 释放的高频延伸受保守调音压抑（12kHz 可再 +0.5dB）",
                 "40mm 镀铝 LCP 振膜+封闭式+全包裹的物理优势未充分发挥"],
        "direction": ["1kHz +1.5dB 把人声从'靠后'拉回'居中前位'（用户评价最痛点的核心补偿）",
                      "2kHz +1.0dB 推前齿音区之前的人声胸腔/口型感，与 1kHz 形成宽带抬升",
                      "5kHz +0.5dB 提升乐器泛音存在感（克制幅度防齿音）",
                      "12kHz 高架 +0.5dB 释放 LDAC/DSEE 频段；20Hz 低架 +1dB 保持下潜",
                      "全部 ≤1.5dB 守 24Ω/98dB 单元裕量；有线与 BT-LDAC 模式通用"],
    },
    "Bose QC 45": {
        "pain": ["Bose 商业目标曲线'Veiled'——>10kHz 主动滚降导致细节/空气感被遮蔽",
                 "ANC ON 时 sub-bass 被主动抬升（Bose 声学掩蔽对冲策略）→ 偏暖略糊",
                 "ANC 模式下人声可懂度被环境噪声掩蔽（2-3kHz 收益最大频段未补偿）",
                 "封闭式+ANC 设计物理上限：声场偏窄、降噪等级属硬件能力",
                 "动态 EQ（音量自适应）需避免与外部 EQ 叠加失真"],
        "direction": ["40Hz -1dB 收敛 ANC ON 偏多的 sub-bass（不破坏 Bose 招牌低频印象）",
                      "2.5kHz +1.5dB 主攻人声可懂度（ANC 噪声掩蔽下人耳最敏感频段）",
                      "8kHz +1dB 补回 Bose 滚降起始段的'Veiled'感（细节回归）",
                      "14kHz 高架 +0.5dB 封闭式物理极限内的空气感恢复",
                      "Bose 应用内置 EQ 必须先关以免双 EQ 叠加；ANC ON/OFF 分别校准"],
    },
}


def main() -> int:
    ensure_dir(PROFILE_DIR)
    ensure_dir(EXPORT_DIR)
    now = now_iso()

    report = [
        "# PEQ 优化方案 v3 —— 十款设备 31 段频点精细化配置",
        "",
        f"生成时间：{now}　|　方法：v2 声学重设计（依据 声学特点.txt 实测数据）→ 合成目标响应"
        "采样至 1/3 倍频程 31 段频栅　|　计算引擎：poweramp-peq-tuner",
        "",
        f"**统一约定**：31 段 = 1/3 倍频程 ISO 频栅（20-20000Hz，31.5Hz 按规范取整为 31）；"
        f"每段均为**峰值滤波（PK）**，Q 统一 = {GRID_Q}（1/3 倍频程本征 Q，各段近似独立、"
        "增益即该频点实际修正量）；v2 中的搁架结构已量化为相邻频段斜坡（如低频平台=低段"
        "连续正增益、高频空气感=高段连续正增益）；preamp 由引擎按合成响应自动计算防削波。",
        "",
        "---",
    ]

    for idx, dev in enumerate(V2_DEVICES, 1):
        ana = ANALYSIS[dev["name"]]
        v2_bands = [
            {"type": {"PK": 3, "LSC": 0, "HSC": 1}[f["t"]], "frequency": float(f["f"]),
             "q": float(f["q"]), "gain": float(f["g"])}
            for f in dev["filters"]
        ]
        # 采样 v2 合成响应到 31 段网格
        bands = []
        for f in FREQS:
            g = round(sum(_band_gain_at(b, f) for b in v2_bands), 1)
            g = max(-10.0, min(10.0, g))
            bands.append({"type": TYPE_PEAK, "frequency": int(f),
                          "q": GRID_Q, "gain": g})

        preamp = compute_preamp(bands)
        preset = {"name": f"{dev['name']} v3 - 31段精细化", "preamp": preamp,
                  "parametric": True, "bands": bands}
        warnings = validate_preset(preset)
        preset["warnings"] = warnings

        profile = {
            "name": f"{dev['name']}v3", "device_type": dev["device_type"],
            "brand": "", "model": "v3 31段精细化（v2 响应网格采样）",
            "preference": "custom_v3", "intensity": 1.0,
            "custom_bands": [f"PK {b['frequency']} {b['gain']:g} {b['q']:g}"
                              for b in bands],
            "locked": True, "note": "v2 声学方案细化为 31 段频点",
            "active": False, "created_at": now, "updated_at": now,
            "pain_points": ana["pain"], "directions": ana["direction"],
            "target": dev["target"], "metrics": dev["metrics"],
            "advice": dev["advice"],
            "preset": preset,
        }
        write_json(PROFILE_DIR / f"{dev['name']}v3.json", profile)
        write_text(EXPORT_DIR / f"{dev['name']}v3-Poweramp.txt", render_poweramp_txt(preset))
        # render_equalizer_json() 返回预序列化字符串（已含 \n 转义），用 write_text
        write_text(EXPORT_DIR / f"{dev['name']}v3-PowerampEQ.json", render_equalizer_json(preset))

        report += [
            f"## {idx}. {dev['name']}",
            "",
            f"**目标听感**：{dev['target']}",
            "",
            "**关键痛点（频响层面）**：",
        ]
        report += [f"- {p}" for p in ana["pain"]]
        report += ["", "**优化方向**："]
        report += [f"- {d}" for d in ana["direction"]]
        report += [
            "",
            f"**31 段精细配置**（全 PK，Q={GRID_Q}，preamp `{preamp:+.1f} dB`）：",
            "",
            "| # | 中心频率 Hz | 增益 dB | Q | 类型 |",
            "|---|---|---|---|---|",
        ]
        report += [
            f"| {i} | {b['frequency']} | {b['gain']:+.1f} | {b['q']:g} | 峰值 |"
            for i, b in enumerate(bands, 1)
        ]
        report += [
            "",
            f"**执行提示**：{dev['advice']}",
            "",
            f"**导出文件**：`exports/v3/{dev['name']}v3-Poweramp.txt`、"
            f"`exports/v3/{dev['name']}v3-PowerampEQ.json`",
            "",
        ]
        if warnings:
            report += [f"**校验提示**：{'；'.join(warnings)}", ""]
        report += ["---", ""]

    REPORT.write_text("\n".join(report), encoding="utf-8", newline="\n")
    print(f"完成：{len(V2_DEVICES)} 个 v3 方案 -> {EXPORT_DIR} / {PROFILE_DIR} / {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
