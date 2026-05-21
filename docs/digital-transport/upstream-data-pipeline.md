# 上游数据流水线设计

## 0. 设计目标

把音频文件（FLAC / WAV / DSF / DFF）从存储介质送到末级电路 Si8645 隔离器的输入端，要求：

1. **数据 bit-perfect**：解码 / 解压完成后到 I2S 输出，整条路径不允许任何采样率转换、抖动校正、电平调整、滤波
2. **播放期间电气行为与音乐内容完全解耦**：CPU 不动、文件系统不动、网络不动、解码不动；只有 FPGA 的固定状态机在搬数据
3. **整轨预读 + 内存播放**：播放开始时整轨已经在 RAM 里，存储/网络/解码模块**可以断电**
4. **galvanic 与末级隔离**：和末级电路之间只有 Si8645 / 光纤通信，无共地

---

## 1. 顶层架构

```
═══════════════════════════════════════════════════════════════════════
                          HOST 域（吵，没关系）
═══════════════════════════════════════════════════════════════════════

   [SSD NVMe]               ← 大容量音乐库
       │ M.2
       ▼
   [SBC: i.MX8M-Plus / RK3568 / 自研 MCU 板]
       │
       ├─→ 网络 (gigabit Ethernet) - 流媒体/NAS
       ├─→ USB 3.0 - 移动盘 / DAC控制
       ├─→ HDMI - 屏显（可选）
       │
       │ 运行：
       │   • 最小化 Linux (PREEMPT_RT) 或 ThreadX
       │   • MPD / squeezelite / 自研播放器
       │   • FLAC / Opus / DSD 解码器
       │   • 文件系统、网络栈
       │
       │ 输出：
       │   • SPI（控制命令送给 FPGA）
       │   • Quad-SPI 或 LVDS（解码后的 PCM/DSD 数据送给 FPGA）
       │
   ───┼─────────────────────────────────────────────────────────────
      │
  ════│════════════ GALVANIC 隔离边界 ═════════════════════════════
      │ (4× Si8645BB 跨过这道边界，分别承载：
      │  控制 SPI、数据 LVDS、状态反馈、master clock 反向送回)
      │
   ───┼─────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════
                  PLAYBACK 域（必须安静、确定性、单调）
═══════════════════════════════════════════════════════════════════════

   ┌──────────────────────────────────────────────────────────┐
   │  FPGA: Xilinx Artix-7 35T (XC7A35T-1FGG484C)             │
   │                                                            │
   │  播放期间运行的逻辑（全部固定状态机，无 CPU）：           │
   │   1. PSRAM 读控制器（按 BCLK 节拍读取）                  │
   │   2. I2S 输出格式器（PCM/DSD 切换）                       │
   │   3. 主时钟分频器（22.5792 → BCLK / LRCK）               │
   │   4. SPI 接收（来自 host 的控制命令，握手用）             │
   │                                                            │
   │  装载期间额外运行：                                       │
   │   5. LVDS 接收器（从 host 接收解码后数据流）             │
   │   6. PSRAM 写控制器                                       │
   └──────────────────────────────────────────────────────────┘
       │ ↑ 8 颗 PSRAM 数据/地址                                
       ▼ │                                                     
   ┌──────────────┐                                            
   │ PSRAM ×8     │ ← 总容量 512 MB（足够装一整张 DSD256 专辑）
   │ APS25608N    │                                            
   │ 64 MB ×8     │                                            
   └──────────────┘                                            
                                                                
       FPGA I2S 输出 ────→ [Si8645] ──→ 末级 D-FF 输入 (D, BCLK, LRCK)
                              ↑                                
       FPGA 时钟输入 ←──────  Si8645 ←── 末级 OCXO MCLK (反向)
                                                                
   ┌──────────────────────────────────────┐                    
   │ 独立 LDO（LT3045 ×N）                │                    
   │  +3.3V_FPGA, +1.0V_CORE, +1.8V_AUX  │                    
   │  +1.8V_PSRAM, +1.2V_DDR             │                    
   │  全部从专用变压器副绕组供电          │                    
   └──────────────────────────────────────┘                    
```

