# PEQ 优化方案 v5 —— 综合调优（PEQ + 分频 + 增益 + 延迟 + 动态处理）

生成时间：2026-10-08T20:12:31　|　基准：v4统一无损 31 段 PEQ　|　声学参考：声学特点.txt　|　计算引擎：poweramp-peq-tuner

## 升级定位

v5 在 v4统一无损 31 段 PEQ 基础上，**新增 4 类综合调优参数**，覆盖完整调优链路：

| 维度 | 新增内容 | 主要适用设备 | Poweramp 是否直接支持 |
|---|---|---|---|
| **均衡 (equalizer)** | 继承 v4统一无损 PEQ（无改动）| 12 设备 | ✓ 直接导入 |
| **分频 (crossover)** | 物理分频点 / 斜率 / 位置 / EQ 补偿 | X-Trail（K13 是 full-range）| ✗ 需外置 DSP |
| **增益 (gain)** | 通道平衡 + 前端输出阻抗建议 + 单元电平匹配 | 12 设备差异化 | △ 部分（前端阻抗为建议）|
| **延迟 (delay)** | 多驱动单元时间对齐 | K13 / X-Trail | ✗ 需外置 DSP |
| **动态 (dynamics)** | 压缩器 (compressor) + 限幅器 (limiter) | IE900 复刻 / XB12 / 车载 | ✗ 需外置 DSP（Poweramp 无动态）|

## v3 → v5 升级总览（12 设备）

| 设备 | EQ | 分频 | 增益新增 | 延迟 | 动态 | 主要升级点 |
|---|---|---|---|---|---|---|
| IE900复刻版 | 继承 v4统一无损 | none | 前端 ≤ 4Ω | none | +limiter | 复刻 THD 3% 保护 |
| BGVP Scale Pro | 继承 v4统一无损 | none | 前端 ≤ 2Ω | none | 无 | 底噪敏感防护 |
| 1圈14铁耳机 | 继承 v4统一无损 | passive_4way | 声道匹配 < 2dB | none | 无 | 分频点相位记录 |
| HD800耳机 | 继承 v4统一无损 | none | 前端 ≤ 10Ω | none | 无 | 110Hz 谐振峰前端建议 |
| Sony MDR-1ABT | 继承 v4统一无损 | none | 前端 ≤ 3Ω | none | 无 | BT 链路记录 |
| Bose QC 45 | 继承 v4统一无损 | none | Bose App EQ 必须关 | none | Bose 自研 | 应用互锁 + 动态 EQ 联动 |
| Ugreen Hitune T8降噪耳机 | 继承 v4统一无损 | none | LDAC 推荐 | none | TWS 内置 | 编解码建议 |
| Sony XB12双音箱组合 | 继承 v4统一无损 | none | 独立音量 | none | +limiter | 小单元保护 |
| Samsung S25 Plus手机扬声器 | 继承 v4统一无损 | none | 系统声道平衡 | none | 手机 DSP | 硬件不可修项记录 |
| OPPO A5 4G手机扬声器 | 继承 v4统一无损 | none | 系统声道平衡 | none | 手机 DSP | 硬件不可修项记录 |
| Micra K13车载音响 | 继承 v4统一无损 | full_range | 原厂无电平匹配 | 后门 +0.5ms | +compressor +limiter | 车载综合升级 |
| Nissan X-Trail车载音响 | 继承 v4统一无损 | passive_2way | 原厂分频器已匹配 | 中低音 +1.5ms / 后门 +0.5ms | +compressor +limiter | 2 路被动分频 + 时间对齐 |

## 通用调优原则

1. **均衡**：v3 已针对每设备单元特性优化；v5 不修改 EQ 本身，继承 v4统一无损 即可
2. **分频**：EQ **不可改变物理分频**；EQ 只能补偿分频点附近的声学问题（如相位干涉、指向性）
3. **增益**：
   - 前端输出阻抗 ≤ 1/8 单元阻抗（低音偏移防抖）
   - 300Ω 大阻单元（HD800）建议 ≤ 10Ω 阻尼（控制 110Hz 谐振峰）
   - 多单元声道匹配 < 2dB 为正常
4. **延迟**：仅多驱动单元需要；单驱动单元 0ms；时间对齐 = (远端距离 - 近端距离) / 343 m/s × 1000
5. **动态**：
   - 压缩器：保护单元免受热压缩失真（单元功率余量小时启用）
   - 限幅器：封顶防单元烧毁（单元最大功率时启用）
   - 已被厂商内置的设备（Bose QC 45 / TWS）不需外部配置
