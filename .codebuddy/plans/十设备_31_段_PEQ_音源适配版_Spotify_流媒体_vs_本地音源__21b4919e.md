---
name: 十设备 31 段 PEQ 音源适配版（Spotify 流媒体 vs 本地音源）
overview: 以现有 v3 31 段配置为基准，按 Spotify 流媒体（有损编解码/响度归一化特性）与本地音源（无损/高码率特性）两种音源分别派生 10 台设备的 31 段 PEQ 变体：确定性脚本生成 20 个新档案与 40 个可导入预设文件，并输出含调整目标、逐频段增益/Q 修改建议、听感差异说明与调优优先级顺序的完整报告。
todos:
  - id: build-v4-script
    content: 遵循 [skill:poweramp-peq-tuner] 引擎规范，编写 design_v4.py：加载 v3 档案、应用流媒体/本地双音源规则、重算 preamp 并校验
    status: completed
  - id: generate-variants
    content: 运行脚本生成 20 个 v4 locked 档案与 40 个预设文件至 exports/v4/流媒体 与 exports/v4/本地音源
    status: completed
    dependencies:
      - build-v4-script
  - id: write-report
    content: 编写 PEQ优化方案v4-音源适配.md：每设备每音源的调整目标、逐频段修改表、听感差异说明与调优优先级顺序
    status: completed
    dependencies:
      - generate-variants
  - id: verify-present
    content: 抽查 .txt/.json 格式合规性与 CLI 档案列表，输出汇总与可执行调优优先级
    status: completed
    dependencies:
      - write-report
---

## 需求概述
在现有十款设备的 v3 31 段 PEQ 配置基础上，针对 **Spotify 在线流媒体** 与 **本地下载音乐** 两种音源特性，进行精细化优化与升级调校。

## 核心交付内容
- **双音源变体**：每台设备派生两套 31 段配置（流媒体版 / 本地音源版），共 20 个设备档案 + 40 个可导入预设文件（.txt + .json 双格式，兼容 Poweramp 主应用与 Poweramp Equalizer）
- **每设备每音源需列出**：
  1. PEQ 调整目标（结合音源编码特性与设备声学痛点）
  2. 频段增益与 Q 值修改建议（相对 v3 基准的逐频段变化）
  3. 优化前后的听感差异说明
- **可执行的调优优先级顺序**（分设备类别、按步骤可操作）

## 设计依据（音源声学特性）
- **Spotify（Ogg Vorbis 320/160kbps 有损）**：≥16kHz 内容被心理声学模型剔除，正增益只会放大编码伪影；10–12.5kHz 镲片/齿音区伪影需收敛；响度归一化压缩动态 → 深潜段（20–31.5Hz）增益收敛约 30%
- **本地音源（假设无损/≥320kbps）**：全频段真实内容完整；高频延伸能力真实存在的耳机类设备 12.5–20kHz 可 +0.5dB 发挥音源优势；物理受限设备（手机扬声器/便携音箱/车载原厂）高频维持 v3 不变

## 假设（默认采用）
1. Spotify = Premium 320kbps（免费档 160kbps 在报告附注给出更保守建议）
2. 本地 = 无损或 ≥320kbps（低码率有损则套用流媒体变体）
3. v4 变体与 v1/v2/v3 档案并存不覆盖；Q 值统一维持 4.32（1/3 倍频程本征 Q）不变，仅调增益


## 技术栈
- Python 3 标准库（无第三方依赖，Windows/PowerShell 零安装可用）
- 复用 `poweramp-peq-tuner` 技能引擎：`peq_engine.py`（compute_preamp / validate_preset / render_poweramp_txt / render_equalizer_json）
- 数据格式：设备档案 JSON（locked 定制方案 schema）、预设 .txt（REW/APO）与 .json（Equalizer）

## 实现方案
新建确定性驱动脚本 `design_v4.py`，从 `peq-profiles/*v3.json` 读取 31 段基准配置，按音源规则逐频段计算 delta：

- **流媒体规则**：gain(f≥16000) 的正增益归零（负增益保留）；10000≤f<16000 正增益 -0.5dB；20–31.5Hz 正增益 ×0.7
- **本地规则**：高频延伸型设备（iem_dynamic / iem_hybrid / open_headphone / bluetooth_headphone）12500–20000Hz 正增益 +0.5dB；物理受限设备（phone_speaker / portable_speaker / car_audio）不变
- 每套变体经 `compute_preamp` 重算 preamp（防削波）与 `validate_preset` 声学校验后落盘导出

关键决策：
1. **派生而非重设计**——v3 已含三轮迭代的声学依据，音源适配是确定性规则变换，保证可追溯（每频段变化可解释为音源特性）
2. **Q 不变、只调增益**——31 段网格 Q=4.32 为"所见即所得"本征值，音源适配不改变滤波器形状，仅改变修正量
3. **听感差异说明手写绑定**——报告文本按设备特性（延伸能力/伪影敏感度/物理边界）与实际 delta 逐台撰写，非模板套话

## 目录结构
```
c:/Users/izual/Desktop/Poweramp/
├── design_v4.py                        # [NEW] 音源适配驱动脚本：加载 v3 → 应用双音源规则 → 重算 preamp/校验 → 落盘导出
├── peq-profiles/
│   ├── <设备名>v4流媒体.json            # [NEW] x10 locked 档案（含 preset、调整目标、变更依据）
│   └── <设备名>v4本地音源.json          # [NEW] x10
├── exports/
│   ├── v4/流媒体/                       # [NEW] 10 组 .txt + .json 预设
│   └── v4/本地音源/                     # [NEW] 10 组 .txt + .json 预设
├── PEQ优化方案v4-音源适配.md            # [NEW] 完整报告：调整目标/逐频段修改表/听感差异/调优优先级顺序
└── PEQ优化方案v3-31段精细化.md          # [既有] 基准参照，不修改
```

## 实施要点
- 档案命名含中文（如 `HD800耳机v4流媒体.json`），`peq_cli.py` 的 locked 档案导出路径已验证可用
- 修改建议表仅列有变化频段（流媒体版集中在 16–20k/10–12.5k/20–31.5Hz；本地版集中在 12.5–20kHz），无变化段注明"维持 v3"
- 报告附注：Spotify 免费档（160kbps）更保守建议、本地低码率降级使用流媒体变体的判定规则
- 校验：增益 ±10dB 硬上限、preamp 重算后无削波错误；v4 与既有档案并存，`set-active` 按当前音源切换


## Agent Extensions
### Skill
- **poweramp-peq-tuner**
  - Purpose: 提供 PEQ 计算引擎（preamp 自动补偿、声学校验、双格式渲染）、档案管理 CLI 与格式规范，v4 脚本直接复用其 `peq_engine.py` 全部函数与 locked 档案机制
  - Expected outcome: 20 个 v4 档案与 40 个预设文件通过官方兼容格式校验，可被 Poweramp / Poweramp Equalizer 识别导入，且可用 `peq_cli.py` 统一管理切换