---

## 2. 关键架构决策

### 2.1 为什么 host 和 playback 域要分开？

| Host 域 | Playback 域 |
|---------|-------------|
| 跑 Linux/RTOS，有调度抖动 | 纯硬件状态机，时钟周期级确定性 |
| 文件系统 I/O 突发 | 等间隔从 PSRAM 读 |
| 网络/USB 中断随时来 | 没有中断，没有任务调度 |
| 解码器电流随音乐内容变化 | 电流和音乐无关（PSRAM 读访问模式恒定） |
| **电气行为随音乐变化** | **电气行为完全恒定** |

让它们物理隔离（不共电源、不共地、只通过 Si8645 通信），就让 host 的所有"音乐相关污染"**到不了 playback 域**。

### 2.2 为什么用 PSRAM 而不是 DDR？

| 项 | DDR4 | PSRAM | SRAM |
|----|------|-------|------|
| 容量 | 1-16 GB | 64-512 MB | 2-16 MB |
| 刷新 | 外部控制，必须做 | 内部自动，固定模式 | 无 |
| 接口复杂度 | 高（控制器要 PHY、训练） | 简单（QSPI/HyperBus） | 极简（异步） |
| 功耗变化 | 大（DRAM 访问突发） | 小（内部刷新匀速） | 极小 |
| 价格/MB | $0.01 | $0.1 | $1+ |

**选 PSRAM**：
- 容量够（512MB 装 5 张 DSD256 专辑或 1 张 DSD512 长曲）
- 内部刷新是**固定周期**（约 16μs 间隔），对外表现为**和音乐无关的固定纹波** → DAC 端听不见
- 接口比 DDR 简单 10 倍，FPGA 逻辑省 80%

**SRAM 太小**：单芯片最大 16Mb（2MB），装一张 DSD256 单曲要 16 颗 SRAM，PCB 占面积 + 走线复杂度爆炸。

**DDR 太复杂**：必须用 DDR PHY IP、做训练校准、刷新调度，控制器复杂度高，且 DDR 工作时**电源纹波随访问 burst 强烈变化**。

**最终方案**：8 颗 **AP Memory APS25608N** (64MB, 200MHz QSPI/HyperBus)，并联组成 512MB / 64-bit 总线。

### 2.3 SBC 怎么选？

要求：
- 能跑 Linux + 文件系统 + 网络
- 有足够 I/O 把数据送给 FPGA（>= QSPI）
- 内置硬件解码 FLAC 是加分项（其实软解就够，CPU 完全闲）

**推荐档次**：

| 档次 | 型号 | 内核 | 价格 | 备注 |
|------|------|------|------|------|
| 入门 | Raspberry Pi CM4 | 4× A72 1.5GHz | $60 | 现成、生态好，PCIe 接 NVMe |
| **首选** | **NXP i.MX 8M Plus** | 4× A53 1.8GHz + Cortex-M7 + NPU | $40 (SoC) | 工业级，长寿命，M7 可专跑实时任务 |
| 高端 | Xilinx Zynq UltraScale+ ZU3EG | 4× A53 + PL FPGA | $200 | 集成 FPGA，但和 playback FPGA 需分开供电 |

选 **i.MX 8M Plus** 的理由：
- A53 跑 Linux 处理文件 + 网络
- **Cortex-M7 实时核**专门负责把解码后的 PCM 流送给 playback FPGA，避免 Linux 调度抖动
- 工业级温度范围、10+ 年供货保证
- 内置千兆 Ethernet、USB3、PCIe2，外设全

### 2.4 FPGA 选 Artix-7 35T

