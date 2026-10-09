# -*- coding: utf-8 -*-
"""v4：12 设备 31 段 PEQ 的音源适配版（流媒体有损 / 统一无损）。

以 v3 31 段配置为基准派生双变体（确定性规则变换，Q=4.32 网格不变，仅调增益）：

流媒体规则（Ogg Vorbis / AAC 320kbps，心理声学有损 + 响度归一化）：
  - f ≥ 16000Hz：正增益归零（编码剔除区，补偿只会放大伪影；负增益保留）
  - 10000 ≤ f < 16000Hz：正增益 -0.5dB（镲片/齿音区伪影收敛）
  - f ∈ {20,25,31}Hz：正增益 ×0.7（深潜段收敛约 30%，适配响度归一化的动态）

统一无损规则（在线无损 + 本地无损合并）：
  - ≥16kHz / 10-12.5kHz / 20-31Hz 三处均**不施加流媒体规则**（无损不引入这些伪影）
  - 12.5-20kHz 仅 hi_res_capable 设备正增益 +0.3dB（发挥 Hi-Res 优势；保守于 v4本地音源 +0.5）
  - 其他频段维持 v3

输出：
  peq-profiles/<设备名>v4流媒体.json / <设备名>v4统一无损.json  （24 个 locked 档案）
  exports/v4/流媒体/ 与 exports/v4/统一无损/  （各 12 组 .txt + .json）
  PEQ优化方案v4-音源适配.md  （决策树/服务偏移表/调整目标/逐频段/听感差异）

依赖：peq_common（共享常量/路径/IO）+ peq_engine（确定性计算/校验/渲染）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\izual\.codebuddy\skills\poweramp-peq-tuner\scripts")
from peq_common import (  # noqa: E402
    GRID_Q, PROFILE_DIR, now_iso, ensure_dir, write_json, write_text,
    export_dir_for, DEVICE_REGISTRY, hi_res_capable_of,
)
from peq_engine import (  # noqa: E402
    compute_preamp,
    render_equalizer_json,
    render_poweramp_txt,
    validate_preset,
)

EXPORT_STREAM = export_dir_for("v4") / "流媒体"
EXPORT_UNIFIED = export_dir_for("v4") / "统一无损"
REPORT = Path("PEQ优化方案v4-音源适配.md")

HF_EXT_TYPES = {"iem_dynamic", "iem_hybrid", "open_headphone", "bluetooth_headphone"}

# Hi-Res 解析能力已迁入 peq_common.DEVICE_REGISTRY（单一来源）
# 使用 peq_common.hi_res_capable_of(name) 查询
# 规则：有线 IEM/HP 默认 True；蓝牙/手机/便携/车载默认 False
# Hi-Res boost 仅作用于 True 的设备（12.5-20kHz +0.3dB）

# 主流无损服务的响度归一化策略（用户调 preamp 时参考）
# 偏移 = 在 v4统一无损 基础上还需额外调整的 preamp 增量
# 含义：服务端若开 -16 LUFS 归一化（更激进的压峰），需在基准 preamp 上再 -0.5dB 防削波
UNIFIED_SERVICES = {
    "Apple Music Lossless":    {"loudness": -16, "codec": "ALAC",  "offset_db": -0.5, "note": "iTunes Sound Check 默认开 -16 LUFS"},
    "Tidal HiFi":              {"loudness": -14, "codec": "FLAC",  "offset_db":  0.0, "note": "Tidal 自身不开归一化，但下游 OS 常做"},
    "Tidal HiFi Plus (MQA)":   {"loudness": -14, "codec": "FLAC/MQA", "offset_db": 0.0, "note": "MQA 折叠时降级为 48k/24bit"},
    "Qobuz Studio":            {"loudness": -14, "codec": "FLAC",  "offset_db":  0.0, "note": "Qobuz 不开归一化，保留动态"},
    "Amazon Music HD":         {"loudness": -14, "codec": "FLAC",  "offset_db":  0.0, "note": "Auto-normalization 可在 App 关"},
    "QQ Music 无损":            {"loudness": -14, "codec": "FLAC",  "offset_db":  0.0, "note": "用户可在 App 设匹配（默认跟随系统）"},
    "本地 FLAC（无归一化）":      {"loudness": None, "codec": "FLAC", "offset_db":  0.0, "note": "动态范围保留最佳，建议 Poweramp 关闭 RVU"},
    "本地 ALAC":                {"loudness": None, "codec": "ALAC", "offset_db":  0.0, "note": "Apple 生态，bit-perfect 仅限 macOS Core Audio"},
    "本地 DSD/DSF":            {"loudness": None, "codec": "DSD",  "offset_db":  0.0, "note": "需 DAC 支持 DSD；Poweramp 需在设置中启用 DSD over PCM"},
}

# 每设备两音源的调整目标与听感差异说明（手写绑定，配合脚本计算的逐频段 delta）
# v4统一无损 = 合并在线无损（Apple Music Lossless / Tidal / Qobuz / Amazon Music HD / QQ 无损）+ 本地 FLAC
META = {
    "IE900复刻版": {
        "target_stream": "消除流媒体伪影放大风险：16-20kHz 编码剔除区正增益归零，"
                         "10-12.5kHz 镲片伪影区收敛，深潜补偿克制以保数字余量。",
        "diff_stream": "优化前（v3 + Spotify）：高频带轻微数字'沙沙'感，镲片毛刺略刺耳；"
                       "优化后：沙沙感与毛刺消失，中高频细节与 6k 架桥补偿保持，低频下潜稍收敛但更干净。",
        "target_unified": "无损内容下完整保留复刻架构的细节与延伸：6kHz 架桥与 3kHz 解析补偿不受影响，"
                          "12.5-20kHz +0.3dB 发挥 Hi-Res 优势（仅本设备启用 Hi-Res boost）。",
        "diff_unified": "优化前：v3 高频到顶但延伸保守；优化后：在线/本地无损下空气感与泛音尾音更连贯，"
                        "1k 轰头收敛段在 Apple Music Lossless 等 -16 LUFS 归一化下仍保有余量。",
        "conditions": [
            "FLAC/ALAC ≥ 16bit/44.1kHz（CD 质量或更高）",
            "复刻单元可解析 Hi-Res（7mm 动圈架构的延伸极限）",
            "建议 Apple Music Lossless 用户在 Poweramp 端 preamp 再 -0.5dB（-16 LUFS 补偿）",
            "前端输出阻抗 ≤ 4Ω（32Ω 标称对前端敏感）",
        ],
    },
    "Sony XB12双音箱组合": {
        "target_stream": "被动辐射器深潜增益 ×0.7（响度归一化下省动态余量），"
                         "16-20kHz 伪影区归零。",
        "diff_stream": "优化前：极高频偶现'嘶啦'感、深潜略浪费动态；优化后：极高频干净，"
                      "低频弹性保持，大音量余量更足（preamp 负值减小）。",
        "target_unified": "物理受限设备的统一无损方案：维持 v3 不变（便携音箱物理极限不随音源改变）。"
                          "若内容确为 24/96 Hi-Res，可在 Poweramp GUI 内手动抬 12.5-20k 段 +0.3dB。",
        "diff_unified": "优化前/后差异极小：便携蓝牙音箱的频响边界由单元物理决定；"
                        "统一无损方案不引入任何额外修改，避免对物理受限设备过度处理。",
        "conditions": [
            "任一无损源（在线/本地）——本设备频响边界不因音源改善",
            "推荐满电使用（低电量音量衰减属硬件，非 PEQ 范畴）",
            "听音距离 ≤ 1m（被动辐射器耦合需近场）",
        ],
    },
    "1圈14铁耳机": {
        "target_stream": "EST 超高频在流媒体下无真实内容，16-20kHz 增益归零防伪影；"
                         "人声与双分频点补偿不受影响。",
        "diff_stream": "优化前：超高频增益只放大编码噪声，听感略'毛'；优化后：中频人声扎实度"
                       "与分频点衔接保持，高频干净自然。",
        "target_unified": "EST 50kHz 延伸的无损发挥：12.5-20kHz +0.3dB 释放超高频单元的架构优势，"
                          "350Hz/3000Hz 双分频点补偿在所有无损源下稳定。",
        "diff_unified": "优化前：高频顺滑但空气感保守（流媒体 / 早期 v3）；"
                        "优化后：泛音与空间残响在无损下丰富，'耐听'底子上叠加'细腻'。",
        "conditions": [
            "FLAC/ALAC ≥ 16bit/44.1kHz（CD 起步）",
            "推荐 24bit/96kHz 以上（充分发挥 EST 50kHz 延伸）",
            "前端输出阻抗 ≤ 2Ω（12-20Ω 标称极敏）",
            "音量 ≤ 70%（底噪敏感）",
        ],
    },
    "HD800耳机": {
        "target_stream": "16-20kHz 归零（流媒体无内容）、10-12.5kHz 收敛防锐利伪影、"
                        "20-31Hz 低频平台 ×0.7 适配响度归一化音轨。",
        "diff_stream": "优化前：流媒体下高频偶有数字刺感、+4dB 级低频平台在归一化音轨上略过；"
                       "优化后：更耐听均衡，最大音量余量增加（preamp 由 -9.2 收敛）。",
        "target_unified": "无损下完整保留低频平台（+5.9dB）与 6.5k 窄带收敛（-2.5dB），"
                          "12.5-20kHz +0.3dB 释放开放式大耳标志性的空气感与堂音。",
        "diff_unified": "优化前：声场通透但极高频略保守；优化后：完整 51kHz 延伸在无损下可闻，"
                        "0.02% THD 余量内低频平台无失真（Hi-Res 母带可让低频量感更明显）。",
        "conditions": [
            "FLAC ≥ 16bit/44.1kHz；推荐 24bit/96kHz（51kHz 单元延伸需要 Hi-Res 内容）",
            "耳放输出阻抗 ≤ 10Ω（300Ω 标称需优质耳放）",
            "110Hz 处 650Ω 阻抗谐振峰附近低频会被某些耳放自然抬升——若低频过隆，把 110Hz 段 -2dB",
        ],
    },
    "Micra K13车载音响": {
        "target_stream": "原厂全频单元对编码伪影放大明显：12.5-20kHz 全面收敛，深潜 ×0.7，"
                         "人声可懂度补偿（2.5k）不动。",
        "diff_stream": "优化前：车内听流媒体高频'嘶啦'感明显；优化后：高频干净许多，"
                       "人声清晰度不变，ANC/路噪下可闻改善。",
        "target_unified": "物理受限设备：原厂全频单元在 15-20kHz 已截止，无损内容无可闻延伸，"
                          "维持 v3 不变（高频补偿段在物理频带外）。",
        "diff_unified": "优化前/后无差异：车载原厂全频单元的频响边界由硬件决定，"
                        "无损源相比有损源对该设备无可闻改进；保留 v3 配置即可。",
        "conditions": [
            "任一无损源——本设备物理高频止于 15-20kHz",
            "车机音量建议下调 2 格使用（无外置功放，单元功率余量小）",
            "驾驶位校准（离轴响应差）",
        ],
    },
    "BGVP Scale Pro": {
        "target_stream": "10-12.5kHz 正增益收敛防伪影揭示（'明亮不刺'特质易被编码毛刺干扰），"
                         "16-20kHz 归零。",
        "diff_stream": "优化前：流媒体下明亮感中混入毛刺；优化后：恢复其招牌的顺滑耐听，"
                       "人声厚度与分频点结像保持。",
        "target_unified": "无损下 12.5-20kHz +0.3dB 发挥 HVEK 动铁高频延伸，"
                          "2.5kHz 分频点收敛在所有无损源下稳定。",
        "diff_unified": "优化前：明亮但极高频保守；优化后：亮度延伸更完整，齿音控制依旧良好。",
        "conditions": [
            "FLAC/ALAC ≥ 16bit/44.1kHz（CD 起步）",
            "前端输出阻抗 ≤ 2Ω（17Ω 标称 + 113dB/mW 极敏）",
            "音量 ≤ 60%（底噪敏感）",
        ],
    },
    "Samsung S25 Plus手机扬声器": {
        "target_stream": "手机扬声器在 >16kHz / <40Hz 无实际输出，规则性收敛对可闻频段"
                         "几乎无影响（20-31Hz 微量正增益 ×0.7）。",
        "diff_stream": "两版差异极小：有损音源对该设备可闻频段（125Hz-10kHz）影响有限，"
                       "实测 100-315Hz 填补与线性度修正全部保留。",
        "target_unified": "物理受限设备：超薄机身 -3dB 截止 >100Hz，>16kHz 无实际输出，"
                          "无损源对该设备无可闻改进。维持 v3 不变。",
        "diff_unified": "优化前/后无差异：手机扬声器的物理边界由单元与腔体决定，"
                        "无损源相对有损源无可闻改进；保留 v3 配置即可。",
        "conditions": [
            "任一无损源——本设备物理频响边界由超薄机身决定",
            "声像偏下需系统 Dolby Atmos 声道平衡（全局 EQ 不可修）",
        ],
    },
    "OPPO A5 4G手机扬声器": {
        "target_stream": "v3 干预已是 ±0.5dB 最小级且无正增益位于伪影区——完全不变，"
                         "流媒体与本地可共用。",
        "diff_stream": "无变化：该设备无需音源变体，保留一套 v3 即可。",
        "target_unified": "物理受限设备：v3 已是 ±0.5dB 最小干预，无损源无可闻改进。"
                          "维持 v3 不变。",
        "diff_unified": "优化前/后无差异：保留 v3 即可。",
        "conditions": [
            "任一无损源——本设备 v3 干预幅度已极小",
            "通道平衡向顶部扬声器偏置 1-2 格（系统设置）",
        ],
    },
    "Ugreen Hitune T8降噪耳机": {
        "target_stream": "通勤流媒体主场景：TWS 对伪影敏感，10-20kHz 全面收敛"
                         "（16-20k 归零、10-12.5k -0.5），深潜 ×0.7 保节奏感。",
        "diff_stream": "优化前：地铁里流媒体齿音毛刺经 LDAC 链路被放大；优化后：人声干净突出，"
                       "ANC 下节奏感保持。",
        "target_unified": "TWS+蓝牙的物理限制：BT 带宽上限决定无损内容传输的最高质量（LDAC 990kbps 上限 96k/24bit）。"
                          "维持 v3 不变——BT 已把 Hi-Res 优势压缩至接近 CD 质量水平。",
        "diff_unified": "优化前/后差异极小：BT 链路本身已是瓶颈；无损与有损在 TWS 上"
                        "的差异主要在元数据完整度（无静音帧/无伪影区），不是频响。"
                        "若启用 LDAC 990kbps 模式可手抬 12.5-20k +0.3dB（边际收益）。",
        "conditions": [
            "在线无损 / 本地无损——本设备频响边界由 BT 链路决定",
            "推荐 LDAC 990kbps 模式（aptX HD 576k 仅 48k/24bit）",
            "ANC 开关需分别校准（ANC 改变低频感知）",
        ],
    },
    "Nissan X-Trail车载音响": {
        "target_stream": "原厂仪表台高音把编码伪影放大可闻：10-20kHz 收敛、20kHz 归零，"
                         "分频点 3k 干涉补偿与人声密度保持。",
        "diff_stream": "优化前：流媒体下仪表台高音'沙沙'感可闻；优化后：高频干净，"
                       "人声轮廓与结像改善保持。",
        "target_unified": "物理受限设备：两分频+20W 额定+离轴响应，"
                          "无损源在该标准版音响上无可闻改进。维持 v3 不变。",
        "diff_unified": "优化前/后无差异：原厂 6 扬声器的物理上限由功放与扬声器决定，"
                        "无损源对这套音响无可闻改进；保留 v3 即可。",
        "conditions": [
            "任一无损源——本设备物理边界由原厂音响决定",
            "车机音量建议下调 2 格使用（20W 额定功率动态余量小）",
            "高速副本：1k/3k 各 +0.5dB（路噪掩蔽补偿）",
        ],
    },
    "Sony MDR-1ABT": {
        "target_stream": "1-2kHz 人声推前段不受流媒体编码影响（人声基频不丢失），"
                         "10-16kHz DSEE/LDAC 频段中 ≥16k 归零（编码剔除区，徒增伪影），"
                         "12.5kHz 段轻收，5kHz 齿音下缘适度收敛防 Ogg 编码器预回声揭示。",
        "diff_stream": "优化前：流媒体下 5kHz 镲片/人声边缘偶有'毛刺'、16-20kHz 增益只放大嘶声；"
                       "优化后：齿音下缘顺滑，超高频不再嘶叫，1-2kHz 人声前移段在两种音源下均稳定。",
        "target_unified": "BT 4.0 LDAC 上限 96k/24bit 已是'伪 Hi-Res'：DAC 与单元限制下无损源优势仅在元数据完整度。"
                          "维持 v3 不变——1-2kHz 人声补偿不受音源影响。",
        "diff_unified": "优化前/后差异极小：BT 4.0 + 24Ω/98dB + 封闭式设计的瓶颈在物理链路上，"
                        "无损源对比有损源在该设备的可闻差异极小。",
        "conditions": [
            "在线无损 / 本地无损——BT 4.0 LDAC 已是瓶颈",
            "推荐有线模式（24Ω/98dB 单元可被手机直推）",
            "户外需注意全包裹隔音（设计权衡，无法通过 EQ 解决）",
        ],
    },
    "Bose QC 45": {
        "target_stream": "Bose 主动滚降区 ≥10kHz 在 Ogg Vorbis 编码下无可闻内容，"
                         "归零收敛防伪影放大；8kHz 'Veiled' 起始段适度收敛；"
                         "40Hz sub-bass 与 2.5kHz 人声核心段不受流媒体影响（编码不丢失这两段）保持 v3。",
        "diff_stream": "优化前：流媒体下'Veiled' + 编码毛刺同时存在，高频像'隔了层纱'；"
                       "优化后：高频'开纱'感，伪影不放大；2.5kHz 人声在两种音源下信噪比收益一致。",
        "target_unified": "Bose 动态 EQ + ANC + 封闭式物理瓶颈：BT 5.1 + ANC 设计上限。"
                          "维持 v3 不变——2.5kHz 人声核心与 8kHz 'Veiled' 修复对所有无损源稳定。",
        "diff_unified": "优化前/后差异极小：Bose 架构自身已含动态 EQ，"
                        "外部 EQ 叠加边际收益小；无损源对比有损源在 BT 5.1 链路下无可闻改进。",
        "conditions": [
            "在线无损 / 本地无损——BT 5.1 + ANC 已是瓶颈",
            "Bose App 内置 EQ 必须关闭以免双 EQ 叠加失真",
            "ANC ON/OFF 需分别校准（ANC 改变低频感知）",
        ],
    },
}


def apply_stream(bands: list) -> tuple[list, list]:
    """流媒体规则，返回 (新 bands, 变更记录 [(freq, old, new)])。"""
    out, deltas = [], []
    for b in bands:
        f, g = b["frequency"], b["gain"]
        g2 = g
        if f >= 16000 and g > 0:
            g2 = 0.0
        elif 10000 <= f < 16000 and g > 0:
            g2 = round(g - 0.5, 1)
        elif f in (20, 25, 31) and g > 0:
            g2 = round(g * 0.7, 1)
        if g2 != g:
            deltas.append((f, g, g2))
        out.append({**b, "gain": g2})
    return out, deltas


def apply_unified(bands: list, hi_res_capable: bool) -> tuple[list, list]:
    """统一无损规则（在线无损 + 本地无损合并），返回 (新 bands, 变更记录)。

    核心思路：v4流媒体的三条规则（≥16k 归零 / 10-12.5k 收敛 / 深潜 ×0.7）
    都是为了补偿 Ogg/AAC 有损编码伪影。无损源不引入这些伪影，故**全部不再施加**。
    唯一保留的规则：hi_res_capable 设备 12.5-20kHz +0.3dB 释放 Hi-Res 空气感
    （保守于原 v4本地音源的 +0.5dB，确保同时适配在线/本地）。
    """
    out, deltas = [], []
    for b in bands:
        f, g = b["frequency"], b["gain"]
        g2 = g
        # 仅 Hi-Res 设备：12.5-20kHz 正增益 +0.3dB
        if hi_res_capable and 12500 <= f <= 20000 and g > 0:
            g2 = round(g + 0.3, 1)
        if g2 != g:
            deltas.append((f, g, g2))
        out.append({**b, "gain": g2})
    return out, deltas


def _fmt_freq(f: int) -> str:
    return f"{f/1000:g}kHz" if f >= 1000 else f"{f}Hz"


def main() -> int:
    now = now_iso()
    ensure_dir(EXPORT_STREAM)
    ensure_dir(EXPORT_UNIFIED)

    v3_files = sorted(PROFILE_DIR.glob("*v3.json"))
    assert len(v3_files) == 12, f"应找到 12 个 v3 档案，实际 {len(v3_files)}"

    # 全局服务特定 preamp 偏移（用于档案 JSON 与报告"服务偏移表"）
    services_offset_lines = [
        f"| {name} | {info['codec']} | "
        f"{info['loudness'] if info['loudness'] is not None else '不归一化'} LUFS | "
        f"{info['offset_db']:+.1f} dB | {info['note']} |"
        for name, info in UNIFIED_SERVICES.items()
    ]

    report = [
        "# PEQ 优化方案 v4 —— 音源适配版（流媒体有损 / 统一无损）",
        "",
        f"生成时间：{now}　|　基准：v3 31 段配置（31 段 PK、Q=4.32、1/3 倍频程 ISO 频栅）"
        "　|　计算引擎：poweramp-peq-tuner",
        "",
        "## 决策树：按你的音源选变体",
        "",
        "```",
        "你的音源是？",
        "├─ 在线有损 (Spotify 320k / Apple Music 标准 / QQ MP3 / 网易云标准)",
        "│   └─ 用 v4流媒体（防伪影放大）",
        "├─ 本地有损 (MP3 128-320k / AAC 256k 文件)",
        "│   └─ 用 v4流媒体（同上有损编码特性）",
        "├─ 在线无损 (Apple Music Lossless / Tidal HiFi / Qobuz / Amazon Music HD / QQ 无损)",
        "│   └─ 用 v4统一无损（按下方服务偏移表调 preamp）",
        "├─ 本地无损 (FLAC / ALAC / DSF 文件)",
        "│   └─ 用 v4统一无损（Poweramp 关闭 RVU 保留动态）",
        "└─ 不确定 / 混用",
        "    └─ 优先用 v4统一无损（无损内容可听化更完整）；流媒体切换时手动 set-active",
        "```",
        "",
        "## 服务特定 preamp 偏移表（v4统一无损 基础上额外调整）",
        "",
        "每个 v4统一无损 档案已按主流量无损服务的响度归一化策略预设偏移。"
        "导入后根据实际订阅的服务在 Poweramp GUI 内调整 preamp 滑条：",
        "",
        "| 服务 | 编码 | 响度归一化 | 额外 preamp 偏移 | 备注 |",
        "|---|---|---|---|---|",
        *services_offset_lines,
        "",
        "## Poweramp 必关项目（避免双 EQ / 重采样损失）",
        "",
        "- **关 ReplayGain / Sound Check**（Poweramp 设置 → 音频 → Replay Gain → 关）"
        "—— 服务端已做响度归一化时，本地再做会双重压峰",
        "- **关系统 EQ**（Android：开发者选项 → 禁用绝对音量；iOS：Settings → Music → EQ → Off）"
        "—— 避免与 Poweramp EQ 串联",
        "- **开 High Quality Output / Direct**（Poweramp 设置 → 音频 → Output → Direct/USB DAC）"
        "—— 避免 Android 混音器 48kHz 重采样",
        "- **DSD 启用 DSD over PCM**（仅本地 DSD/DSF 用户，Poweramp 设置 → 音频 → DSD over PCM → 开）",
        "- **蓝牙设备优先 LDAC 990kbps / aptX HD**（Android 开发者选项 → 蓝牙音频编码）"
        "—— 避免 SBC/AAC 有损编码对无损内容的二次压缩",
        "",
        "## 音源规则",
        "",
        "| 变体 | 规则 | 声学依据 |",
        "|---|---|---|",
        "| v4流媒体 | ≥16kHz 正增益归零（负增益保留） | 心理声学编码剔除该频段，增益只放大伪影 |",
        "| v4流媒体 | 10–12.5kHz 正增益 -0.5dB | 镲片/齿音区编码伪影收敛 |",
        "| v4流媒体 | 20/25/31Hz 正增益 ×0.7 | 响度归一化压动态，深潜段省数字余量 |",
        "| v4统一无损 | ≥16kHz / 10-12.5kHz / 20-31Hz 均**不施加流媒体规则** | 无损不引入这些伪影 |",
        "| v4统一无损 | 仅 hi_res_capable 设备 12.5–20kHz +0.3dB | 发挥 Hi-Res 内容优势（保守于原 v4本地音源 +0.5） |",
        "| v4统一无损 | 物理受限设备（手机/便携/车载）维持 v3 | 频响边界由硬件决定 |",
        "",
        "## 调优优先级顺序（按序执行）",
        "",
        "1. 先导入**v4统一无损**（与 v3 最接近 + Hi-Res boost）作为基线；",
        "2. 同一曲目用 v4统一无损 与 v4流媒体 A/B，确认无损源与有损源在该设备的可闻差异；",
        "3. 切换到当前实际订阅的服务，按上表调 Poweramp preamp 滑条；",
        "4. 启用 LDAC 990kbps（蓝牙用户）/ 独占模式（有线用户）做二次校准；",
        "5. 日常按当前音源用 `peq_cli.py set-active` 切换档案；",
        "6. OPPO A5 / X-Trail 标准版等物理受限设备两变体几乎相同，保留一套即可。",
        "",
        "**附注**：",
        "- Spotify 免费档（160kbps Ogg）建议在 v4流媒体 基础上将 10–12.5kHz 再各 -0.5dB；",
        "- 本地若实为 <192kbps 有损文件，请直接使用 v4流媒体（判定规则：码率低于 192kbps 即降级）；",
        '- Apple Music Lossless + iOS 用户需在 iPhone 端关闭"自动音量平衡"（设置 → 音乐 → 音量平衡 → 关）'
        "以避免与 Poweramp RVU 重复压峰。",
        "",
        "---",
        "",
        "## 各设备音源适配方案",
        "",
    ]

    total = 0
    for p in v3_files:
        v3 = json.loads(p.read_text(encoding="utf-8"))
        dev = v3["name"][:-2]          # 去掉 "v3" 后缀
        dtype = v3["device_type"]
        meta = META[dev]
        hi_res = hi_res_capable_of(dev)
        base_bands = v3["preset"]["bands"]
        assert len(base_bands) == 31

        # 三变体迭代（思路 A：流媒体有损 + 统一无损）
        variants = [
            ("v4流媒体", "stream", apply_stream(base_bands), EXPORT_STREAM,
             "Ogg Vorbis / AAC 有损编码适配"),
            ("v4统一无损", "unified", apply_unified(base_bands, hi_res), EXPORT_UNIFIED,
             "在线无损 + 本地无损合并方案"),
        ]

        report += [f"## {dev}（{dtype}，Hi-Res {'是' if hi_res else '否'}）", ""]

        for source, key, (bands, deltas), out_dir, desc in variants:
            preamp = compute_preamp(bands)
            preset = {
                "name": f"{dev} {source[2:]}适配（基准 {dev}v3）",
                "preamp": preamp, "parametric": True, "bands": bands,
            }
            warnings = validate_preset(preset)
            preset["warnings"] = warnings

            # 档案 JSON：注入服务偏移与元数据
            profile_extra = {
                "source_class": "lossy" if key == "stream" else "lossless",
                "hi_res_capable": hi_res,
                "assumed": {
                    "codec": "Ogg Vorbis 320kbps / AAC 256kbps" if key == "stream" else "FLAC/ALAC ≥ 16bit/44.1kHz",
                    "loudness": "-14 to -16 LUFS (service-dependent)" if key == "stream" else "service-dependent / -14 to -16 LUFS",
                    "bit_depth": "n/a" if key == "stream" else "16-24",
                    "sample_rate": "44.1k-48k" if key == "stream" else "44.1k-192k",
                },
                "service_preamp_offsets_db": (
                    {} if key == "stream" else {n: info["offset_db"] for n, info in UNIFIED_SERVICES.items()}
                ),
                "target": meta[f"target_{key}"],
                "listen_diff": meta[f"diff_{key}"],
                "conditions": meta.get("conditions", []),
                "deltas": [{"freq": f, "old": o, "new": n} for f, o, n in deltas],
            }

            profile = {
                "name": f"{dev}{source}", "device_type": dtype,
                "brand": v3.get("brand", ""), "model": f"{source[2:]}音源适配（{desc}）",
                "preference": f"custom_{source}", "intensity": 1.0,
                "locked": True, "active": False,
                "note": desc,
                "created_at": now, "updated_at": now,
                "base": f"{dev}v3", "source": source,
                "preset": preset,
                **profile_extra,
            }
            write_json(PROFILE_DIR / f"{dev}{source}.json", profile)
            write_text(out_dir / f"{dev}{source}-Poweramp.txt", render_poweramp_txt(preset))
            # render_equalizer_json() 返回预序列化字符串（已含 \n 转义），用 write_text
            write_text(out_dir / f"{dev}{source}-PowerampEQ.json", render_equalizer_json(preset))
            total += 1

            # 报告：每变体小节
            label = "流媒体有损" if key == "stream" else "统一无损"
            report += [
                f"### {label}版（`{dev}{source}`）",
                "",
                f"**调整目标**：{meta[f'target_{key}']}",
                "",
                f"**逐频段修改建议**（Q 全程 {GRID_Q} 不变；"
                f"{len(deltas)} 段有变化，其余 {31 - len(deltas)} 段维持 v3）：",
            ]
            if deltas:
                report += ["| 中心频率 | 增益 v3 → v4 | 修改依据 |", "|---|---|---|"]
                for f, o, n in deltas:
                    if f >= 16000:
                        why = "编码剔除区归零（仅流媒体），防伪影放大"
                    elif 10000 <= f < 16000:
                        why = "镲片/齿音伪影区收敛 -0.5dB（仅流媒体）"
                    elif f in (20, 25, 31):
                        why = "深潜段 ×0.7 适配响度归一化（仅流媒体）"
                    elif 12500 <= f <= 20000 and n > o:
                        why = "Hi-Res 内容空气感 +0.3dB（仅本设备 hi_res_capable）"
                    else:
                        why = "增益微调"
                    report.append(f"| {_fmt_freq(f)} | {o:+.1f} → {n:+.1f} | {why} |")
            else:
                report += ["无增益修改（该设备对此音源维持 v3 配置）。"]
            report += [
                "",
                f"**听感差异说明**：{meta[f'diff_{key}']}",
                "",
                f"**preamp**：`{preamp:+.1f} dB`（引擎按合成响应重算）",
            ]
            if key == "unified":
                report += [
                    "",
                    "**适用条件**：",
                    *[f"- {c}" for c in meta.get("conditions", [])],
                ]
            report += [
                "",
                f"导出：`exports/v4/{'流媒体' if key == 'stream' else '统一无损'}/"
                f"{dev}{source}-Poweramp.txt` / `-PowerampEQ.json`",
                "",
            ]
        report += ["---", ""]

    REPORT.write_text("\n".join(report), encoding="utf-8", newline="\n")
    print(f"完成：{total} 个 v4 变体（12 设备 x {len(variants)} 音源）")
    print(f"档案 -> {PROFILE_DIR}；预设 -> {EXPORT_STREAM} 与 {EXPORT_UNIFIED}；报告 -> {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
