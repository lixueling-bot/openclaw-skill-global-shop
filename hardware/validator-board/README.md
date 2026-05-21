# Output Stage Core Validator (OSCV) — KiCad 8 Project

> **目的**：用一块 80×50mm 的小 PCB 验证整个数字转盘项目的两个核心理论假设。
> 详细测试方案见上一级 `docs/digital-transport/validator-board.md`。

## 板上元件

最小子集，仅包含验证所需：

| 元件 | 数量 | 用途 |
|------|------|------|
| Crystek CCHD-957 OCXO 22.5792MHz | 1 | 主时钟 |
| ON Semi NB7L72M | 1 | **重对齐 D-FF（验证假设 A）** |
| Microchip SY58025U | 1 | **CML 恒流驱动（验证假设 B）** |
| Scientific Conversion SC916 | 1 | SPDIF 输出变压器 |
| Analog Devices LT3045 | 3 | 三路独立 LDO（CLK / DIG / DRV） |
| TI LM317 | 1 | 预稳到 +6V |
| STM32G031F8P6 (header only) | 1 | PRBS 测试源 |
| BNC 75Ω | 1 | 主输出 |
| SMA edge mount | 7 | 测试点 |

**板总 BOM ~$205**，加上 5 块 JLCPCB 打样约 $35，**总验证成本 ~$240**。

## 测试输入与输出

```
                  外部信号发生器  ─→ SMA[D_EXT]    ┐
                                                    │
                  板上 OCXO ÷2 分频  ──────────────┤  跳线选择 → D-FF D 输入
                                                    │
                  板上 STM32 PRBS  ────────────────┘

  测试点（SMA）：
    TP_CK       OCXO 直出（经 1kΩ 隔离）
    TP_DIN      D-FF 输入
    TP_QOUT     D-FF 输出（重对齐后）
    TP_CMLP     CML 输出（变压器初级）
    TP_VCC_CLK  OCXO 电源轨（监测纹波）
    TP_VCC_DRV  CML 电源轨（监测纹波）

  主输出：
    BNC         75Ω SPDIF，进示波器或 DAC
```

## 三种 D 源（跳线选择）

板上有两个 6 针跳线（`JP_D` 和 `JP_DN`）选择 D-FF 的差分输入信号来源：

| 跳线位置 | D 源 | 用途 |
|---------|------|------|
| A | SMA `D_EXT` | 外部信号发生器（最严格的抖动注入测试） |
| B | OCXO ÷2 | 基准测试，D 与 CK 同源，输出应为 ÷2 干净方波 |
| C | STM32 PRBS | 切换 PRBS 模式，验证 CML 数据无关性 |

## 关键验证目标

| Test | 通过条件 |
|------|---------|
| **Test 1** OCXO 自身相噪 | < 1 ps RMS（10kHz-1MHz 积分） |
| **Test 2** Reclock 消除抖动 | 注入 0-1 ns RMS 抖动，输出浮动 < ±0.5 ps |
| **Test 3** CML 数据无关性 | LDO 输出端电流变化 < 10μA RMS |
| **Test 4** 端到端 | 5 种数据模式下输出抖动最大-最小差 < 0.5 ps |
| **Test 5** vs Esoteric P-02X | ABX 盲听不可区分 |

完整测试程序详见 `../../docs/digital-transport/validator-board.md` 第 5 节。

## 工程结构

```
hardware/validator-board/
├── validator-board.kicad_pro        KiCad 8 工程
├── validator-board.kicad_sch        平铺单页原理图（A3）
├── sym-lib-table                    符号库表
├── symbols/
│   └── digital-transport.kicad_sym  自定义符号库（5 个符号，复用自 output-stage）
├── generate_kicad.py                生成脚本（reuse 自 output-stage 的符号定义）
└── README.md                        本文件
```

## 验证结果

打开 KiCad 之前，工程文件已经过自动验证：

- ✅ S-expression 括号配平
- ✅ 64 个元件实例（9 个 IC + 55 个无源）
- ✅ 144 个全局网络标签
- ✅ 所有 IC 引脚都有对应的网络标签

## 与主输出板的关系

本板是 `../output-stage/` 的精简子集，省略了：

- 第二颗 OCXO（24.576MHz，48k 系列） + HMC349 RF 切换
- ADCLK948 时钟 fanout buffer（单负载下不需要）
- 第二颗变压器（LL1572 AES/EBU 输出）
- Si8645 隔离器（验证板上直连 D 输入便于注入抖动）
- 第 4 路 LDO（+3V3_ISO）
- 整机电源（用电池便于排除市电干扰）

**所有保留下来的元件型号、走线规则、PCB 叠层和主板完全一致**——验证结果可直接外推到整机性能。

## 下一步

1. 在 KiCad 中打开 `validator-board.kicad_pro`
2. 跑 ERC，调整 stock 元件标签对齐
3. 分配 footprint，生成 PCB
4. PCB 布局按 `../../docs/digital-transport/validator-board.md` 第 6 节
5. JLCPCB 打样 → 焊接 → 上电按 §8 顺序调试
6. 跑 Test 1-5，记录数据
7. **写 `validation-report.md` 决定是否进入整机阶段**
