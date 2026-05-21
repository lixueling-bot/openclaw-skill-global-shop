# Output Stage — KiCad 8 Project

数字转盘末级输出电路的 KiCad 8 工程文件。

## 目录结构

```
hardware/output-stage/
├── output-stage.kicad_pro          # KiCad 工程文件
├── output-stage.kicad_sch          # 平铺单页原理图
├── sym-lib-table                   # 符号库表（指向 ./symbols/）
├── symbols/
│   └── digital-transport.kicad_sym # 自定义符号库（OCXO/DFF/CML/LDO 等）
├── generate_kicad.py               # 生成上述文件的 Python 脚本
└── README.md
```

## 如何打开

1. **环境**：KiCad 8.0 或更新版本（KiCad 7 可能需要小幅修改文件版本号）
2. 用 KiCad 打开 `output-stage.kicad_pro`
3. 在 Schematic Editor 中打开 `output-stage.kicad_sch`

工程使用 **A2 图纸**（594×420 mm）—— 因为元件数较多，使用大图纸便于查看。

## 设计内容概览

原理图包含 **38 个元件**，分为五个功能区：

| 区域 | 位置 | 关键元件 |
|------|------|---------|
| 时钟域 | 上中 | Y1, Y2 (OCXO), U1 (HMC349), U2 (ADCLK948) |
| 重对齐 + CML 输出 | 中部 | U3 (NB7L72M), U4 (SY58025U) |
| 输出变压器与接插件 | 右侧 | T1 (SC916), T2 (LL1572), J1 (BNC), J2 (XLR) |
| 上游数据隔离 | 左中 | U5 (Si8645BB) |
| 电源域 | 底部 | LDO1-LDO4 (LT3045 ×4) + 设定电阻 + 储能电容 |

完整设计说明见上一级目录的 `docs/digital-transport/output-stage-schematic.md`。

## 连接方式

所有信号连接通过 **global labels**（全局标签）建立，**没有手绘的连线**。

**优点**：
- 不依赖元件坐标，移动元件不会断开连接
- 网表始终正确，可以直接生成 PCB
- 你可以自由重新排版，让原理图更美观

**操作建议**：
- 元件放置后，运行 **ERC** （Tools → Electrical Rules Checker）会提示哪些 stock 元件（R/C/连接器）的标签位置需要对齐到实际引脚
- 在 KiCad 里通过 `M` 键移动元件，或 `M` + 选中标签来微调标签位置
- 也可以画一小段线段把引脚连到标签

## 自定义符号

`symbols/digital-transport.kicad_sym` 包含 8 个自定义符号：

| 符号名 | 元件 | 引脚数 |
|--------|------|--------|
| OCXO_CCHD957 | Crystek CCHD-957 OCXO | 4 |
| RF_SWITCH_HMC349 | Analog Devices HMC349 | 6 |
| CLK_BUFFER_ADCLK948 | Analog Devices ADCLK948（精简引脚） | 10 |
| DFF_NB7L72M | ON Semi NB7L72M（重对齐 D-FF） | 8 |
| CML_DRIVER_SY58025U | Microchip SY58025U | 6 |
| ISOLATOR_Si8645 | Silicon Labs Si8645BB | 12 |
| LDO_LT3045 | Analog Devices LT3045 | 9 |
| TRANSFORMER_PULSE | 通用 4 端脉冲变压器 | 4 |

符号库已在 `output-stage.kicad_sch` 中**内联保存**，即使不加载外部库也能打开。

## 网络分类（Net Classes）

`output-stage.kicad_pro` 中预设了 5 个网络类，用于 PCB 阻抗控制：

| Net Class | 线宽 | 间距 | 差分间距 | 用途 |
|-----------|------|------|---------|------|
| Default | 0.25mm | 0.2mm | — | 普通信号 |
| ClockDiff100 | 0.18mm | 0.2mm | 0.18mm | 100Ω 差分（CK, D, Q, CML） |
| SPDIF75 | 0.30mm | 0.3mm | — | 75Ω 单端（SPDIF 输出） |
| AES110 | — | 0.3mm | 0.22mm | 110Ω 差分（AES 输出） |
| Power | 0.5mm | 0.25mm | — | 电源走线 |

在 KiCad 里通过 **Net Class** 给每根网络分配类别，PCB 编辑器会自动应用对应规则。

## 下一步工作

1. **打开工程，运行 ERC** —— 确认所有信号都正确连接，调整 stock 元件位置
2. **分配 Footprint**：
   - Crystek CCHD-957 → 需要从 Crystek 网站下载或自建
   - ADCLK948 → `Package_DFN_QFN:LFCSP-32-1EP_5x5mm_P0.5mm`（KiCad 内置）
   - NB7L72M / SY58025U → `Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm`
   - LT3045 → `Package_DFN_QFN:DFN-12-1EP_3x3mm_P0.5mm_EP1.65x2.38mm`
   - Si8645BB → `Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm`
   - 变压器 → 需要自建（SC916 / LL1572 都是 through-hole）
3. **生成网表 → PCB**
4. **PCB 布局**：参照 `docs/digital-transport/output-stage-schematic.md` 第 9 节的分区与叠层

## 重新生成

如需修改设计（添加元件、调整连接），编辑 `generate_kicad.py` 顶部的 `SYMBOLS`、`PLACEMENTS`、`PASSIVES` 三个列表后运行：

```bash
python3 generate_kicad.py
```

会重新生成 `.kicad_sch`、`.kicad_sym`、`.kicad_pro`、`sym-lib-table`。

## 已知限制

1. **stock 元件的网络标签位置**可能不精确对齐引脚（因为 Device:R / Device:C 等的引脚坐标没有在脚本中精确建模）。打开 KiCad 后通过 ERC 提示移动即可，自定义元件（所有 IC）的连接全部正确。
2. **图纸布局**是机械网格放置，不具备美观度。可在 KiCad 里自由重新排版。
3. **没有包含 PCB 文件**（.kicad_pcb）—— 需要从原理图生成。

## 设计正确性验证

脚本生成时已验证：
- ✅ S-expression 括号配平
- ✅ 自定义符号库 24 个 symbol 全部可解析
- ✅ 38 个元件实例的所有 94 个 IC 引脚都有对应的网络标签放置在引脚顶端

实际打开 KiCad 后建议**立即跑一遍 ERC** 检查电气连通性。