需求清点：
- I/O：PSRAM 64-bit 数据线 + 地址 + 控制 ≈ 100 个 I/O
- 内部逻辑：PSRAM 控制器 + I2S 输出 + 命令解析 ≈ 5000 LUT
- BRAM：FIFO 缓冲 4-8KB
- 速度：PSRAM 200MHz，逻辑 100MHz 够

**Artix-7 35T 满足**：
- 33280 LUT（用 15%）
- 100 I/O（FGG484 封装 285 I/O）
- 1800Kb BRAM（用 < 1%）
- $40 单片

也可用 **Lattice ECP5-25F**（开源工具链 Yosys+nextpnr，省 Vivado 许可证）。

---

## 3. PSRAM 子系统详细设计

### 3.1 拓扑

8 颗 PSRAM 并联成 64-bit 数据总线（每颗 8-bit DQ），地址/控制总线共享：

```
                FPGA
                  │
        ┌─────────┼─────────┐
        │   命令/地址/时钟  │  (并联到所有 8 颗)
        │   CK, CK#, CS#,  │
        │   CMD[7:0]       │
        └─────────┬────────┘
                  │
   ┌───┬───┬───┬──┴┬───┬───┬───┬───┐
   │ U1│ U2│ U3│ U4│ U5│ U6│ U7│ U8│   8× APS25608N (64 MB each, 8-bit DQ each)
   │   │   │   │   │   │   │   │   │
   │DQ0│DQ1│DQ2│DQ3│DQ4│DQ5│DQ6│DQ7│   (8-bit per chip, parallel = 64-bit bus)
   │[7:│[7:│[7:│[7:│[7:│[7:│[7:│[7:│
   │ 0]│ 0]│ 0]│ 0]│ 0]│ 0]│ 0]│ 0]│
   └───┴───┴───┴───┴───┴───┴───┴───┘
        到 FPGA 的 64 个 DQ 输入
```

### 3.2 关键波形和时序

- 接口模式：**Octal HyperBus** (8-bit DDR @ 200MHz = 400 MT/s × 8 = 3.2 Gbps per chip)
- 8 颗并联：64-bit @ 400MT/s = **25.6 Gbps 总带宽**
- 一张 DSD512 立体声: 45 Mbps，**带宽过剩 500 倍** → FPGA 可以做超低占空比读取（读一次缓存几 ms 数据，然后空闲）

### 3.3 为什么超低占空比读取是关键

PSRAM 不读时电流极低（几 mA）。读时电流大（几十 mA）。如果**让读访问短而稀疏**：
- 8KB SRAM 在 FPGA 内做 FIFO，每 ~10ms 触发一次 burst 读
- Burst 读 8KB 只需 ~2μs（25.6 Gbps）
- **PSRAM 99.98% 时间在空闲低电流状态**
- I2S 输出由 FIFO 提供，访问 PSRAM 的 burst **完全和音频信号节奏无关**

这是关键设计点：**让访问模式去音乐化**。无论你播放纯音乐还是静音，PSRAM 的访问 burst 都是固定间隔 10ms 的小尖峰，对电源/地的影响**完全可预测、和音乐无关**。

### 3.4 PSRAM 选型

| 型号 | 厂家 | 容量 | 接口 | 价格 |
|------|------|------|------|------|
| **APS25608N-OBR-BG** | AP Memory | 64MB | Octal HyperBus 200MHz | $5 |
| W958D6NKY5I | Winbond | 64MB | Octal SPI 200MHz | $4 |
| MX25UM51245GXDI00 | Macronix | 64MB | Octal SPI 200MHz | $6 |

选 APS25608N：FBGA-24 小封装、3.3V/1.8V 双 VCC，最常用。

---

## 4. FPGA 内部架构