6. **应用互锁**：Bose QC 45 的 Bose Music App EQ 必须关闭（与 Poweramp EQ 串联失真）

---

## 各设备 v5 详细配置

### 1圈14铁耳机（iem_hybrid）

**基准档案**：`1圈14铁耳机v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-2.7 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/1圈14铁耳机v4统一无损.json`

#### 2. 分频

- 类型：**passive_4way**
- EQ 补偿：350Hz / 3000Hz 双分频点相位补偿（v3 PEQ 已含）
- 内部结构：Multitube 多路滤波专利（4 分频 / 4 独立声孔）
- 声学依据：

#### 3. 增益

- preamp：-2.7 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 单元声道匹配：< 2 dB（厂家调校基准）
- 声学依据：多单元声道匹配通常 < 2dB；超出需厂家调校

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用

**导出**：`exports/v5/1圈14铁耳机v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/1圈14铁耳机v5.json`（含分频/增益/延迟/动态）

---

### BGVP Scale Pro（iem_hybrid）

**基准档案**：`BGVP Scale Prov4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-3.5 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/BGVP Scale Prov4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-3.5 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 前端输出阻抗建议：≤ **2 Ω**
- 声学依据：17Ω 极低阻抗 + 113dB 高灵敏；前端输出阻抗 ≤ 2Ω 防频响偏移与底噪放大

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用

**导出**：`exports/v5/BGVP Scale Prov5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/BGVP Scale Prov5.json`（含分频/增益/延迟/动态）

---

### Bose QC 45（bluetooth_headphone）

**基准档案**：`Bose QC 45v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-2.7 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Bose QC 45v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-2.7 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用
- 厂商内置动态：Bose 自研动态音质均衡已含主动保护；外部 EQ 叠加边际收益小
- 应用互锁：Bose Music → must_disable_eq
  - 声学依据：Bose Music App 内置 EQ 必须关闭，避免与 Poweramp EQ 串联失真

**导出**：`exports/v5/Bose QC 45v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Bose QC 45v5.json`（含分频/增益/延迟/动态）

---

### HD800耳机（open_headphone）

**基准档案**：`HD800耳机v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-9.2 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/HD800耳机v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-9.2 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 前端输出阻抗建议：≤ **10 Ω**
- 声学依据：300Ω 标称 + 110Hz 650Ω 谐振峰；建议前端输出阻抗 ≤ 10Ω 提供阻尼

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用

**导出**：`exports/v5/HD800耳机v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/HD800耳机v5.json`（含分频/增益/延迟/动态）

---

### IE900复刻版（iem_dynamic）

**基准档案**：`IE900复刻版v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-3.5 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/IE900复刻版v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-3.5 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 前端输出阻抗建议：≤ **4 Ω**
- 声学依据：32Ω 复刻品；建议前端输出阻抗 ≤ 1/8 阻抗（4Ω），防频响偏移

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：启用
  - ceiling: -3.0 dB / release: 50 ms
  - 声学依据：复刻品 THD 可达 3%（原版 <0.05%），limiter 防失真恶化

**导出**：`exports/v5/IE900复刻版v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/IE900复刻版v5.json`（含分频/增益/延迟/动态）

---

### Micra K13车载音响（car_audio）

**基准档案**：`Micra K13车载音响v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-3.4 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Micra K13车载音响v4统一无损.json`

#### 2. 分频

- 类型：**full_range_no_xover**
- 声学依据：4 全频扬声器无独立高音单元；分频 = 无（被动物理结构）

#### 3. 增益

- preamp：-3.4 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 按驱动单元：{'rear_left': 0.5, 'rear_right': 0.5}
- 声学依据：后门全频单元到驾驶位约多 0.17m（343m/s = 0.5ms）；无 DSP 不可实现
- 备注：无

#### 5. 动态

- 压缩器：启用
  - threshold: -6.0 dB / ratio: 3.0 / attack: 30 ms / release: 250 ms
  - 声学依据：无外置功放；4Ω/90-93dB 单元功率余量小；压缩保护免受热压缩失真
- 限幅器：启用
  - ceiling: -0.5 dB / release: 80 ms
  - 声学依据：原厂 4 全频单元功率小；limiter 防单元损坏
- **DSP 备注**：无外置 DSP 功放不可实现本配置；外置 DSP（如 Helix DSP Mini）参考方案

**导出**：`exports/v5/Micra K13车载音响v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Micra K13车载音响v5.json`（含分频/增益/延迟/动态）

---

### Nissan X-Trail车载音响（car_audio）

**基准档案**：`Nissan X-Trail车载音响v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-2.7 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Nissan X-Trail车载音响v4统一无损.json`

