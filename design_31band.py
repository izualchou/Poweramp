# -*- coding: utf-8 -*-
"""十三款音频设备 Poweramp 31 段 PEQ 多轮迭代设计驱动脚本。

流程（每设备三轮）：
  R1 基于官方参数与用户反馈痛点设定初始修正曲线
  R2 针对典型听感缺陷（低频下潜/中频厚度/高频顺滑度/声场宽度）精细补偿
  R3 结合实际使用场景（通勤降噪/桌面立体声/车载嘈杂）验证微调

输出：
  peq-profiles/<设备名>.json        设备档案（locked，31 段定制）
  exports/31band/<设备名>-Poweramp.txt     Poweramp 主应用导入
  exports/31band/<设备名>-PowerampEQ.json   Poweramp Equalizer 导入
  31band-PEQ设计报告.md              逐轮依据、效果分析与最终参数

依赖：poweramp-peq-tuner 技能的 peq_engine（确定性计算/校验/渲染）。
共享常量/路径/IO/设备元数据从 peq_common 导入。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\izual\.codebuddy\skills\poweramp-peq-tuner\scripts")
from peq_common import (  # noqa: E402
    FREQS, DEFAULT_Q, PROFILE_DIR, export_dir_for, now_iso, ensure_dir, write_json, write_text,
    validate_device_coverage,
)
from peq_engine import (  # noqa: E402
    TYPE_PEAK,
    compute_preamp,
    render_equalizer_json,
    render_poweramp_txt,
    validate_preset,
)

EXPORT_DIR = export_dir_for("31band")
REPORT = Path("31band-PEQ设计报告.md")

DEVICES = [
    {
        "key": "ie900_replica", "name": "IE900复刻版", "device_type": "iem_dynamic",
        "brand": "Sennheiser复刻", "model": "IE900 style",
        "pain": "复刻动圈入耳。用户反馈：声场浑浊、低音与乐器泛音表现不佳、依赖前端驱动。",
        "r1_rationale": "官方参数（7mm单元、5Hz-48kHz、123dB）显示潜力在两端延伸；痛点集中在浑浊与泛音不足——收紧125-315Hz中低频堆积，抬升20-50Hz下潜与2.5-4kHz泛音轮廓。",
        "r1": {20: 3, 25: 3, 31.5: 3, 40: 2.5, 50: 2, 63: 1, 125: -1.5, 160: -2.5,
               200: -3, 250: -2.5, 315: -2, 2500: 1.5, 3150: 2, 4000: 1.5,
               5000: 1, 10000: 1, 12500: 1, 16000: 0.5},
        "r2_rationale": "精细补偿：400-630Hz补中频厚度防'薄'，8k空气感微抬增强声场纵深与高频顺滑度。",
        "r2": {400: 1, 500: 1, 630: 1, 800: 0.5, 6300: 0.5},
        "r3_rationale": "桌面/前端听音场景：安静环境下进一步收窄125Hz残留闷感，2k/1k微抬人声与结像密度。",
        "r3": {1000: 0.5, 2000: 0.5, 125: -0.5},
        "narrow": {},
        "analysis": "频响：低频下潜+3dB平台与125-315Hz收敛形成干净的下盘；2.5-4kHz泛音增益还原乐器轮廓。失真：中低频收敛降低单元中低频行程，间接降低低次谐波失真。主观：浑浊感改善、声场层次更清晰；建议搭配较好的前端以发挥瞬态潜力。",
    },
    {
        "key": "xb12_pair", "name": "Sony XB12双音箱组合", "device_type": "portable_speaker",
        "brand": "Sony", "model": "SRS-XB12 x2 立体声配对",
        "pain": "46mm单元'Extra Bass'调音中低频过肥；低电量时最大音量显著衰减；麦克风差（非EQ范畴）。",
        "r1_rationale": "官方'Extra Bass'导向使100-250Hz隆起3dB以上，遮蔽中高频细节——大幅收敛中低频，抬升2.5-12.5kHz解析与声场宽度（立体声配对后高频衔接更好）。",
        "r1": {63: -1.5, 80: -2, 100: -2.5, 125: -3, 160: -3, 200: -2.5, 250: -1.5,
               315: -1, 400: -0.5, 2500: 1, 3150: 1.5, 4000: 1.5, 5000: 1,
               6300: 1, 8000: 1.5, 10000: 1.5, 12500: 1, 16000: 0.5},
        "r2_rationale": "精细补偿：40-50Hz适度下潜补偿（小单元物理极限内），1.6-2k微抬改善人声与乐器分离度。",
        "r2": {31.5: 1.5, 40: 2, 50: 1.5, 800: 0.5, 1600: 0.5},
        "r3_rationale": "桌面立体声近场场景：1k/2k微抬人声；125Hz再收0.5dB防近场闷。低电量音量衰减无法用EQ修复——保留负preamp余量并建议满电使用（见报告失真控制说明）。",
        "r3": {1000: 0.5, 2000: 0.5, 125: -0.5},
        "narrow": {},
        "analysis": "频响：抵消Extra Bass染声后频响回归中性，立体声声场宽度进一步提升。失真：中低频-3dB显著降低小单元低频冲程与失真，同时缓解低电量限幅触发的概率。主观：低频干净有弹性、高频通透；麦克风与电量问题属硬件范畴，EQ不处理。",
    },
    {
        "key": "dd14ba", "name": "1圈14铁耳机", "device_type": "iem_hybrid",
        "brand": "qdc风格", "model": "1DD+14BA",
        "pain": "整体'中正细腻、低频弹性好、高频顺滑'；痛点：标准线材下人声偏薄，建议暖声前端。",
        "r1_rationale": "基础素质好，仅做最小幅度高频延伸增强（6.3-10kHz微抬），保留其耐听底子。",
        "r1": {6300: 0.5, 8000: 0.5, 10000: 0.5},
        "r2_rationale": "精细补偿（用EQ替代换线/换前端）：500-800Hz人声厚度核心区+1.5dB，向两侧平滑过渡至250-1.6kHz，矫正'人声偏薄'。",
        "r2": {250: 1, 315: 1, 400: 1, 500: 1.5, 630: 1.5, 800: 1, 1000: 1,
               1250: 0.5, 1600: 0.5},
        "r3_rationale": "日常/通勤便携场景：轻度环境噪声掩蔽低频感知，20-50Hz微抬保持下盘量感不失衡。",
        "r3": {20: 1, 25: 1, 31.5: 1, 40: 1, 50: 0.5},
        "narrow": {},
        "analysis": "频响：中频厚度平台（250-1.6kHz）叠加在原本平直的底子上，曲线平滑无突兀拐点。失真：全部增益≤1.5dB，对多单元分频网络压力极小。主观：人声更扎实有肉感而不掩蔽高频顺滑度，接近'换暖声前端'的效果。",
    },
    {
        "key": "hd800", "name": "HD800耳机", "device_type": "open_headphone",
        "brand": "Sennheiser", "model": "HD800（300Ω，配耳放）",
        "pain": "声场与解析极致，但低频量感偏少；6kHz附近固有尖峰略刺激。",
        "r1_rationale": "官方THD≤0.02%说明可安全施加低频增益：20-100Hz构建+3~4dB下潜平台矫正量感缺失；6.3kHz窄带收敛固有尖峰、5-8k顺滑处理。",
        "r1": {20: 3, 25: 3.5, 31.5: 4, 40: 4, 50: 3.5, 63: 3, 80: 2.5, 100: 2,
               125: 1.5, 160: 1, 200: 0.5, 5000: -1, 6300: -2.5, 8000: -1.5},
        "r2_rationale": "精细补偿：500-800Hz微抬中频厚度；10-16kHz抬升补开放式单元空气感与声场通透度。",
        "r2": {500: 0.5, 630: 0.5, 800: 0.5, 10000: 1, 12500: 1, 16000: 0.5},
        "r3_rationale": "桌面HiFi安静场景：40-50Hz回撤0.5dB防'轰'；2k/3.15k微抬维持人声存在感与密度。",
        "r3": {40: -0.5, 50: -0.5, 2000: 0.5, 3150: 0.5},
        "narrow": {6300: 4.32},
        "analysis": "频响：低频平台+声压平缓滚降至中频，矫正HD800标志性'低频量感少'；6.3kHz窄带(-2.5dB, Q4.32)精准收敛尖峰而不损伤5-8k整体通透。失真：低频段提升后仍远低于其0.02% THD余量（需耳放充分驱动300Ω）。主观：低频量感与氛围明显补齐，声场依旧开阔且更耐听。",
    },
    {
        "key": "micra_k13", "name": "Micra K13车载音响", "device_type": "car_audio",
        "brand": "Nissan", "model": "Micra K13 原厂4扬声器（基础版）",
        "pain": "用户评价低：整体'不怎么样'、浑浊、功率不足。",
        "r1_rationale": "门板全频小扬声器中低频糊、高频衰减——160-500Hz大幅收敛浑浊源，2-12.5kHz全面抬升清晰度与细节（功率不足用感知补偿对冲）。",
        "r1": {160: -2, 200: -2.5, 250: -2.5, 315: -2, 400: -1.5, 500: -1,
               2000: 1, 2500: 1.5, 3150: 2, 4000: 2, 5000: 1.5, 6300: 1.5,
               8000: 1.5, 10000: 1, 12500: 0.5},
        "r2_rationale": "精细补偿：100-160Hz门板共振区再收敛，40Hz微抬下潜（小口径门板单元极限内），1k密度补偿。",
        "r2": {40: 1, 80: -1, 100: -1.5, 125: -1, 160: -0.5, 1000: 0.5},
        "r3_rationale": "市区车载场景：630Hz微抬改善门板扬声器中频凹陷；2k/2.5k/1.25k微抬对抗市区噪声下人声清晰度衰减。",
        "r3": {630: 0.5, 800: 0.5, 1250: 0.5, 2000: 0.5, 2500: 0.5},
        "narrow": {},
        "analysis": "频响：中低频-2~3dB清理门板腔体驻波，高频+1.5~2dB补偿全频单元高频滚降，整体从'浑'转'清'。失真：负增益段降低功放与单元负担，缓解'功率不足'的破音风险；高频段抬升注意原车机音量上限。主观：人声与高频细节显著可闻，后排受高频指向性限制改善有限。",
    },
    {
        "key": "scale_pro", "name": "BGVP Scale Pro", "device_type": "iem_hybrid",
        "brand": "BGVP", "model": "Scale Pro（1DD+1BA，17Ω/113dB）",
        "pain": "调音成熟耐听；低频凝聚但下潜不深；人声距离适中、厚度稍薄，易被低频掩盖。",
        "r1_rationale": "低阻抗高灵敏度好推——20-63Hz直接构建+2~2.5dB下潜平台，补齐'下潜不深'。",
        "r1": {20: 2, 25: 2.5, 31.5: 2.5, 40: 2.5, 50: 2, 63: 1.5},
        "r2_rationale": "精细补偿：315-800Hz人声厚度增益，矫正'厚度稍薄'；160Hz微收防止新增低频掩盖人声。",
        "r2": {160: -0.5, 315: 1, 400: 1, 500: 1, 630: 1, 800: 0.5},
        "r3_rationale": "日常杂食场景：6.3-16kHz空气感微抬保持'明亮不刺'的顺滑特质。",
        "r3": {6300: 0.5, 10000: 0.5, 12500: 0.5, 16000: 0.5},
        "narrow": {},
        "analysis": "频响：下潜平台与人声厚度区之间在160Hz做了防掩蔽缓冲，曲线连续无对冲。失真：增益温和（≤2.5dB），17Ω/113dB灵敏度下前端轻松驱动不失真。主观：低频'沉得下去'、人声更有厚度，同时保持其招牌的顺滑耐听。",
    },
    {
        "key": "s25plus", "name": "Samsung S25 Plus手机扬声器", "device_type": "phone_speaker",
        "brand": "Samsung", "model": "Galaxy S25+（AKG调校立体声扬声器）",
        "pain": "用户反馈声音'空洞'、低音不佳、音质不如前代。",
        "r1_rationale": "'空洞'=中低频(125-630Hz)量感缺失——手机扬声器150Hz以下物理无输出不强推；125-800Hz构建丰满度平台，直接填'洞'。",
        "r1": {125: 2, 160: 2.5, 200: 3, 250: 3, 315: 2.5, 400: 2, 500: 1.5,
               630: 1, 800: 0.5},
        "r2_rationale": "精细补偿：2-4kHz人声可懂度与高频质感，6.3-10kHz微抬改善'不如前代'的暗淡感。",
        "r2": {2000: 1, 2500: 1.5, 3150: 1.5, 4000: 1, 6300: 0.5, 8000: 0.5,
               10000: 0.5},
        "r3_rationale": "手持近场+Dolby Atmos场景：200/250Hz回撤0.5dB防近场过肥与单元失真；1.6k微抬对话清晰度。单段增益≤3dB守住手机扬声器失真红线。",
        "r3": {200: -0.5, 250: -0.5, 1600: 0.5},
        "narrow": {},
        "analysis": "频响：中低频丰满度平台直接矫正'空洞'观感，高频微抬恢复AKG调校的明亮质感。失真控制：所有增益≤2.5dB（末轮后最大3dB→净2.5dB），低于手机扬声器AGC限幅触发阈值附近的安全线，配合负preamp保证不破音。主观：听感从'薄而空'转为'饱满清晰'；外放仍受物理限制，低频改善集中在可闻频段。",
    },
    {
        "key": "oppo_a5", "name": "OPPO A5 4G手机扬声器", "device_type": "phone_speaker",
        "brand": "OPPO", "model": "A5 4G（立体声双扬声器，Dolby Atmos）",
        "pain": "该价位罕见的优秀立体声外放，'顶部与底部一样饱满'；仅需轻度精修，部分应用单边出声（系统问题非EQ范畴）。",
        "r1_rationale": "外放已接近满血，仅做最小干预：250-400Hz轻微收敛箱染，3.15/4k微抬清晰度。",
        "r1": {250: -0.5, 315: -0.5, 400: -0.5, 3150: 0.5, 4000: 0.5},
        "r2_rationale": "精细补偿：2-2.5k微抬乐器亮度与细节，保留其'准旗舰'饱满底子。",
        "r2": {2000: 0.5, 2500: 0.5},
        "r3_rationale": "影音/通话场景：800Hz-1.6k人声对话可懂度微抬（针对Zoom等应用的语音内容）。",
        "r3": {800: 0.5, 1000: 0.5, 1600: 0.5},
        "narrow": {},
        "analysis": "频响：±0.5dB级别的'精修'曲线，干预幅度刻意保持最小以保留原厂调音。失真：增益极小，几乎不增加单元负担。主观：人声台词更突出一点，整体仍是'越级'外放水准；应用单边出声属软件问题需检查声道设置。",
    },
    {
        "key": "hitune_t8", "name": "Ugreen Hitune T8降噪耳机", "device_type": "bluetooth_headphone",
        "brand": "Ugreen", "model": "Hitune T8（-55dB ANC，LDAC，12.4mm镀钛单元）",
        "pain": "降噪与续航强、人声干净；复杂环境蓝牙连接缩水；ANC下低频感知被削。",
        "r1_rationale": "TWS+ANC通病：125-200Hz低频过肥、6.3-16kHz编解码与ANC高频损失——收敛低频肥感，抬升高频延伸还原LDAC潜力。",
        "r1": {125: -1, 160: -1.5, 200: -1.5, 6300: 1, 8000: 1.5, 10000: 1.5,
               12500: 1, 16000: 0.5},
        "r2_rationale": "精细补偿（人声核心）：1.6-3.15k人声可懂度平台+1~1.5dB，500-630Hz微抬温暖度，巩固'人声干净'优势。",
        "r2": {500: 0.5, 630: 0.5, 1600: 1, 2000: 1.5, 2500: 1.5, 3150: 1},
        "r3_rationale": "地铁通勤降噪场景：-55dB ANC下耳压与低频感知被削，20-63Hz微抬维持节奏感；ANC已隔离噪声故不需大幅补偿。",
        "r3": {20: 1, 25: 1, 31.5: 1, 40: 1, 50: 0.5, 63: 0.5},
        "narrow": {},
        "analysis": "频响：收敛TWS肥低频+高频延伸+人声前移，形成干净的'通勤人声'曲线。失真：LDAC高码率下+1.5dB级增益无 audible 失真风险；preamp余量防止-55dB ANC大音量下的削波。主观：地铁中人声与乐器分离度进一步拉开，节奏感在ANC下不塌；连接缩水属射频问题，建议手机放右侧裤袋/避开干扰。",
    },
    {
        "key": "xtrail_std", "name": "Nissan X-Trail车载音响", "device_type": "car_audio",
        "brand": "Nissan", "model": "X-Trail 标准版6扬声器",
        "pain": "标准版被评测形容为'浑浊的六扬声器声音系统'；Bose选装版才有'轮廓清晰'。",
        "r1_rationale": "'浑浊'=160-630Hz泥泞区——大幅收敛（对标Bose版'轮廓清晰'的频响倾向）；2-12.5kHz全面抬升细节与轮廓感。",
        "r1": {160: -2.5, 200: -3, 250: -3, 315: -2.5, 400: -2, 500: -1.5, 630: -1,
               2500: 1.5, 3150: 2, 4000: 2, 5000: 1.5, 6300: 1.5, 8000: 1.5,
               10000: 1},
        "r2_rationale": "精细补偿：63-100Hz路噪竞争区微抬低频存在感，1.25k人声密度。",
        "r2": {63: 1, 80: 1, 100: 0.5, 1250: 0.5},
        "r3_rationale": "嘈杂高速场景：路噪/风噪掩蔽中频与高频感知，1k/1.25k再抬人声可懂度；31.5/40Hz微收防座舱低频增益+新增低频叠加产生轰鸣，12.5k微抬空气感。",
        "r3": {1000: 1, 1250: 0.5, 31.5: -0.5, 40: -0.5, 12500: 0.5},
        "narrow": {},
        "analysis": "频响：中低频-1.5~-3dB清理六扬声器浑浊，高频+1.5~2dB重建'轮廓'，末轮防低频叠加轰鸣。失真：净负增益于中低频降低功放压力；高频抬升段建议原车机音量-2格使用。主观：从'糊成一团'到人声/乐器轮廓可辨，接近'选装Bose'的清晰度方向；极限低频改善受原车扬声器物理限制。",
    },
    {
        "key": "mdr1abt", "name": "Sony MDR-1ABT", "device_type": "bluetooth_headphone",
        "brand": "Sony", "model": "MDR-1ABT（40mm镀铝LCP振膜，24Ω/98dB，LDAC+Hi-Res）",
        "pain": "万金油均衡调音，'低频干净利落、中频中正、高频控制不出齿音'；用户痛点：'Recessed vocals'（What Hi-Fi）、'Lack get-up-and-go'（人声靠后、声音不抓人）、户外全包裹隔音太好不安全（设计权衡）。",
        "r1_rationale": "基础素质好且为'万金油'调音——最小幅度保持：20-50Hz低架 +1dB 保下潜，10-16kHz +0.5dB 释放 LDAC/DSEE 恢复的高频延伸。",
        "r1": {20: 1, 25: 1, 31.5: 1, 40: 1, 50: 0.5, 10000: 0.5, 12500: 0.5, 16000: 0.5},
        "r2_rationale": "补偿 'Recessed vocals'：1-2kHz 人声核心区 +1.5dB 把人声推前；4-6.3kHz 0.5dB 提乐器存在感但不引入齿音。",
        "r2": {1000: 1.5, 1250: 1, 1600: 1, 2000: 1, 4000: 0.5, 5000: 0.5, 6300: 0.5},
        "r3_rationale": "BT（LDAC）+ 日常场景：125-200Hz 收敛 -0.5dB 轻微抑制大单元小腔体下潜在肥感；3.15kHz +0.5dB 拉近人声距离感。",
        "r3": {125: -0.5, 160: -0.5, 200: -0.5, 3150: 0.5},
        "narrow": {},
        "analysis": "频响：在'万金油'底子上微抬 1-2kHz 人声核心区拉回 'Recessed'，0.5-2dB 内整体保持原厂调音。失真：所有增益 ≤1.5dB，远低于 24Ω/98dB 单元裕量，BT-LDAC 高码率无失真。主观：人声从'靠后'移至'居中前位'，低频弹性与高频延伸保持原样；户外全包裹安全属佩戴习惯问题。",
    },
    {
        "key": "qc45", "name": "Bose QC 45", "device_type": "bluetooth_headphone",
        "brand": "Bose", "model": "QuietComfort 45（ANC + Aware，BT5.1，240g）",
        "pain": "降噪与舒适度顶级，'动态音质均衡'算法；用户痛点：'Veiled'（高频被滚降遮蔽）、'Muddy bass' ANC 关时、'Lack detail' vs HiFi 玩家、声场偏窄。",
        "r1_rationale": "Bose 经典 'Consumer Target' 调音：低频微微抬（特别 sub-bass）、中高频清晰但略收、>10kHz 滚降——先收 30-50Hz 过量 sub-bass（-1dB），轻度补 6.3-10kHz 还原细节。",
        "r1": {25: -1, 31.5: -1, 40: -1, 50: -0.5, 6300: 0.5, 8000: 0.5, 10000: 0.5},
        "r2_rationale": "补偿 'Veiled'：2-3.15kHz 人声可懂度区 +1.5dB（ANC 模式下被环境噪声掩蔽的频段优先）；5-8kHz 进一步抬 +1dB 补细节。",
        "r2": {2000: 1, 2500: 1.5, 3150: 1, 5000: 1, 6300: 0.5, 8000: 0.5},
        "r3_rationale": "ANC ON 通勤场景：200-400Hz 收敛 -0.5dB 抑制 ANC 耳压引发的低频隆起（被动密封叠加效应）；12.5-20kHz 轻补空气感。",
        "r3": {200: -0.5, 250: -0.5, 315: -0.5, 400: -0.5, 12500: 0.5, 16000: 0.5, 20000: 0.5},
        "narrow": {},
        "analysis": "频响：在 Bose 商业目标曲线上做最小偏离，sub-bass 微收 + 中高频微补，'veiled' 感改善，声场仍偏窄（物理封闭式 + ANC 设计权衡）。失真：所有增益 ≤1.5dB，远低于 24-bit 动态 EQ 余量，BT5.1 链路无损。主观：人声从'雾里看花'变'清晰可辨'，细节与空气感补回；声场与降噪等级属硬件能力。",
    },
    {
        "key": "samsung_htf5500w", "name": "三星HT-F5500W家庭影院", "device_type": "home_theater",
        "brand": "Samsung", "model": "HT-F5500W（5.1 HTiB，无源6寸炮，SWA-6000无线环绕）",
        "pain": "5.1 家庭影院一体机（2013款HTiB）。用户反馈（Amazon 4.1/5）：声音干净、响度大、环绕定位真实；痛点：对白/人声易被背景音效淹没（最高频槽点）、无源低音炮缺深度与冲击力、环绕箱无独立高音后场偏暗、听音乐'够好但不优秀'。",
        "r1_rationale": "用户反馈驱动：160-400Hz 中低频染声是对白掩蔽的直接来源——收敛该区释放人声；2-3.15kHz 对白可懂度平台抬升；80-100Hz 温和补无源炮量感（40-50Hz 滚降段不强推）；8-12.5kHz 补 ¾\" 高音空气感。",
        "r1": {50: 1, 63: 1.5, 80: 1.5, 100: 1.5, 125: 1, 160: -1, 200: -1.5, 250: -1.5,
               315: -1, 400: -0.5, 2000: 1, 2500: 1.5, 3150: 1.5, 8000: 1, 10000: 1, 12500: 0.5},
        "r2_rationale": "精细补偿：500-800Hz 微抬人声 body 防中频发薄；6.3kHz 微抬衔接前/后场亮度差（环绕箱无高音）。",
        "r2": {500: 0.5, 630: 0.5, 800: 0.5, 6300: 0.5},
        "r3_rationale": "小房间客厅影院场景：200/250Hz 再收 0.5dB 防小房间边界增益叠加轰鸣；2.5kHz 再微抬对白存在感（夜间低音量观看可懂度）。",
        "r3": {200: -0.5, 250: -0.5, 2500: 0.5},
        "narrow": {},
        "analysis": "频响：中低频 -2dB 级收敛解除对白掩蔽，2-3.15kHz +1.5~2dB 对白平台，低频 60-100Hz 温和补量，形成'对白优先'的家庭影院曲线。失真：中低频负增益降低无源炮与卫星箱冲程；低频增益止于 100Hz 以上，避开无源 6 寸炮 40-50Hz 滚降区防打底。主观：对白从配乐中浮出、口型清晰；低频量感补足但冲击力受无源炮物理限制；环绕后场偏暗与无线断连属硬件范畴，EQ 不处理。",
    },
]


def _fmt_delta(d: dict) -> str:
    items = sorted(d.items())
    return ", ".join(f"{_fmt_freq(f)}Hz{'+' if g >= 0 else ''}{g:g}" for f, g in items)


def _fmt_freq(f: float) -> str:
    return f"{f:g}"


def build_bands(dev: dict) -> list:
    gains = {f: 0.0 for f in FREQS}
    for rnd in ("r1", "r2", "r3"):
        for f, g in dev[rnd].items():
            assert f in gains, f"{dev['name']}: {f}Hz 不在31段频栅上"
            gains[f] = round(gains[f] + g, 1)
    bands = []
    for f in FREQS:
        g = gains[f]
        assert -10 <= g <= 10, f"{dev['name']}: {f}Hz 增益 {g} 超限"
        bands.append({
            "type": TYPE_PEAK,
            "frequency": int(f),
            "q": dev.get("narrow", {}).get(f, DEFAULT_Q),
            "gain": g,
        })
    return bands


def main() -> int:
    ensure_dir(PROFILE_DIR)
    ensure_dir(EXPORT_DIR)
    # 启动时一次校验：v1 DEVICES 设备名必须与 peq_common.DEVICE_REGISTRY 一致
    missing, extra = validate_device_coverage([d["name"] for d in DEVICES])
    if missing or extra:
        raise AssertionError(
            f"v1 DEVICES 清单与 DEVICE_REGISTRY 不一致: missing={missing}, extra={extra}"
        )
    now = now_iso()
    report = [
        "# 十三款音频设备 Poweramp 31 段 PEQ 设计报告",
        "",
        f"生成时间：{now}　|　计算引擎：poweramp-peq-tuner（确定性计算，preamp 自动补偿）",
        "",
        "**统一约定**：31 段 = 1/3 倍频程频栅（20Hz-20kHz ISO 中心频率）；滤波器全部为峰值（PK），"
        f"默认 Q={DEFAULT_Q}（1/3 倍频程本征 Q：各段近似独立，单段增益即该频点实际修正量，所见即所得；"
        "例外单独注明）；preamp 由引擎按合成响应自动计算防削波。",
        "",
        "---",
    ]

    for idx, dev in enumerate(DEVICES, 1):
        bands = build_bands(dev)
        preamp = compute_preamp(bands)
        preset = {
            "name": f"{dev['name']} - 31段定制",
            "preamp": preamp,
            "parametric": True,
            "bands": bands,
        }
        warnings = validate_preset(preset)
        preset["warnings"] = warnings

        # 设备档案（locked：直接使用已计算 preset）
        profile = {
            "name": dev["name"],
            "device_type": dev["device_type"],
            "brand": dev["brand"],
            "model": dev["model"],
            "preference": "custom31",
            "intensity": 1.0,
            "custom_bands": [
                f"PK {b['frequency']} {b['gain']:g} {b['q']:g}" for b in bands
            ],
            "locked": True,
            "note": f"31段三轮迭代定制方案（{dev['pain'][:40]}…）",
            "active": False,
            "created_at": now,
            "updated_at": now,
            "rounds": {"r1": dev["r1"], "r2": dev["r2"], "r3": dev["r3"]},
            "rationale": {"r1": dev["r1_rationale"], "r2": dev["r2_rationale"],
                          "r3": dev["r3_rationale"]},
            "preset": preset,
        }
        # 设备名交叉验证（确保 13 设备名与 peq_common.DEVICE_REGISTRY 一致）
        # 已移到 main() 启动时一次性校验

        write_json(PROFILE_DIR / f"{dev['name']}.json", profile)

        # 导出双格式
        write_text(EXPORT_DIR / f"{dev['name']}-Poweramp.txt", render_poweramp_txt(preset))
        # render_equalizer_json() 返回预序列化字符串（含 \n 转义），用 write_text 写
        write_text(EXPORT_DIR / f"{dev['name']}-PowerampEQ.json", render_equalizer_json(preset))

        # 报告段落
        narrow_note = (
            f"；例外：{', '.join(f'{_fmt_freq(f)}Hz Q={q}' for f, q in dev.get('narrow', {}).items())}"
            if dev.get("narrow") else ""
        )
        report += [
            f"## {idx}. {dev['name']}（{dev['brand']} {dev['model']}）",
            "",
            f"**设备特性与痛点**：{dev['pain']}",
            "",
            f"**首轮（R1）初始修正**：{dev['r1_rationale']}",
            f"  - 调整：{_fmt_delta(dev['r1'])}",
            "",
            f"**次轮（R2）精细补偿**：{dev['r2_rationale']}",
            f"  - 调整：{_fmt_delta(dev['r2'])}",
            "",
            f"**末轮（R3）场景验证微调**：{dev['r3_rationale']}",
            f"  - 调整：{_fmt_delta(dev['r3'])}",
            "",
            f"**效果分析**：{dev['analysis']}",
            "",
            f"**最终参数**：preamp `{preamp:+.1f} dB`，31 段 PK，"
            f"Q 默认 {DEFAULT_Q}{narrow_note}",
            "",
            "| # | 频率 Hz | 增益 dB | Q |",
            "|---|---|---|---|",
        ]
        report += [
            f"| {i} | {b['frequency']} | {b['gain']:+.1f} | {b['q']:g} |"
            for i, b in enumerate(bands, 1)
        ]
        report += [
            "",
            f"**导出文件**：`exports/31band/{dev['name']}-Poweramp.txt`、"
            f"`exports/31band/{dev['name']}-PowerampEQ.json`；档案：`peq-profiles/{dev['name']}.json`",
            "",
        ]
        if warnings:
            report += [f"**校验提示**：{'；'.join(warnings)}", ""]
        report += ["---", ""]

    REPORT.write_text("\n".join(report), encoding="utf-8", newline="\n")
    print(f"完成：{len(DEVICES)} 个设备 -> {EXPORT_DIR} / {PROFILE_DIR} / {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