```
                ┌────────────────────────────────────────────────────┐
                │                  FPGA: Artix-7 35T                  │
                │                                                      │
   MCLK_22M ────│→[Clock Manager (MMCM)]                              │
   from output  │   │                                                  │
   stage via    │   ├── BCLK_22M / 2  ─── 11.2896 MHz (DSD)           │
   Si8645       │   ├── BCLK_22M / 8  ─── 2.8224 MHz (PCM 44.1k 64fs) │
                │   ├── BCLK_22M / 4  ─── 5.6448 MHz (PCM 88.2k)      │
                │   └── PSRAM_CLK_200 ─── 200 MHz (PSRAM ref)         │
                │                                                      │
                │   ┌──────────────────┐                              │
                │   │  Command Parser  │ ← SPI (from host MCU)        │
                │   │  (state machine) │   - LOAD_TRACK(addr, len)    │
                │   └────────┬─────────┘   - PLAY(addr, len, fmt)     │
                │            │             - PAUSE / STOP             │
                │            ▼                                         │
                │   ┌──────────────────┐                              │
                │   │  Master FSM      │ ── 状态: IDLE / LOAD / PLAY  │
                │   └────────┬─────────┘                              │
                │            │                                         │
                │   ┌────────┼─────────────────────────────────────┐  │
                │   │        ↓                                      │  │
                │   │  ┌─────────────┐    ┌──────────────┐         │  │
                │   │  │ PSRAM Ctrl  │←──→│  PSRAM bus   │         │  │
                │   │  │ (HyperBus)  │    │  to 8× chips │         │  │
                │   │  └──────┬──────┘    └──────────────┘         │  │
                │   │         │                                      │  │
                │   │         ▼ (read burst, ~8KB at a time)        │  │
                │   │  ┌─────────────┐                              │  │
                │   │  │  Block RAM  │  (8KB FIFO, dual-port)       │  │
                │   │  │  FIFO       │                              │  │
                │   │  └──────┬──────┘                              │  │
                │   │         │ (read at BCLK rate)                 │  │
                │   │         ▼                                      │  │
                │   │  ┌─────────────┐                              │  │
                │   │  │ I2S Encoder │  ← clocked by BCLK/LRCK     │  │
                │   │  │ DSD passthru│                              │  │
                │   │  └──────┬──────┘                              │  │
                │   │         │ SDATA, BCLK, LRCK                  │  │
                │   └─────────┼─────────────────────────────────────┘  │
                │             │                                         │
                │   ──────────┼──────→ Si8645 (隔离) → 末级 D-FF       │
                │             │                                         │
                │   ┌─────────┴─────────┐                              │
                │   │  LVDS RX (LOAD)   │ ← from host MCU (only       │
                │   │  (装载期间)        │   active during loading)    │
                │   └───────────────────┘                              │
                └────────────────────────────────────────────────────┘
```

### 4.1 状态机

```
       ┌─────────┐
       │  IDLE   │ ←─── 复位后默认状态
       └────┬────┘     PSRAM 空闲，所有 I/O 静止
            │
            │ host 发 LOAD_TRACK(addr, len)
            ▼
       ┌─────────┐
       │  LOAD   │     LVDS 接收 host 发来的 PCM/DSD 流
       └────┬────┘     写入 PSRAM @ addr
            │           (此时 host 还在解码工作，吵)
            │
            │ host 发 LOAD_DONE
            ▼
       ┌─────────┐
       │ READY   │     等待播放命令；host 可以断电或 idle
       └────┬────┘
            │
            │ host 发 PLAY(addr, len, fmt)
            ▼
       ┌─────────┐
       │  PLAY   │ ←─┐  纯硬件状态机，循环：
       └────┬────┘   │  1. 检查 FIFO 余量
            │        │  2. 余量 < 50% 时 burst 读 PSRAM
            │        │  3. I2S 编码器从 FIFO 读出数据
            │        │  4. SDATA/BCLK/LRCK 输出
            │        │
            │        │  此期间 host 可以完全断电
            │        │
            │        └─── 直到 len 字节读完
            │
            ▼
       ┌─────────┐
       │  DONE   │     向 host 报告播放完成
       └─────────┘     等待下一条 LOAD 命令
```

