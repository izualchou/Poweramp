# -*- coding: utf-8 -*-
"""基于《声学特点.txt》实测/技术数据的 PEQ v2 系统性重设计驱动脚本。

与 31 段网格方案（v1）的区别：v2 以设备具体声学数据（阻抗谐振峰、THD、
分频点、ANC 带宽、被动辐射器、离轴响应等）为依据，使用少量目标明确的
滤波器（PK/低架/高架混合），每个滤波器绑定声学依据与预测效果。

输出：
  peq-profiles/<设备名>v2.json            设备档案（locked）
  exports/v2/<设备名>v2-Poweramp.txt       Poweramp 主应用导入
  exports/v2/<设备名>v2-PowerampEQ.json    Poweramp Equalizer 导入
  PEQ优化方案v2-声学重设计.md              完整方案（目标/现状/滤波器/依据/步骤）

依赖：peq_common（共享常量/路径/IO）+ peq_engine（确定性计算/校验/渲染）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\izual\.codebuddy\skills\poweramp-peq-tuner\scripts")
from peq_common import (  # noqa: E402
    PROFILE_DIR, export_dir_for, now_iso, ensure_dir, write_json, write_text,
    validate_device_coverage,
)
from peq_engine import (  # noqa: E402
    TYPE_LOW_SHELF,
    TYPE_PEAK,
    TYPE_HIGH_SHELF,
    compute_preamp,
    render_equalizer_json,
    render_poweramp_txt,
    validate_preset,
)

TYPE_MAP = {"PK": TYPE_PEAK, "LSC": TYPE_LOW_SHELF, "HSC": TYPE_HIGH_SHELF}
TYPE_CN = {"PK": "峰值", "LSC": "低搁架", "HSC": "高搁架"}

EXPORT_DIR = export_dir_for("v2")
REPORT = Path("PEQ优化方案v2-声学重设计.md")

DEVICES = [
    {
        "name": "IE900复刻版", "device_type": "iem_dynamic",
        "target": "干净下盘、顺滑衔接的中高频；保留 X3R 结构的细节揭示力",
        "metrics": "频响偏差 ±3dB（100Hz-10kHz，以 500Hz 为基准）；THD <1% @正常听音音量"
                   "（通过中低频负增益降低单元行程实现）；6kHz 陷波补偿后 5-8kHz 段无 >2dB 谷",
        "status": "阻抗 32Ω（对前端输出阻抗敏感）；THD 标称可达 3%；Helmholtz 共振腔调校不足"
                  "致低频轰头；6kHz 陷波处理不当致中高频衔接不自然；高频延伸受限",
        "filters": [
            {"t": "PK", "f": 100, "g": -3.5, "q": 1.1,
             "why": "Helmholtz 共振腔（低频导管）调校不到位的轰头主频段",
             "fx": "低频浑浊与掩蔽效应收敛，中频细节浮出"},
            {"t": "LSC", "f": 45, "g": 2.0, "q": 0.7,
             "why": "共振腔工作频段以下保留真实下潜；宽缓转折避免与 100Hz 收敛段打架",
             "fx": "下潜有量而不轰，低频弹性改善"},
            {"t": "PK", "f": 6000, "g": 2.0, "q": 1.4,
             "why": "6kHz 陷波（复刻加工精度不足的衔接断点）中心架桥补偿",
             "fx": "中高频衔接自然，乐器泛音连贯"},
            {"t": "PK", "f": 3000, "g": 1.0, "q": 1.4,
             "why": "X3R 三腔体结构意图提升的细节揭示频段，复刻版普遍不足",
             "fx": "中高频密度与解析改善"},
            {"t": "HSC", "f": 12000, "g": 1.5, "q": 0.7,
             "why": "复刻版高频延伸常受限（标称 20kHz 实际打折）",
             "fx": "高频通透度与空气感补偿"},
        ],
        "advice": "THD 3% 的复刻单元行程红线低：先启用 100Hz 收敛段再启用其余段；"
                  "若大音量发毛，优先降 3k/6k 增益而非整体音量。",
    },
    {
        "name": "Sony XB12双音箱组合", "device_type": "portable_speaker",
        "target": "干净有弹性的低频、无颗粒感的中频、不嘶叫的高频；保留成对立体声的声场优势",
        "metrics": "100-250Hz 隆起收敛至 +2dB 内；6-10kHz 嘶声区 -2dB；THD <3% @70% 音量；"
                   "极高频（>14kHz）不强推（物理已衰减）",
        "status": "46mm 单元+被动辐射器低频增强；中频颗粒感/鼻音感；高频突出带嘶嘶声；"
                  "极高频衰减；实际 -3dB 低频截止远高于标称 20Hz；成对 +3-6dB 声压",
        "filters": [
            {"t": "PK", "f": 125, "g": -3.0, "q": 1.0,
             "why": "被动辐射器与主动单元协同过量的低频隆起主频段",
             "fx": "低频干净、下潜与量感平衡恢复"},
            {"t": "LSC", "f": 60, "g": 1.5, "q": 0.7,
             "why": "辐射器有效工作区下缘的可用下潜，宽转折不与 125Hz 收敛冲突",
             "fx": "保留'这个尺寸令人惊讶'的低频质感"},
            {"t": "PK", "f": 1000, "g": -1.5, "q": 1.4,
             "why": "单只 XB12 的中频颗粒感/鼻音感集中区",
             "fx": "人声与乐器质感纯净度提升"},
            {"t": "PK", "f": 8000, "g": -2.0, "q": 2.8,
             "why": "高频'嘶嘶声'窄带收敛（Q 取窄避免误伤整体亮度）",
             "fx": "高频顺滑不刺，齿音与镲片收敛"},
            {"t": "HSC", "f": 14000, "g": 1.0, "q": 0.7,
             "why": "极高频物理衰减的轻度补偿（被动方案，不追求还原）",
             "fx": "高频延伸'到顶'的听感改善"},
        ],
        "advice": "被动辐射器对音量敏感：先在 70% 音量下校准，满音量时低频收敛段"
                  "（125Hz）可再降 0.5dB。",
    },
    {
        "name": "1圈14铁耳机", "device_type": "iem_hybrid",
        "target": "四分频频段无缝衔接、人声扎实、超高频延伸可听化",
        "metrics": "200-500Hz 与 2-4kHz 分频点凹陷补偿至 ±1.5dB；频响偏差 ±2dB（声道匹配 <2dB 基础上）；"
                   "THD 不劣于原厂（增益全部 ≤1.5dB）",
        "status": "1DD+14BA+EST，4 分频/4 声孔，Multitube 多路滤波；阻抗 12-20Ω（输出阻抗敏感）；"
                  "灵敏度 105-108dB/mW；分频点 200-500Hz 与 2-4kHz 存在相位抵消风险（声音脱节/结像模糊）",
        "filters": [
            {"t": "PK", "f": 350, "g": 1.0, "q": 0.9,
             "why": "200-500Hz 低段分频点相位抵消的能量补偿（宽 Q 跨越分频区）",
             "fx": "低频向中频衔接连贯，鼓点到人声不断层"},
            {"t": "PK", "f": 3000, "g": 1.0, "q": 1.0,
             "why": "2-4kHz 高段分频点相位抵消补偿",
             "fx": "结像聚焦，人声与高频乐器不'脱节'"},
            {"t": "LSC", "f": 60, "g": 1.5, "q": 0.7,
             "why": "动圈单元负责的低频氛围强化（其架构强项）",
             "fx": "低频弹性与氛围感增强"},
            {"t": "HSC", "f": 10000, "g": 1.0, "q": 0.7,
             "why": "EST 静电单元 50kHz 延伸的可听频段衔接",
             "fx": "超高频空气感与泛音细节"},
        ],
        "advice": "低阻抗高灵敏：搭配 ≥1Ω 输出阻抗前端时先听再调——若前端低频分压增益明显，"
                  "60Hz 低架减半。",
    },
    {
        "name": "HD800耳机", "device_type": "open_headphone",
        "target": "补齐低频量感、收敛 6-7kHz 锐利、保持极致声场",
        "metrics": "20-100Hz 低频平台 +4-5dB（THD 0.02% 余量内安全）；6-7kHz 峰值收敛 -2.5dB；"
                   "整体频响偏差 ±2.5dB；THD <0.05% @1Vrms 维持",
        "status": "56mm 开放式环形动圈；300Ω、110Hz 处 650Ω 阻抗谐振峰；灵敏度 102dB/Vrms；"
                  "THD≤0.02%；<100Hz 低频滚降；6-7kHz 明显峰值（锐利感根源）",
        "filters": [
            {"t": "LSC", "f": 110, "g": 4.0, "q": 0.7,
             "why": "开放式低频滚降平台补偿；转角避开 110Hz 阻抗谐振峰激发（置于峰上方起坡）",
             "fx": "低频量感补齐，声场规模不受损"},
            {"t": "PK", "f": 40, "g": 2.0, "q": 1.2,
             "why": "次低频下潜加强（0.02% THD 的巨大余量允许适度提升）",
             "fx": "管风琴/电子乐低频氛围可闻"},
            {"t": "PK", "f": 6500, "g": -2.5, "q": 4.32,
             "why": "6-7kHz 固有峰值窄带收敛（锐利/刺耳感根源），窄 Q 不伤 5-8k 空气感",
             "fx": "高频锐利感消失、长时间聆听不疲劳"},
            {"t": "PK", "f": 5000, "g": -1.0, "q": 1.41,
             "why": "峰值下肩部顺滑处理，与 6.5k 窄带形成连续过渡",
             "fx": "中高频到高频过渡平顺"},
            {"t": "HSC", "f": 10000, "g": 1.0, "q": 0.7,
             "why": "斜置障板强项区的空气感微抬，弥补收敛后的亮度感知",
             "fx": "声场通透度保持"},
        ],
        "advice": "300Ω+110Hz 谐振峰：耳放输出阻抗 >10Ω 时低频会自然隆起，"
                  "此时 110Hz 低架增益减半。",
    },
    {
        "name": "Micra K13车载音响", "device_type": "car_audio",
        "target": "优先清晰度与高频细节，弥补无高音单元的空气感缺失",
        "metrics": "160-500Hz 浑浊区 -2~-3dB；2-8kHz +2dB（补偿离轴衰减）；"
                   ">15kHz 不强推（全频单元延伸极限）；THD 安全（负增益段降低 4Ω 单元负担）",
        "status": "4 只门板全频扬声器（无独立高音、无外置功放）；4Ω、90-93dB；"
                  "高频止于 15-20kHz、低频截止 60-80Hz；离轴响应差；门腔驻波致中低频浑浊",
        "filters": [
            {"t": "PK", "f": 200, "g": -2.5, "q": 1.0,
             "why": "门腔驻波激发的浑浊主频段（车门下部安装）",
             "fx": "中低频清晰、人声从背景中分离"},
            {"t": "PK", "f": 160, "g": -1.5, "q": 1.4,
             "why": "驻波区下肩处理，形成平滑谷形",
             "fx": "浑浊收敛无副作用"},
            {"t": "PK", "f": 2500, "g": 2.0, "q": 1.41,
             "why": "全频单元离轴衰减的人声可懂度补偿（听者不在单元轴向）",
             "fx": "人声与乐器轮廓清晰"},
            {"t": "HSC", "f": 6000, "g": 2.0, "q": 0.8,
             "why": "无独立高音单元的空气感/高频细节缺失补偿（止于 15-20kHz 内）",
             "fx": "高频细节与空间感改善"},
            {"t": "LSC", "f": 70, "g": 1.0, "q": 0.7,
             "why": "60-80Hz 截止以上的可用低频微补（门板单元极限内）",
             "fx": "低频存在感维持而不轰"},
        ],
        "advice": "顺序：先启用两个收敛段→听 10 分钟→再启用 2.5k/6k 补偿段；"
                  "后排听感受离轴物理限制，以前排驾驶位校准为准。",
    },
    {
        "name": "BGVP Scale Pro", "device_type": "iem_hybrid",
        "target": "保持耐听均衡，补下潜与中频厚度，稳固分频点结像",
        "metrics": "2-3kHz 分频区平整度 ±1.5dB；THD 维持 <1% 红线内（增益 ≤2dB）；"
                   "低频提升幅度适配低输出阻抗前端的自然低频增益",
        "status": "10mm DC 涂层动圈+HVEK 定制动铁；双音腔+电子/物理分频；17Ω、113dB/mW（极敏）；"
                  "THD<1%；分频点 2-3kHz 相位未对齐时 200Hz-2kHz 结像偏移；"
                  "低阻前端下动圈阻抗曲线与输出阻抗形成分压→低频增益",
        "filters": [
            {"t": "LSC", "f": 80, "g": 2.0, "q": 0.7,
             "why": "下潜补偿；对低输出阻抗前端的天然低频增益叠加，故取保守值",
             "fx": "下潜沉得下去、鼓点清晰"},
            {"t": "PK", "f": 400, "g": 1.0, "q": 1.0,
             "why": "用户反馈的人声厚度稍薄（200Hz-2k 结像偏移的听感结果）",
             "fx": "人声厚度与密度改善"},
            {"t": "PK", "f": 2500, "g": -1.0, "q": 1.4,
             "why": "2-3kHz 分频点能量堆积收敛，稳固结像（相位问题的能量域补偿）",
             "fx": "人声定位居中不飘、齿音控制保持"},
            {"t": "PK", "f": 8000, "g": 1.0, "q": 2.0,
             "why": "HVEK 动铁负责的高频衔接区微亮",
             "fx": "明亮不刺耳的特质保持"},
        ],
        "advice": "113dB 极敏：底噪大的前端建议音量 60% 以下使用；"
                  "preamp 已留余量，若仍削波先查前端增益而非 EQ。",
    },
    {
        "name": "Samsung S25 Plus手机扬声器", "device_type": "phone_speaker",
        "target": "填补实测中低频空洞、平滑高频线性度缺陷",
        "metrics": "100-315Hz 补至 +2.5~3dB（Notebookcheck 实测不足区）；2-16kHz 线性度偏差感知降低"
                   "（嘶声区 -1dB）；最大声压 90.9dB(A) 无失真维持；顶部扬声器声压差（声像偏下）"
                   "无法用全局 EQ 修复——需系统声道平衡配合",
        "status": "顶部（听筒位）+底部立体声；实测最大 90.9dB(A) 无失真；100-315Hz 输出显著不足；"
                  "400-2kHz 相对均衡；2-16kHz 线性度偏差 15-17%；顶部声压低于底部",
        "filters": [
            {"t": "PK", "f": 200, "g": 3.0, "q": 0.8,
             "why": "实测 100-315Hz 显著不足的核心段（超薄机身容积限制）",
             "fx": "鼓点冲击力与'体感'恢复，空洞感消除"},
            {"t": "PK", "f": 125, "g": 1.5, "q": 1.0,
             "why": "不足区下缘衔接（-3dB 截止高于 100Hz，不越界强推）",
             "fx": "低频下限平滑、无断崖感"},
            {"t": "PK", "f": 3150, "g": 1.0, "q": 1.4,
             "why": "2-16kHz 线性度问题的中段毛刺感补偿",
             "fx": "高频质感平滑、人声唇齿音自然"},
            {"t": "PK", "f": 6300, "g": -1.0, "q": 1.41,
             "why": "线性度偏差区最易发嘶的频段收敛",
             "fx": "大音量下毛刺感降低"},
        ],
        "advice": "顶部/底部频响不匹配导致的声像偏下：在系统 Dolby Atmos 设置中微调声道平衡"
                  "（EQ 为全局处理无法单独修）。",
    },
    {
        "name": "OPPO A5 4G手机扬声器", "device_type": "phone_speaker",
        "target": "轻度精修保持原厂饱满，人声对话清晰度微增",
        "metrics": "干预幅度 ≤1dB（保留原厂调音）；300% 软件增益建议 ≤200% 使用（防单元失真）；"
                   "底部>顶部的通道音量差（声像偏移）需系统设置配合",
        "status": "顶部+底部双扬声器（顶部非降级听筒，全频段输出）；Dolby Atmos 虚拟化上混；"
                  "底部音量显著大于顶部；300% 软件音量增强",
        "filters": [
            {"t": "PK", "f": 800, "g": 0.5, "q": 1.0,
             "why": "影音/通话场景的人声对话频段微抬",
             "fx": "台词可懂度提升"},
            {"t": "PK", "f": 3000, "g": 0.5, "q": 1.4,
             "why": "清晰度微调（保持 ±1dB 内最小干预原则）",
             "fx": "乐器亮度与细节略增"},
            {"t": "PK", "f": 250, "g": -0.5, "q": 1.0,
             "why": "轻度箱染收敛",
             "fx": "低频干净度微增"},
        ],
        "advice": "通道音量差：Dolby Atmos 或辅助功能中的左右平衡向顶部扬声器侧偏置 1-2 格。",
    },
    {
        "name": "Ugreen Hitune T8降噪耳机", "device_type": "bluetooth_headphone",
        "target": "通勤降噪场景下的人声清晰与节奏感保持",
        "metrics": "1.6-3.15kHz 人声可懂度 +1.5dB；ANC 带宽外缘（>4kHz，瞬态噪声抑制弱区）+1dB 补偿；"
                   "THD 无感（镀钛振膜刚性优势保持）；低频肥感段 -1.5dB",
        "status": "12.4mm 镀钛动圈；ANC -55dB 深度主要作用于 <1kHz、有效带宽至 4kHz（>4kHz 瞬态噪声"
                  "抑制弱）；LDAC/AAC/SBC；腔体导管限制高频延伸",
        "filters": [
            {"t": "PK", "f": 2000, "g": 1.5, "q": 1.41,
             "why": "ANC 有效区内的人声核心频段（降噪后此段信噪比最佳，增益收益最大）",
             "fx": "地铁中人声显著清晰"},
            {"t": "PK", "f": 5000, "g": 1.0, "q": 1.41,
             "why": "ANC 带宽外缘（4kHz+）环境泄漏声的掩蔽补偿",
             "fx": "通勤环境下高频细节不'缩水'"},
            {"t": "PK", "f": 150, "g": -1.5, "q": 1.0,
             "why": "TWS 入耳式常见低频肥感（12.4mm 大单元小腔体）",
             "fx": "低频干净、人声不闷"},
            {"t": "LSC", "f": 60, "g": 1.5, "q": 0.7,
             "why": "-55dB ANC 主要作用于 <1kHz，佩戴后低频节奏感感知被削",
             "fx": "节奏感与'身体感'维持"},
            {"t": "HSC", "f": 10000, "g": 1.5, "q": 0.7,
             "why": "腔体导管限制的高频延伸补偿（LDAC 高码率传送的高频信息可听化）",
             "fx": "高频延伸与空气感改善"},
        ],
        "advice": "先关 ANC 校准基础曲线，再开 ANC 微调 60Hz 低架与 5k 补偿段"
                  "（ANC 开关会改变频响）。",
    },
    {
        "name": "Nissan X-Trail车载音响", "device_type": "car_audio",
        "target": "清理标准版浑浊、修复两分频路径差干涉、大音量失真控制",
        "metrics": "160-630Hz 浑浊区 -2.5dB；2-4kHz 相位干涉区补偿 +1.5dB；20W 额定功率动态余量内"
                   "（大音量热压缩：负 preamp+收敛段保护）；THD 大音量不破",
        "status": "6 扬声器：仪表台高音+门板中低音（两分频被动分频）+后门全频；前门 4Ω/20W 额定；"
                  "高音与中低音声学路径差大→2-4kHz 相位干涉（凹陷或峰）；后门离轴限制后排高频",
        "filters": [
            {"t": "PK", "f": 200, "g": -2.5, "q": 1.1,
             "why": "门板中低音浑浊主频段（车门下部安装的驻波与腔体共鸣）",
             "fx": "中低频轮廓清晰、'浑浊六扬声器'主诉改善"},
            {"t": "PK", "f": 400, "g": -1.5, "q": 1.4,
             "why": "浑浊区上肩，与 200Hz 形成平滑谷",
             "fx": "人声频段下缘干净"},
            {"t": "PK", "f": 3000, "g": 1.5, "q": 1.4,
             "why": "高音（仪表台）与中低音（车门）路径差造成的 2-4kHz 分频点相位凹陷补偿",
             "fx": "分频区衔接平滑、结像高度上移至仪表台"},
            {"t": "HSC", "f": 8000, "g": 1.5, "q": 0.8,
             "why": "仪表台高音单元指向性补偿（听者耳位偏离高音轴向）",
             "fx": "高频细节与声场高度改善"},
            {"t": "PK", "f": 1000, "g": 1.0, "q": 1.0,
             "why": "人声密度（20W 额定功率动态余量内的安全增益）",
             "fx": "人声存在感增强"},
        ],
        "advice": "顺序执行：先 200/400Hz 收敛段→停红灯听人声→加 3k 干涉补偿→最后 8k。"
                  "高速场景建议另存副本并将 1k/3k 各 +0.5dB（路噪掩蔽）。",
    },
    {
        "name": "Sony MDR-1ABT", "device_type": "bluetooth_headphone",
        "target": "把万金油'均衡耐听'底子的人声从靠后（Recessed vocals）拉回居中前位，"
                  "同时保留 LDAC/DSEE 带来的高频延伸",
        "metrics": "1-2kHz 人声核心区 +1.5dB（推前中频）；4-6.3kHz 乐器存在感 +0.5dB"
                   "（不引入齿音）；10-16kHz +0.5dB 释放 LDAC/DSEE 频段；全部 ≤1.5dB 守 24Ω/98dB 单元裕量",
        "status": "40mm 镀铝液晶高分子振膜；24Ω @1kHz；98 dB/mW 灵敏度；4-100,000Hz（有线）"
                  "/20-20,000Hz（BT）；BT4.0+LDAC+aptX+NFC；DSEE 数字声音增强引擎；100mW 容量；"
                  "~300g；封闭式；用户评价'低频干净利落、中频中正不突出、高频控制不出齿音'，"
                  "但 What Hi-Fi 直言'Recessed vocals'、'Lack get-up-and-go'。",
        "filters": [
            {"t": "PK", "f": 1000, "g": 1.5, "q": 1.0,
             "why": "1kHz 'Recessed vocals' 核心：人声基频区被'中正'调音压到靠后",
             "fx": "人声从靠后移至居中前位，存在感显著增强"},
            {"t": "PK", "f": 2000, "g": 1.0, "q": 1.2,
             "why": "2kHz 人声频段上缘（前齿音区之前），补偿人声胸腔/口型感",
             "fx": "人声密度与清晰度提升（与 1kHz 配合形成宽带抬升）"},
            {"t": "PK", "f": 5000, "g": 0.5, "q": 1.4,
             "why": "5kHz 乐器存在感区（弦乐泛音、人声齿音下缘），微抬不引入齿音",
             "fx": "乐器泛音丰满、整体听感更'抓人'"},
            {"t": "HSC", "f": 12000, "g": 0.5, "q": 0.7,
             "why": "12kHz 补偿 LDAC/DSEE 释放的高频延伸（万金油调音本就在此处保守）",
             "fx": "高频空气感与声场微张，保持'控制不出齿音'的优势"},
        ],
        "advice": "顺序：1kHz→2kHz→5kHz 渐进听感；如发现齿音先降 5kHz 段。"
                  "户外/通勤建议另存副本将 125-200Hz 收敛 -0.5dB 防全包裹共振；"
                  "有线 vs LDAC 模式下曲线一致（DSEE 仅 BT 模式下有效）。",
    },
    {
        "name": "Bose QC 45", "device_type": "bluetooth_headphone",
        "target": "在 Bose 商业目标曲线（Bose Consumer Target）上做最小偏离："
                  "轻度收紧 Bose 偏多 sub-bass、补回被滚降遮蔽的中高频细节与空气感",
        "metrics": "25-50Hz sub-bass -1dB（Bose 目标曲线在 ANC ON 时偏暖）；"
                   "2-3.15kHz 人声可懂度 +1.5dB（ANC 模式被环境噪声掩蔽的优先补偿频段）；"
                   "6.3-10kHz 滚降遮蔽 +0.5~1dB；12.5-20kHz 空气感轻补 +0.5dB；"
                   "全部 ≤1.5dB 守 Bose 动态 EQ 算法输入裕量",
        "status": "Bose 2021-09-29 发布，240g；主动消噪（ANC）+ Aware 透明模式；"
                  "BT5.1（9m），24h 续航（ANC ON）；6 麦克风；动态音质均衡（音量自适应 EQ）；"
                  "用户痛点：'Veiled'（高频被滚降）、ANC OFF 时'Muddy bass'、"
                  "'Lack detail' vs HiFi、声场偏窄（封闭式物理上限）。",
        "filters": [
            {"t": "PK", "f": 40, "g": -1.0, "q": 0.8,
             "why": "40Hz sub-bass：ANC ON 时 Bose 主动提升（声学掩蔽对冲），轻收恢复平衡",
             "fx": "低频从'略糊'转'清晰有弹性'，不破坏 Bose 招牌的'低频量感'印象"},
            {"t": "PK", "f": 2500, "g": 1.5, "q": 1.2,
             "why": "2.5kHz 人声可懂度核心（ANC 噪声掩蔽下人耳最敏感频段）",
             "fx": "地铁/通勤人声从'雾里'变'清晰'，与 Bose 动态 EQ 形成稳态互补"},
            {"t": "PK", "f": 8000, "g": 1.0, "q": 1.4,
             "why": "8kHz 'Veiled' 滚降起始段补回，避免典型 ANC 耳机高频发暗",
             "fx": "镲片/齿音的空气感与细节回归，'Detail' 痛点改善"},
            {"t": "HSC", "f": 14000, "g": 0.5, "q": 0.7,
             "why": "14kHz Bose 主动滚降区轻补（封闭式物理衰减 14kHz 后趋零，留 0.5dB 余量）",
             "fx": "空气感微抬，声场'打开'感（封闭式物理上限内）"},
        ],
        "advice": "顺序：2.5k→8k→40Hz→14kHz 渐进；2.5kHz 最重要（信噪比收益最大）。"
                  "ANC ON/OFF 需分别校准（ANC 改变低频感知）；Bose 应用 EQ 建议先关闭以免双 EQ 叠加失真；"
                  "声场偏窄与降噪等级属硬件能力，EQ 不可改善。",
    },
    # ==================== 家用家庭影院（car_audio/speaker 类） ====================
    {
        "name": "三星HT-F5500W家庭影院", "device_type": "home_theater",
        "target": "对白优先：解除中低频对白掩蔽、抬升对白可懂度，"
                  "温和补无源炮量感与 ¾\" 高音空气感（不触碰物理滚降区）",
        "metrics": "160-315Hz 中低频 -2dB 级收敛；2.5-3.15kHz 对白区 +1.8~2dB；"
                   "60-100Hz 低架 +2dB（40-50Hz 滚降段不强推）；9kHz 高架 +1.5dB；"
                   "全部 ≤2dB 守无源炮与塑料卫星箱裕量",
        "status": "5.1 蓝光一体式家庭影院（2013 HTiB）；前置 2¾\"+¾\" 两分频、中置双 2\"+¾\"、"
                  "环绕单 2¾\"（无独立高音）；低音炮无源 6\"（功放内置主机）；"
                  "1000W PMPO（165W×4+170W×2 营销口径）；SWA-6000 无线环绕；"
                  "官方未公布频响/THD；用户痛点：对白被背景声淹没（Amazon/AVS Forum 最高频槽点）、"
                  "炮缺深度与冲击力、环绕后场偏暗",
        "filters": [
            {"t": "LSC", "f": 90, "g": 2.0, "q": 0.7,
             "why": "无源 6\" 小口径炮 60-100Hz 量感温和补偿；转角置于滚降区上方，不强推 40-50Hz 物理边界（推则打底失真）",
             "fx": "低频存在感增强，观影氛围改善而不轰"},
            {"t": "PK", "f": 220, "g": -2.0, "q": 1.2,
             "why": "塑料薄壁卫星箱谐振 + 小房间边界反射的 160-315Hz 染声——对白掩蔽的直接声学来源",
             "fx": "对白从配乐/环境音效中分离，中低频干净"},
            {"t": "PK", "f": 2800, "g": 2.0, "q": 1.2,
             "why": "2.8kHz 对白可懂度核心（用户最高频槽点：人声被淹没）；中置双 2\" 全频灵敏度受限区",
             "fx": "台词口型清晰、人声穿透力增强"},
            {"t": "HSC", "f": 9000, "g": 1.5, "q": 0.7,
             "why": "前置/中置 ¾\" 高音延伸有限的空气感补偿；环绕箱无独立高音（后场暗），全局保守处理不分离声道",
             "fx": "镲片/空间残响的空气感回归，听感不再发闷"},
        ],
        "advice": "顺序：先 220Hz 收敛→听 10 分钟→再 2.8kHz→最后 90Hz/9kHz；"
                  "音源设备须开 Dolby Digital 位流输出（否则中置偏弱、人声从全部音箱一起出）；"
                  "蓝牙播放后置无声时按遥控器 3D Sound 键；"
                  "避免与机内 DSP（3D Sound/夜间模式）叠加造成双 EQ 失真。",
    },
]


def main() -> int:
    ensure_dir(PROFILE_DIR)
    ensure_dir(EXPORT_DIR)
    # 启动时一次校验：v2 DEVICES 设备名必须与 peq_common.DEVICE_REGISTRY 一致
    missing, extra = validate_device_coverage([d["name"] for d in DEVICES])
    if missing or extra:
        raise AssertionError(
            f"v2 DEVICES 清单与 DEVICE_REGISTRY 不一致: missing={missing}, extra={extra}"
        )
    now = now_iso()

    report = [
        "# PEQ 优化方案 v2 —— 基于设备声学特性的系统性重设计",
        "",
        f"生成时间：{now}　|　依据：声学特点.txt（实测/技术数据）　|　计算引擎：poweramp-peq-tuner",
        "",
        "**与 v1（31 段网格）的区别**：v2 以每个滤波器绑定具体声学依据（阻抗谐振峰、THD、分频点、"
        "ANC 带宽、被动辐射器、离轴响应等），使用少量目标明确的 PK/低搁架/高搁架滤波器。"
        "Poweramp 参数 EQ 原生支持 PK/低搁架/高搁架三种类型；'低通/高通'类需求以陡峭搁架近似"
        "（搁架转折即等效截止点控制）。",
        "",
        "**通用调优步骤（按顺序执行）**：",
        "1. 导入预设前将媒体音量降至 50%，确认 preamp 已生效（防止导入瞬间削波）；",
        "2. 按滤波器排列顺序从低频到高频逐个启用，每启用一个 A/B 对比一次（关闭/开启该段）；",
        "3. 每段增益以 ±1dB 步进微调；某段'听不出差别'时直接禁用（减少处理损耗）；",
        "4. 全部启用后整体试听 10 分钟（疲劳感检查：高频段若有刺耳，优先降 6-8kHz 增益）；",
        "5. 场景切换（通勤/桌面/车载高速）用 peq_cli.py set-active 切换对应档案；",
        "6. 修改任一增益后必须同步检查 preamp 仍 ≤ -（最大合成正增益）。",
        "",
        "---",
    ]

    for idx, dev in enumerate(DEVICES, 1):
        bands = [
            {"type": TYPE_MAP[f["t"]], "frequency": int(f["f"]),
             "q": round(float(f["q"]), 2), "gain": float(f["g"])}
            for f in dev["filters"]
        ]
        bands.sort(key=lambda b: b["frequency"])
        preamp = compute_preamp(bands)
        preset = {"name": f"{dev['name']} v2 - 声学重设计", "preamp": preamp,
                  "parametric": True, "bands": bands}
        warnings = validate_preset(preset)
        preset["warnings"] = warnings

        profile = {
            "name": f"{dev['name']}v2", "device_type": dev["device_type"],
            "brand": "", "model": "v2 声学重设计（依据声学特点.txt）",
            "preference": "custom_v2", "intensity": 1.0,
            "custom_bands": [
                f"{f['t']} {int(f['f'])} {f['g']:g} {f['q']:g}" for f in dev["filters"]
            ],
            "locked": True, "note": "基于设备声学数据的系统性重设计",
            "active": False, "created_at": now, "updated_at": now,
            "target": dev["target"], "metrics": dev["metrics"],
            "status": dev["status"], "advice": dev["advice"],
            "filters_rationale": [
                {"freq": int(f["f"]), "type": f["t"], "gain": f["g"], "q": f["q"],
                 "why": f["why"], "effect": f["fx"]} for f in dev["filters"]
            ],
            "preset": preset,
        }
        write_json(PROFILE_DIR / f"{dev['name']}v2.json", profile)

        write_text(EXPORT_DIR / f"{dev['name']}v2-Poweramp.txt", render_poweramp_txt(preset))
        # render_equalizer_json() 返回预序列化字符串（已含 \n 转义），用 write_text
        write_text(EXPORT_DIR / f"{dev['name']}v2-PowerampEQ.json", render_equalizer_json(preset))

        report += [
            f"## {idx}. {dev['name']}",
            "",
            f"**目标听感**：{dev['target']}",
            "",
            f"**可量化指标**：{dev['metrics']}",
            "",
            f"**当前关键声学数据**：{dev['status']}",
            "",
            f"**优化后滤波器组**（preamp `{preamp:+.1f} dB`，导入顺序即表中顺序）：",
            "",
            "| # | 类型 | Fc (Hz) | 增益 (dB) | Q | 声学依据 | 预测改善效果 |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, f in enumerate(sorted(dev["filters"], key=lambda x: x["f"]), 1):
            report.append(
                f"| {i} | {TYPE_CN[f['t']]} | {int(f['f'])} | {f['g']:+.1f} | "
                f"{f['q']:g} | {f['why']} | {f['fx']} |"
            )
        report += [
            "",
            f"**执行提示**：{dev['advice']}",
            "",
            f"**导出文件**：`exports/v2/{dev['name']}v2-Poweramp.txt`、"
            f"`exports/v2/{dev['name']}v2-PowerampEQ.json`",
            "",
        ]
        if warnings:
            report += [f"**校验提示**：{'；'.join(warnings)}", ""]
        report += ["---", ""]

    REPORT.write_text("\n".join(report), encoding="utf-8", newline="\n")
    print(f"完成：{len(DEVICES)} 个 v2 方案 -> {EXPORT_DIR} / {PROFILE_DIR} / {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