#### 2. 分频

- 类型：**passive_2way**
- 分频点：{'mid_low_pass': 3000, 'tweeter_high_pass': 3000}
- 斜率：[12, 12] dB/oct
- 物理位置：{'tweeter': '仪表台顶部', 'mid_woofer': '前门下部'}
- 路径差：0.5 m（高音 vs 中低音）
- EQ 补偿：3kHz +1.5dB 补分频点相位干涉；8kHz +1.5dB 补高音指向性
- 声学依据：

#### 3. 增益

- preamp：-2.7 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 按驱动单元：{'tweeter_dash': 0, 'mid_door': 1.5, 'rear_full': 0.5}
- 声学依据：车门中低音比仪表台高音远约 0.5m → 1.5ms 延迟；后门到驾驶位 0.5ms
- 备注：无

#### 5. 动态

- 压缩器：启用
  - threshold: -10.0 dB / ratio: 4.0 / attack: 20 ms / release: 200 ms
  - 声学依据：20W 额定功率动态余量小；压缩保护免受热压缩失真
- 限幅器：启用
  - ceiling: -1.0 dB / release: 50 ms
  - 声学依据：40W 最大功率封顶；limiter 防单元烧毁
- **DSP 备注**：无外置 DSP 功放不可实现本配置；外置 DSP（如 Helix DSP Mini）参考方案

**导出**：`exports/v5/Nissan X-Trail车载音响v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Nissan X-Trail车载音响v5.json`（含分频/增益/延迟/动态）

---

### OPPO A5 4G手机扬声器（phone_speaker）

**基准档案**：`OPPO A5 4G手机扬声器v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-1.2 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/OPPO A5 4G手机扬声器v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-1.2 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 通道平衡需通过：Android 系统 Dolby Atmos 声道平衡
- 声学依据：底部扬声器音量显著大于顶部；系统设置可改善
- 硬件不可修项（EQ 不可改善）：
  - 左右声道音量差（顶部偏小）
  - 超薄机身物理频响边界

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用

**导出**：`exports/v5/OPPO A5 4G手机扬声器v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/OPPO A5 4G手机扬声器v5.json`（含分频/增益/延迟/动态）

---

### Samsung S25 Plus手机扬声器（phone_speaker）

**基准档案**：`Samsung S25 Plus手机扬声器v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-6.3 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Samsung S25 Plus手机扬声器v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-6.3 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 通道平衡需通过：Android 系统 Dolby Atmos 声道平衡
- 声学依据：顶部扬声器声压级低于底部；声像偏下需系统设置（全局 EQ 不可修）
- 硬件不可修项（EQ 不可改善）：
  - 低频 -3dB 截止 > 100Hz（超薄机身限制）
  - 2-16kHz 线性度偏差 15-17%（单元物理缺陷）

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用

**导出**：`exports/v5/Samsung S25 Plus手机扬声器v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Samsung S25 Plus手机扬声器v5.json`（含分频/增益/延迟/动态）

---

### Sony MDR-1ABT（bluetooth_headphone）

**基准档案**：`Sony MDR-1ABTv4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-3.0 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Sony MDR-1ABTv4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-3.0 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 前端输出阻抗建议：≤ **3 Ω**
- 声学依据：24Ω 标称；建议前端输出阻抗 ≤ 1/8 阻抗（3Ω）

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用

**导出**：`exports/v5/Sony MDR-1ABTv5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Sony MDR-1ABTv5.json`（含分频/增益/延迟/动态）

---

### Sony XB12双音箱组合（portable_speaker）

**基准档案**：`Sony XB12双音箱组合v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-2.4 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Sony XB12双音箱组合v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-2.4 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB
- 双音箱配置：manual_independent
- 声学依据：双音箱组合需独立控制每只音量（电平匹配）；蓝牙声道已自动映射

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：启用
  - ceiling: -3.0 dB / release: 100 ms
  - 声学依据：5-6W 小单元；limiter 防振膜过度位移

**导出**：`exports/v5/Sony XB12双音箱组合v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Sony XB12双音箱组合v5.json`（含分频/增益/延迟/动态）

---

### Ugreen Hitune T8降噪耳机（bluetooth_headphone）

**基准档案**：`Ugreen Hitune T8降噪耳机v4统一无损`（31 段 PEQ + Hi-Res boost 视设备）

#### 1. 均衡（继承 v4统一无损）

- preamp: **-2.7 dB**
- 31 段 parametric bands（Q=4.32，1/3 倍频程 ISO 频栅）
- 详见 base 档案：`peq-profiles/Ugreen Hitune T8降噪耳机v4统一无损.json`