**关键**：PLAY 状态下，FPGA 唯一的活动是"按 BCLK 节拍从 FIFO 移位输出 + 偶尔填充 FIFO"。没有 CPU、没有解码、没有中断、**电流曲线完全周期性**。

### 4.2 I2S 输出格式器

支持的格式：

| 格式 | LRCK | BCLK | SDATA |
|------|------|------|-------|
| PCM 16-bit | fs (44.1k/48k...) | 64 × fs | 标准 I2S |
| PCM 24-bit | fs | 64 × fs | 标准 I2S |
| PCM 32-bit | fs | 64 × fs | 标准 I2S |
| DSD64 | — | 2.8224 MHz | DSD raw bit stream |
| DSD128 | — | 5.6448 MHz | DSD raw |
| DSD256 | — | 11.2896 MHz | DSD raw |
| DSD512 | — | 22.5792 MHz | DSD raw |

DSD 透传时 LRCK 不用，FPGA 把比特流直接送到 SDATA 引脚，BCLK = DSD 比特率。

---

## 5. Host MCU (i.MX 8M Plus) 软件栈

### 5.1 软件架构

```
┌──────────────────────────────────────────────────────────┐
│  Cortex-A53 ×4 (跑 Linux 5.10 + PREEMPT_RT)             │
│                                                            │
│   ┌──────────────────────────────────────────────────┐  │
│   │ Userspace                                          │  │
│   │  - mpd (Music Player Daemon) + custom output      │  │
│   │  - flac/dsd/wav decoders                          │  │
│   │  - Web UI (optional)                              │  │
│   │  - Network share (Samba client, Roon Ready, UPnP) │  │
│   └────────────────┬─────────────────────────────────┘  │
│                    │                                       │
│                    │ shared memory + IPC                   │
│                    ▼                                       │
│   ┌──────────────────────────────────────────────────┐  │
│   │ Kernel driver: transport_ipc                       │  │
│   │  - manages handoff to M7 core                     │  │
│   │  - exposes /dev/transport0 to userspace           │  │
│   └────────────────┬─────────────────────────────────┘  │
└────────────────────│─────────────────────────────────────┘
                     │ RPMsg (shared memory inter-core IPC)
┌────────────────────┼─────────────────────────────────────┐
│  Cortex-M7 (跑裸机 / FreeRTOS, 实时核)                  │
│                    │                                       │
│   ┌────────────────────────────────────────────────┐    │
│   │ Realtime audio shuttle:                          │    │
│   │  - 接收 A53 传来的 PCM/DSD 缓冲                 │    │
│   │  - 通过 QSPI 或 LVDS 把数据送给 FPGA            │    │
│   │  - 在播放期间，A53 可以 suspend 进入低功耗     │    │
│   │  - 维护和 FPGA 的 SPI 控制链路                  │    │
│   └────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 5.2 工作流（播放一首曲子）

```
T=0   Web UI 选择曲目 → mpd 收到指令
T=10ms  mpd 从 SSD 读取 FLAC 文件，开始解码
T=50ms  解码出前 8MB PCM 数据，通过共享内存交给 M7
T=60ms  M7 通过 LVDS 把数据流送给 FPGA
T=200ms FPGA 收完 8MB，写入 PSRAM
T=200ms-继续... mpd 继续解码、M7 继续送、FPGA 继续写
        直到整轨载完（典型 30-300MB，2-15 秒）
T=Tload+ε  M7 给 FPGA 发 PLAY 命令
        FPGA 进入 PLAY 状态
        A53 可以选择 suspend（深度睡眠）以降低噪声
T=Tload+ε  音乐开始从 BNC/XLR 流出
         ...
T=末尾前 30s  M7 唤醒 A53，提前解码下一轨（gapless）
T=末尾  FPGA 报告 DONE，自动切下一轨
```

### 5.3 为什么 A53 在播放期间可以 suspend

播放期间所有音频数据都在 FPGA 的 PSRAM 里。A53 不需要参与。所以可以：
- **A53 进入 Suspend-to-RAM 或 Suspend-to-Idle**：CPU 时钟停，外设时钟大部分停，功耗从 2W 降到 200mW
- **A53 + M7 都进入 idle**：M7 仅在 FPGA 报告"FIFO 余量低需要补数据"时唤醒（实际不需要，因为整轨已在 PSRAM）
- **极致版本**：M7 也可以 idle，直到收到 FPGA 的"播放完成"信号才唤醒
- **更极致**：物理切断 A53 / M7 的电源，只留 FPGA 工作

这一步是数字转盘超越 CD 转盘的**核心机制**：CD 转盘必须实时转、实时纠错；我们在播放期间**整个计算机都可以关机**，只剩 FPGA + PSRAM + OCXO 在工作。

---

## 6. Galvanic 隔离边界（Host ↔ Playback）

通过 4 颗 Si8645BB（每颗 4 通道）跨越边界：

| 隔离器 | 通道 | 方向 | 信号 |
|--------|------|------|------|
| ISO1 | CH1 | Host → Playback | SPI MOSI (control) |
| ISO1 | CH2 | Host → Playback | SPI SCLK |
| ISO1 | CH3 | Host → Playback | SPI CS |
| ISO1 | CH4 | Playback → Host | SPI MISO (status) |
| ISO2 | CH1-4 | Host → Playback | LVDS data (4 lanes) for bulk load |
| ISO3 | CH1-4 | Host → Playback | LVDS data lanes 5-8 |
| ISO4 | CH1 | Playback → Host | LOAD_DONE / PLAY_DONE flags |
| ISO4 | CH2 | Host → Playback | RESET |
| ISO4 | CH3 | Reserved | — |
| ISO4 | CH4 | Reserved | — |

**关键**：Si8645 的两侧地（GNDA / GNDB）**物理上不连接**——只通过芯片内部的电容耦合传递信号。

注意：**master clock 不通过这道边界送给 host**。Host 用自己的便宜晶振，因为 host 输出的数据会在 FPGA 端被 PSRAM 缓冲，最后由 master clock 驱动出去——host 的时钟精度无所谓。

---

## 7. 电源域

Playback 域专用电源（和末级一样的标准）：

| 轨 | 电压 | 电流 | 用途 | LDO |
|----|------|------|------|-----|
| +5V_RAW | +5V | 2A | LDO 输入预稳 | — |
| +3.3V_FPGA | +3.3V | 500mA | FPGA bank I/O | LT3045 |
| +1.0V_CORE | +1.0V | 1A | FPGA core | LT3045 + 跟随 |
| +1.8V_AUX | +1.8V | 200mA | FPGA aux | LT3045 |
| +1.8V_PSRAM | +1.8V | 800mA | 8 颗 PSRAM | LT3045 ×2 并联 |
| +3.3V_PSRAM_IO | +3.3V | 200mA | PSRAM IO bank | LT3045 |

Host 域用独立的开关电源（吵但和 playback 隔离）即可：
- 12V 主入 → 5V/3.3V/1.8V/1.2V DC-DC 给 i.MX 和 SSD
- 不需要超低噪 LDO，因为隔离边界已经切断了

**关键**：playback 域专用变压器副绕组，**不和 host 共享市电整流回路**。

---

## 8. 已知风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| PSRAM 内部刷新引入纹波 | 微弱底噪 | 选 PSRAM 而非 DRAM；FPGA 端电源大容量储能（22μF × 8 颗 + 100μF 钽 × 4 颗） |
| FPGA 内部时钟切换噪声 | FPGA core 电流抖动 | core 电源用 LT3045 + 蓄能电容；FPGA 时钟域尽量少 |
| 装载期间 LVDS 数据流引入瞬态电流 | 影响装载期音质（其实此时不播音乐） | 装载 → 播放之间留 100ms 静默缓冲，等 LVDS 完全静止 |
| Host 通过 Si8645 反向 leak 共模噪声 | 末级看到轻微地噪偏移 | Si8645 旁路 100pF 共模电容；playback 域接 1 个机壳地点（10Ω 软接） |
| Gapless 播放期间 host 必须工作 | 曲间噪声变化 | 提前在曲目末尾 30s 唤醒 host，让 LVDS 装载在曲末 30s 内完成；曲间播放只剩 FPGA |
| FPGA 配置时电流抖动 | 上电瞬间噪声 | FPGA 配置完成后等 5s 再启动 OCXO 输出，避免重叠 |

---

## 9. 验证计划

### Phase 1: FPGA 子系统板级验证

1. 上电后用示波器测各电源轨噪声（频谱分析仪 9kHz-1GHz）
2. 把 FPGA I2S 输出直接（不经 Si8645）连到一台基准 DAC（如 Mola Mola Tambaqui），用其 J-Test 测试模式测 jitter
3. 目标：FPGA I2S 输出的 jitter < 20 ps RMS（不算末级 reclock）

### Phase 2: 全链路 jitter 测量

1. FPGA → Si8645 → 末级 → BNC/XLR，整链路接基准 DAC
2. 测 DAC 端解析出的 jitter（应该 < 5 ps，因为末级会用 OCXO 重对齐）
3. 验证：播放白噪声 vs 静音 vs 正弦，jitter 数值**不能有任何变化**（这就是"和音乐解耦"的客观指标）

### Phase 3: 主观对比

1. 同 DAC，A vs B：
   - A: 本数字转盘
   - B: Esoteric P-02X / dCS Vivaldi One Apex / Wadax Atlantis Reference
2. 盲听 ABX，每组 20 次

**目标**：在 95% 置信度下，本机和参考 CD/SACD 转盘**不可区分**（甚至更好）。

---

## 10. BOM 概要（Playback 域核心）

| 元件 | 型号 | 数量 | 单价 |
|------|------|------|------|
| FPGA | Xilinx XC7A35T-1FGG484C | 1 | $40 |
| PSRAM | AP Memory APS25608N-OBR-BG | 8 | $5 ×8 = $40 |
| 隔离器 | Silicon Labs Si8645BB | 4 | $6 ×4 = $24 |
| LDO | Analog Devices LT3045 | 8 | $7 ×8 = $56 |
| FPGA 配置 Flash | Micron MT25QL128 | 1 | $3 |
| 振荡器（本地，仅 FPGA 启动用） | 25MHz crystal | 1 | $1 |
| 被动元件 | 电阻/电容 | 一批 | ~$30 |
| **Playback 域小计** | | | **~$200** |

| Host 域 | 型号 | 数量 | 单价 |
|---------|------|------|------|
| SoM | i.MX 8M Plus SoM (变信 / Compulab) | 1 | $150 |
| NVMe SSD | Samsung 980 Pro 2TB | 1 | $150 |
| Ethernet PHY | KSZ9131 | 1 | $5 |
| USB hub | USB3.0 4-port | 1 | $10 |
| **Host 域小计** | | | **~$320** |

**整机上游小计：约 $520**（不含 PCB、机箱）

加上末级 $520，**整机 BOM 约 $1040**。售价定位 $20k-50k（顶级数字转盘市场区间）。

---

## 11. 不在本文档范围

- 整机电源（多组环牛、AC 处理）→ `power-system.md`
- 机箱、屏蔽、避震 → `chassis-mechanical.md`
- Host 软件实现细节 → `host-firmware/` （目录待建）
- FPGA Verilog/VHDL 实现 → `fpga/` （目录待建）