#### 2. 分频

- 类型：**none**
- 声学依据：单驱动单元或单元内部分频已完成

#### 3. 增益

- preamp：-2.7 dB（与均衡共享）
- 通道平衡：左 +0.0 dB / 右 +0.0 dB

#### 4. 延迟

- 左/右：0 ms / 0 ms
- 备注：单驱动或单元内对齐已完成

#### 5. 动态

- 压缩器：未启用
- 限幅器：未启用
- 厂商内置动态：TWS 内部已有动态处理；外部叠加无增益
- 编解码推荐：LDAC 990kbps（备选 aptX HD 576kbps）
  - 声学依据：LDAC 模式最大化 Hi-Res 优势；aptX HD 仅 48k/24bit

**导出**：`exports/v5/Ugreen Hitune T8降噪耳机v5-Poweramp.txt` / `-PowerampEQ.json`（仅均衡部分）
**完整配置**：`peq-profiles/Ugreen Hitune T8降噪耳机v5.json`（含分频/增益/延迟/动态）

---

## 跨设备新参数启用统计

| 设备 | 均衡 | 分频 | 增益新增 | 延迟 | 动态 |
|---|---|---|---|---|---|
| IE900复刻版 | 继承 v4统一无损 | — | 前端输出阻抗 | — | — |
| BGVP Scale Pro | 继承 v4统一无损 | — | 前端输出阻抗 | — | — |
| 1圈14铁耳机 | 继承 v4统一无损 | non-trivial | 声道匹配 | — | — |
| HD800耳机 | 继承 v4统一无损 | — | 前端输出阻抗 | — | — |
| Sony MDR-1ABT | 继承 v4统一无损 | — | 前端输出阻抗 | — | — |
| Bose QC 45 | 继承 v4统一无损 | — | 应用互锁 | — | Bose 内置 |
| Ugreen Hitune T8降噪耳机 | 继承 v4统一无损 | — | 编解码 | — | TWS 内置 |
| Sony XB12双音箱组合 | 继承 v4统一无损 | — | 双音箱 | — | — |
| Samsung S25 Plus手机扬声器 | 继承 v4统一无损 | — | 系统声道平衡 / 硬件不可修项 | — | — |
| OPPO A5 4G手机扬声器 | 继承 v4统一无损 | — | 系统声道平衡 / 硬件不可修项 | — | — |
| Micra K13车载音响 | 继承 v4统一无损 | non-trivial | — | ✓ | — |
| Nissan X-Trail车载音响 | 继承 v4统一无损 | non-trivial | — | ✓ | — |

## 实施步骤

### 场景 A：仅 Poweramp 导入（最常用）

1. 从 `exports/v5/<设备名>v5-Poweramp.txt` 或 `.json` 导入 Poweramp Equalizer
2. `equalizer` 部分的 31 段 PEQ + preamp 完整保留 v4统一无损 调音
3. `分频 / 延迟 / 动态` 参数作为后续硬件升级（外置 DSP）参考

### 场景 B：Poweramp + 外置 DSP（车载 / 高级玩家）

1. **Poweramp**：导入 v5 PEQ（场景 A 步骤）
2. **外置 DSP**（如 Helix DSP Mini / Audison bit One / miniDSP）：
   - 分频：按 `crossover.frequencies_hz` 设置分频点 / 斜率
   - 延迟：按 `delay.per_driver_ms` 设置时间对齐
   - 动态：按 `dynamics.compressor` / `dynamics.limiter` 设置压缩限幅
   - 增益：按 `gain.frontend_output_z_max_ohm` 设置输入阻抗（若支持）
3. **系统连接**：手机 / 主机 → 外置 DSP → 功放 → 扬声器

### 场景 C：Bose QC 45 / TWS 等智能设备

1. **关闭厂商 App 内置 EQ**（Bose Music / Ugreen App），避免与 Poweramp 串联
2. **开启 LDAC / aptX HD**（开发者选项 / App 内设置）
3. 导入 v5 PEQ 到 Poweramp
4. 厂商动态 EQ 仍在工作（与 Poweramp 静态 EQ 互补）

## 后续维护建议

1. **声学特点.txt 更新时**：复核 V5_NEW_PARAMS 是否仍准确（特别是前端输出阻抗建议）
2. **新设备加入时**：按 8 维度 + 4 新维度扩展 V5_NEW_PARAMS 字典
3. **PEQ 调整时**：修改 v3 / v4统一无损 后重跑本脚本（v5 自动继承）
4. **跨设备对比**：用 `peq_cli.py list-profiles` 配合 `extras` 字段做横向对比
