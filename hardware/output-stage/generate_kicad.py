#!/usr/bin/env python3
"""
KiCad 8 schematic + symbol library generator for the digital transport output stage.

Generates:
  - symbols/digital-transport.kicad_sym  (custom symbol library)
  - output-stage.kicad_sch               (flat schematic with grid placement)
  - output-stage.kicad_pro               (KiCad project file)

Connections are made via global labels (no drawn wires) so the netlist is
guaranteed correct regardless of placement. After opening in KiCad you can
rearrange components and draw wires for visual clarity.
"""

import uuid
import json
import os
from pathlib import Path

OUT_DIR = Path(__file__).parent
SYM_DIR = OUT_DIR / "symbols"


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Custom symbol library
# ---------------------------------------------------------------------------

# Each symbol: name, footprint hint, pin list (number, name, x, y, orientation, type)
# orientation: 0=right (pin extends right), 180=left, 90=up, 270=down
# pin types: input, output, bidirectional, power_in, power_out, passive, unspecified
SYMBOLS = {
    "OCXO_CCHD957": {
        "footprint": "Oscillator:Oscillator_SMD_Crystek_CCHD-957-4Pin_9.0x14.0mm",
        "value": "CCHD-957",
        "description": "Crystek ultra-low-noise OCXO",
        "size": (15.24, 10.16),
        "pins": [
            ("1", "EN",  -10.16,  2.54, 0, "input"),
            ("2", "GND", -10.16, -2.54, 0, "power_in"),
            ("3", "OUT",  10.16, -2.54, 180, "output"),
            ("4", "VCC",  10.16,  2.54, 180, "power_in"),
        ],
    },
    "RF_SWITCH_HMC349": {
        "footprint": "Package_DFN_QFN:QFN-16-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
        "value": "HMC349ALP4CE",
        "description": "SP2T RF switch DC-4GHz",
        "size": (15.24, 12.7),
        "pins": [
            ("1", "RFC",  -10.16,  5.08, 0, "bidirectional"),
            ("2", "RF1",   10.16,  2.54, 180, "bidirectional"),
            ("3", "RF2",   10.16, -2.54, 180, "bidirectional"),
            ("4", "CTRL", -10.16,  0, 0, "input"),
            ("5", "VDD",  -10.16, -5.08, 0, "power_in"),
            ("6", "GND",   10.16, -5.08, 180, "power_in"),
        ],
    },
    "CLK_BUFFER_ADCLK948": {
        "footprint": "Package_DFN_QFN:LFCSP-32-1EP_5x5mm_P0.5mm_EP3.25x3.25mm",
        "value": "ADCLK948BCPZ",
        "description": "LVPECL clock fanout buffer 6-output",
        "size": (20.32, 17.78),
        "pins": [
            ("1", "CLK_IN",   -12.7,  7.62, 0, "input"),
            ("2", "CLK_INb",  -12.7,  5.08, 0, "input"),
            ("3", "OUT0p",     12.7,  7.62, 180, "output"),
            ("4", "OUT0n",     12.7,  5.08, 180, "output"),
            ("5", "OUT1p",     12.7,  2.54, 180, "output"),
            ("6", "OUT1n",     12.7,  0,    180, "output"),
            ("7", "OUT2p",     12.7, -2.54, 180, "output"),
            ("8", "OUT2n",     12.7, -5.08, 180, "output"),
            ("9", "VS",       -12.7, -2.54, 0, "power_in"),
            ("10", "GND",     -12.7, -7.62, 0, "power_in"),
        ],
    },
    "DFF_NB7L72M": {
        "footprint": "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
        "value": "NB7L72M",
        "description": "2.5GHz LVPECL master-slave D flip-flop (RECLOCK)",
        "size": (17.78, 15.24),
        "pins": [
            ("7",  "D",   -10.16,  5.08, 0, "input"),
            ("6",  "Db",  -10.16,  2.54, 0, "input"),
            ("9",  "CK",  -10.16, -2.54, 0, "input"),
            ("8",  "CKb", -10.16, -5.08, 0, "input"),
            ("3",  "Q",    10.16,  5.08, 180, "output"),
            ("4",  "Qb",   10.16,  2.54, 180, "output"),
            ("2",  "VCC",  10.16, -2.54, 180, "power_in"),
            ("1",  "VEE",  10.16, -5.08, 180, "power_in"),
        ],
    },
    "CML_DRIVER_SY58025U": {
        "footprint": "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
        "value": "SY58025U",
        "description": "CML output driver/equalizer (CONSTANT-CURRENT OUTPUT)",
        "size": (17.78, 12.7),
        "pins": [
            ("1", "INP",   -10.16,  3.81, 0, "input"),
            ("2", "INN",   -10.16,  1.27, 0, "input"),
            ("3", "OUTP",   10.16,  3.81, 180, "output"),
            ("4", "OUTN",   10.16,  1.27, 180, "output"),
            ("5", "VCC",    10.16, -3.81, 180, "power_in"),
            ("6", "VEE",   -10.16, -3.81, 0, "power_in"),
        ],
    },
    "ISOLATOR_Si8645": {
        "footprint": "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
        "value": "Si8645BB-B-IS1",
        "description": "Quad-channel digital isolator 150Mbps",
        "size": (20.32, 17.78),
        "pins": [
            ("2",  "A1",    -12.7,  7.62, 0, "input"),
            ("3",  "A2",    -12.7,  5.08, 0, "input"),
            ("4",  "A3",    -12.7,  2.54, 0, "input"),
            ("5",  "B4_IN", -12.7,  0, 0, "input"),
            ("15", "B1",     12.7,  7.62, 180, "output"),
            ("14", "B2",     12.7,  5.08, 180, "output"),
            ("13", "B3",     12.7,  2.54, 180, "output"),
            ("12", "A4_OUT", 12.7,  0, 180, "output"),
            ("1",  "VDDA",  -12.7, -5.08, 0, "power_in"),
            ("8",  "GNDA",  -12.7, -7.62, 0, "power_in"),
            ("16", "VDDB",   12.7, -5.08, 180, "power_in"),
            ("9",  "GNDB",   12.7, -7.62, 180, "power_in"),
        ],
    },
    "LDO_LT3045": {
        "footprint": "Package_DFN_QFN:DFN-12-1EP_3x3mm_P0.5mm_EP1.65x2.38mm",
        "value": "LT3045",
        "description": "Ultra-low-noise LDO 500mA 0.8uVrms",
        "size": (17.78, 17.78),
        "pins": [
            ("1",  "IN",    -10.16,  7.62, 0, "power_in"),
            ("7",  "OUT",    10.16,  7.62, 180, "power_out"),
            ("5",  "SET",    10.16,  2.54, 180, "input"),
            ("4",  "PROG",  -10.16,  2.54, 0, "input"),
            ("2",  "PG",    -10.16, -2.54, 0, "output"),
            ("3",  "EN/UV", -10.16, -5.08, 0, "input"),
            ("6",  "ILIM",   10.16, -2.54, 180, "input"),
            ("8",  "REF_BYP", 10.16, -5.08, 180, "passive"),
            ("13", "GND",   -10.16, -7.62, 0, "power_in"),
        ],
    },
    "TRANSFORMER_PULSE": {
        "footprint": "Transformer_SMD:Transformer_CoilCraft_LPD3015V_3.0x3.0mm",
        "value": "PULSE_XFMR",
        "description": "Audio digital pulse transformer 1:1",
        "size": (15.24, 10.16),
        "pins": [
            ("1", "P1", -10.16,  2.54, 0, "passive"),
            ("3", "P2", -10.16, -2.54, 0, "passive"),
            ("4", "S1",  10.16,  2.54, 180, "passive"),
            ("6", "S2",  10.16, -2.54, 180, "passive"),
        ],
    },
}


def fmt_symbol(name, spec):
    """Generate a single (symbol ...) S-expression."""
    pins_s = []
    for num, pin_name, x, y, orient, ptype in spec["pins"]:
        pin_s = f'''      (pin {ptype} line (at {x} {y} {orient}) (length 2.54)
        (name "{pin_name}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27))))
      )'''
        pins_s.append(pin_s)

    w, h = spec["size"]
    x1, x2 = -w/2, w/2
    y1, y2 = -h/2, h/2

    pins_block = "\n".join(pins_s)

    return f'''  (symbol "{name}"
    (pin_names (offset 1.016) hide)
    (in_bom yes)
    (on_board yes)
    (property "Reference" "U" (at 0 {h/2 + 2.54} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{spec["value"]}" (at 0 -{h/2 + 2.54} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "{spec["footprint"]}" (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "" (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Description" "{spec["description"]}" (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (symbol "{name}_0_1"
      (rectangle (start {x1} {y1}) (end {x2} {y2})
        (stroke (width 0.254) (type default))
        (fill (type background))
      )
    )
    (symbol "{name}_1_1"
{pins_block}
    )
  )'''


def write_symbol_library():
    SYM_DIR.mkdir(exist_ok=True)
    syms = "\n".join(fmt_symbol(n, s) for n, s in SYMBOLS.items())
    content = f'''(kicad_symbol_lib
  (version 20231120)
  (generator "kicad_symbol_editor")
{syms}
)
'''
    (SYM_DIR / "digital-transport.kicad_sym").write_text(content)


# ---------------------------------------------------------------------------
# Schematic generation
# ---------------------------------------------------------------------------

# Each placed component: (ref, lib_id, x, y, value, pin_to_net_map)
# Position in mm. Will be on an A2 sheet (594x420 mm).
# We connect pins by placing global labels at the pin coordinates.

# Layout grid (top-left origin in KiCad is roughly (0,0); typical A2 sheet)
# We use coarse 50mm grid spacing between blocks.

PLACEMENTS = [
    # ---- Clock domain (top center) ----
    dict(ref="Y1", lib="digital-transport:OCXO_CCHD957",
         x=120, y=80, val="CCHD-957 22.5792MHz",
         nets={"1": "CLK_EN", "2": "GND_CLK", "3": "CLK_44K1", "4": "+5V_CLK"}),
    dict(ref="Y2", lib="digital-transport:OCXO_CCHD957",
         x=120, y=110, val="CCHD-957 24.576MHz",
         nets={"1": "CLK_EN", "2": "GND_CLK", "3": "CLK_48K", "4": "+5V_CLK"}),
    dict(ref="U1", lib="digital-transport:RF_SWITCH_HMC349",
         x=180, y=95, val="HMC349",
         nets={"1": "MCLK_RAW", "2": "CLK_44K1", "3": "CLK_48K",
               "4": "FS_SEL", "5": "+5V_CLK", "6": "GND_CLK"}),
    dict(ref="U2", lib="digital-transport:CLK_BUFFER_ADCLK948",
         x=245, y=95, val="ADCLK948",
         nets={"1": "MCLK_RAW", "2": "GND_CLK",
               "3": "CK_P", "4": "CK_N",
               "5": "MCLK_FPGA_P", "6": "MCLK_FPGA_N",
               "7": "NC_U2_7", "8": "NC_U2_8",
               "9": "+5V_DIG", "10": "GND_DIG"}),

    # ---- Reclock D-FF (center) ----
    dict(ref="U3", lib="digital-transport:DFF_NB7L72M",
         x=245, y=160, val="NB7L72M (RECLOCK)",
         nets={"7": "D_P", "6": "D_N",
               "9": "CK_P", "8": "CK_N",
               "3": "Q_P", "4": "Q_N",
               "2": "+5V_DIG", "1": "GND_DIG"}),

    # ---- CML driver (right of DFF) ----
    dict(ref="U4", lib="digital-transport:CML_DRIVER_SY58025U",
         x=310, y=160, val="SY58025U",
         nets={"1": "Q_P", "2": "Q_N",
               "3": "CML_P", "4": "CML_N",
               "5": "+5V_DRV", "6": "GND_DRV"}),

    # ---- Output transformers (right side) ----
    dict(ref="T1", lib="digital-transport:TRANSFORMER_PULSE",
         x=380, y=140, val="SC916 SPDIF 75R",
         nets={"1": "CML_P", "3": "CML_N",
               "4": "SPDIF_HOT", "6": "GND_CHASSIS"}),
    dict(ref="T2", lib="digital-transport:TRANSFORMER_PULSE",
         x=380, y=180, val="LL1572 AES 110R",
         nets={"1": "CML_P", "3": "CML_N",
               "4": "AES_HOT", "6": "AES_COLD"}),

    # ---- Upstream isolation (left side) ----
    dict(ref="U5", lib="digital-transport:ISOLATOR_Si8645",
         x=160, y=170, val="Si8645BB",
         nets={"2": "SDATA_UPS",  "3": "BCLK_UPS",   "4": "LRCK_UPS",
               "5": "MCLK_FPGA_LVCMOS",
               "15": "D_P", "14": "BCLK_ISO", "13": "LRCK_ISO",
               "12": "MCLK_FPGA_LVCMOS_ISO",
               "1": "+3V3_UPS", "8": "GND_UPS",
               "16": "+3V3_ISO", "9": "GND_ISO"}),

    # ---- Power supplies (bottom) ----
    dict(ref="LDO1", lib="digital-transport:LDO_LT3045",
         x=80, y=250, val="LT3045 → +5V_CLK",
         nets={"1": "+8V_PRE", "7": "+5V_CLK", "5": "LDO1_SET", "4": "LDO1_PROG",
               "2": "LDO1_PG", "3": "+8V_PRE", "6": "LDO1_ILIM",
               "8": "LDO1_REFBYP", "13": "GND_CLK"}),
    dict(ref="LDO2", lib="digital-transport:LDO_LT3045",
         x=160, y=250, val="LT3045 → +5V_DIG",
         nets={"1": "+8V_PRE", "7": "+5V_DIG", "5": "LDO2_SET", "4": "LDO2_PROG",
               "2": "LDO2_PG", "3": "+8V_PRE", "6": "LDO2_ILIM",
               "8": "LDO2_REFBYP", "13": "GND_DIG"}),
    dict(ref="LDO3", lib="digital-transport:LDO_LT3045",
         x=240, y=250, val="LT3045 → +5V_DRV",
         nets={"1": "+8V_PRE", "7": "+5V_DRV", "5": "LDO3_SET", "4": "LDO3_PROG",
               "2": "LDO3_PG", "3": "+8V_PRE", "6": "LDO3_ILIM",
               "8": "LDO3_REFBYP", "13": "GND_DRV"}),
    dict(ref="LDO4", lib="digital-transport:LDO_LT3045",
         x=320, y=250, val="LT3045 → +3V3_ISO",
         nets={"1": "+8V_PRE", "7": "+3V3_ISO", "5": "LDO4_SET", "4": "LDO4_PROG",
               "2": "LDO4_PG", "3": "+8V_PRE", "6": "LDO4_ILIM",
               "8": "LDO4_REFBYP", "13": "GND_ISO"}),
]

# Passive components (R, C) and connectors using stock KiCad symbols
PASSIVES = [
    # LT3045 Rset resistors (Rset = 50k for +5V, 33k for +3.3V; Vout = 100uA * Rset)
    dict(ref="R_S1", lib="Device:R", x=70,  y=235, val="50k 0.1%",  nets={"1": "LDO1_PROG", "2": "GND_CLK"}),
    dict(ref="R_S2", lib="Device:R", x=150, y=235, val="50k 0.1%",  nets={"1": "LDO2_PROG", "2": "GND_DIG"}),
    dict(ref="R_S3", lib="Device:R", x=230, y=235, val="50k 0.1%",  nets={"1": "LDO3_PROG", "2": "GND_DRV"}),
    dict(ref="R_S4", lib="Device:R", x=310, y=235, val="33k 0.1%",  nets={"1": "LDO4_PROG", "2": "GND_ISO"}),

    # LT3045 SET pin reference bypass caps (10nF C0G low leakage)
    dict(ref="C_R1", lib="Device:C", x=95,  y=265, val="10nF C0G", nets={"1": "LDO1_REFBYP", "2": "GND_CLK"}),
    dict(ref="C_R2", lib="Device:C", x=175, y=265, val="10nF C0G", nets={"1": "LDO2_REFBYP", "2": "GND_DIG"}),
    dict(ref="C_R3", lib="Device:C", x=255, y=265, val="10nF C0G", nets={"1": "LDO3_REFBYP", "2": "GND_DRV"}),
    dict(ref="C_R4", lib="Device:C", x=335, y=265, val="10nF C0G", nets={"1": "LDO4_REFBYP", "2": "GND_ISO"}),

    # LDO output bulk caps
    dict(ref="C_O1", lib="Device:C", x=105, y=265, val="22uF X7R", nets={"1": "+5V_CLK", "2": "GND_CLK"}),
    dict(ref="C_O2", lib="Device:C", x=185, y=265, val="22uF X7R", nets={"1": "+5V_DIG", "2": "GND_DIG"}),
    dict(ref="C_O3", lib="Device:C", x=265, y=265, val="22uF X7R", nets={"1": "+5V_DRV", "2": "GND_DRV"}),
    dict(ref="C_O4", lib="Device:C", x=345, y=265, val="10uF X7R", nets={"1": "+3V3_ISO", "2": "GND_ISO"}),

    # OCXO decoupling
    dict(ref="C_Y1", lib="Device:C", x=140, y=75,  val="100nF X7R", nets={"1": "+5V_CLK", "2": "GND_CLK"}),
    dict(ref="C_Y2", lib="Device:C", x=140, y=115, val="100nF X7R", nets={"1": "+5V_CLK", "2": "GND_CLK"}),

    # CK / D LVPECL biasing — DC blocking + bias resistors are integral to LVPECL
    # 100Ω differential termination at U3 inputs
    dict(ref="R_CK_T", lib="Device:R", x=215, y=152, val="100R 0.1%", nets={"1": "CK_P", "2": "CK_N"}),
    dict(ref="R_D_T",  lib="Device:R", x=215, y=165, val="100R 0.1%", nets={"1": "D_P", "2": "D_N"}),
    dict(ref="R_Q_T",  lib="Device:R", x=280, y=160, val="100R 0.1%", nets={"1": "Q_P", "2": "Q_N"}),

    # CML driver biasing/termination
    dict(ref="R_CMLp", lib="Device:R", x=345, y=155, val="50R 0.1%", nets={"1": "CML_P", "2": "+5V_DRV"}),
    dict(ref="R_CMLn", lib="Device:R", x=345, y=165, val="50R 0.1%", nets={"1": "CML_N", "2": "+5V_DRV"}),

    # SPDIF 75Ω termination
    dict(ref="R_SPDIF", lib="Device:R", x=410, y=140, val="75R 0.1%", nets={"1": "SPDIF_HOT", "2": "GND_CHASSIS"}),
    # AES 110Ω termination across the line
    dict(ref="R_AES",   lib="Device:R", x=410, y=180, val="110R 0.1%", nets={"1": "AES_HOT", "2": "AES_COLD"}),

    # Output connectors
    dict(ref="J1", lib="Connector:Conn_Coaxial", x=440, y=140, val="BNC 75R Amphenol B6F",
         nets={"1": "SPDIF_HOT", "2": "GND_CHASSIS"}),

    # XLR-female — we use generic 3-pin connector
    dict(ref="J2", lib="Connector:Conn_01x03_Pin", x=440, y=180, val="XLR-F Neutrik NC3FXX-B",
         nets={"1": "GND_CHASSIS", "2": "AES_HOT", "3": "AES_COLD"}),

    # Power rail entry
    dict(ref="J3", lib="Connector:Conn_01x02_Pin", x=40, y=240, val="+8V_PRE in",
         nets={"1": "+8V_PRE", "2": "GND_PSU"}),

    # Star ground tie
    dict(ref="R_STAR", lib="Device:R", x=400, y=270, val="0R 0805 (star)", nets={"1": "GND_STAR", "2": "GND_CHASSIS"}),
]


def fmt_global_label(net, x, y, orient=0):
    """A global label at (x, y) carrying net name."""
    # KiCad expects a shape: input/output/bidirectional/tri_state/passive
    return f'''  (global_label "{net}" (shape passive) (at {x} {y} {orient})
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid {uid()})
  )'''


def fmt_component(comp):
    """Generate a (symbol ...) instance with property assignments. Connect pins via global labels."""
    ref = comp["ref"]
    lib = comp["lib"]
    x, y = comp["x"], comp["y"]
    val = comp["val"]
    nets = comp["nets"]
    comp_uid = uid()

    # symbol instance
    sym = f'''  (symbol (lib_id "{lib}") (at {x} {y} 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid {comp_uid})
    (property "Reference" "{ref}" (at {x} {y - 12} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{val}" (at {x} {y + 12} 0)
      (effects (font (size 1.27 1.27)))
    )
    (instances
      (project ""
        (path "/{comp_uid}" (reference "{ref}") (unit 1))
      )
    )
  )'''

    # Add a global label near each pin to attach the net name.
    # For custom symbols we know pin coordinates from SYMBOLS dict.
    labels = []
    lib_short = lib.split(":")[1] if ":" in lib else lib
    if lib_short in SYMBOLS:
        pin_coords = {p[0]: (p[2], p[3], p[4]) for p in SYMBOLS[lib_short]["pins"]}
        for pin_num, net in nets.items():
            if pin_num in pin_coords:
                px, py, orient = pin_coords[pin_num]
                # Pin tip position = symbol center + pin offset + pin length (2.54mm)
                if orient == 0:    # extends right
                    tip_x = x + px - 2.54
                    tip_y = y - py
                elif orient == 180:  # extends left
                    tip_x = x + px + 2.54
                    tip_y = y - py
                elif orient == 90:
                    tip_x = x + px
                    tip_y = y - py + 2.54
                else:
                    tip_x = x + px
                    tip_y = y - py - 2.54
                labels.append(fmt_global_label(net, tip_x, tip_y))
    else:
        # For stock symbols (R, C, connectors) use simple offsets
        # We'll just emit labels near the component anchor.
        offset_y = -5
        for pin_num, net in nets.items():
            labels.append(fmt_global_label(net, x, y + offset_y))
            offset_y += 5

    return sym + "\n" + "\n".join(labels)


def write_schematic():
    sheet_uid = uid()

    components_s = "\n".join(fmt_component(c) for c in PLACEMENTS + PASSIVES)

    content = f'''(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (uuid {sheet_uid})
  (paper "A2")
  (title_block
    (title "Digital Transport — Output Stage")
    (date "")
    (rev "v0.1")
    (company "Project: Top-Tier Digital Transport")
    (comment 1 "Master-clock reclock + CML constant-current driver + galvanic isolation")
    (comment 2 "All connections via global labels — rearrange components freely in KiCad")
  )

  (lib_symbols
{generate_lib_symbols_inline()}
  )

{components_s}

  (sheet_instances
    (path "/" (page "1"))
  )
)
'''
    (OUT_DIR / "output-stage.kicad_sch").write_text(content)


def generate_lib_symbols_inline():
    """Inline copies of the custom symbols inside the schematic file
    so the schematic opens without needing the external lib path to be configured."""
    return "\n".join(fmt_symbol_inline(n, s) for n, s in SYMBOLS.items())


def fmt_symbol_inline(name, spec):
    """Same as fmt_symbol but with 'digital-transport:' prefix in the lib id."""
    pins_s = []
    for num, pin_name, x, y, orient, ptype in spec["pins"]:
        pin_s = f'''        (pin {ptype} line (at {x} {y} {orient}) (length 2.54)
          (name "{pin_name}" (effects (font (size 1.27 1.27))))
          (number "{num}" (effects (font (size 1.27 1.27))))
        )'''
        pins_s.append(pin_s)

    w, h = spec["size"]
    x1, x2 = -w/2, w/2
    y1, y2 = -h/2, h/2
    pins_block = "\n".join(pins_s)

    return f'''    (symbol "digital-transport:{name}"
      (pin_names (offset 1.016) hide)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U" (at 0 {h/2 + 2.54} 0))
      (property "Value" "{spec["value"]}" (at 0 -{h/2 + 2.54} 0))
      (property "Footprint" "{spec["footprint"]}" (at 0 0 0) (effects hide))
      (property "Datasheet" "" (at 0 0 0) (effects hide))
      (property "Description" "{spec["description"]}" (at 0 0 0) (effects hide))
      (symbol "{name}_0_1"
        (rectangle (start {x1} {y1}) (end {x2} {y2})
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "{name}_1_1"
{pins_block}
      )
    )'''


def write_project_file():
    """KiCad 8 .kicad_pro JSON."""
    project = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.05,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3
                }
            },
            "layer_presets": [],
            "viewports": []
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {
            "pinned_footprint_libs": [],
            "pinned_symbol_libs": ["digital-transport"]
        },
        "meta": {
            "filename": "output-stage.kicad_pro",
            "version": 1
        },
        "net_settings": {
            "classes": [
                {
                    "name": "Default",
                    "clearance": 0.2,
                    "track_width": 0.25,
                    "via_diameter": 0.6,
                    "via_drill": 0.3
                },
                {
                    "name": "ClockDiff100",
                    "clearance": 0.2,
                    "track_width": 0.18,
                    "diff_pair_gap": 0.18,
                    "diff_pair_width": 0.18,
                    "via_diameter": 0.5,
                    "via_drill": 0.25
                },
                {
                    "name": "SPDIF75",
                    "clearance": 0.3,
                    "track_width": 0.30,
                    "via_diameter": 0.6,
                    "via_drill": 0.3
                },
                {
                    "name": "AES110",
                    "clearance": 0.3,
                    "diff_pair_gap": 0.22,
                    "diff_pair_width": 0.17
                },
                {
                    "name": "Power",
                    "clearance": 0.25,
                    "track_width": 0.5,
                    "via_diameter": 0.8,
                    "via_drill": 0.4
                }
            ]
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "specctra_dsn": "",
                "step": "",
                "vrml": ""
            },
            "page_layout_descr_file": ""
        },
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {
                "dashed_lines_dash_length_ratio": 12.0,
                "dashed_lines_gap_length_ratio": 3.0,
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "default_bus_thickness": 12.0,
                "default_wire_thickness": 6.0,
                "field_names": [],
                "label_size_ratio": 0.375,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15
            },
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "meta": {"version": 1},
            "net_format_name": "",
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_current_sheet_as_root": False,
            "spice_external_command": "spice \"%I\"",
            "spice_model_current_sheet_as_root": True,
            "spice_save_all_currents": False,
            "spice_save_all_voltages": False,
            "subpart_first_id": 65,
            "subpart_id_separator": 0
        },
        "sheets": [["00000000-0000-0000-0000-000000000000", "Root"]],
        "text_variables": {}
    }
    (OUT_DIR / "output-stage.kicad_pro").write_text(json.dumps(project, indent=2))


def write_sym_lib_table():
    """Tells KiCad to load the custom symbol library."""
    content = '''(sym_lib_table
  (lib (name "digital-transport")(type "KiCad")(uri "${KIPRJMOD}/symbols/digital-transport.kicad_sym")(options "")(descr "Custom symbols for digital transport output stage"))
)
'''
    (OUT_DIR / "sym-lib-table").write_text(content)


if __name__ == "__main__":
    write_symbol_library()
    write_schematic()
    write_project_file()
    write_sym_lib_table()
    print("Generated files:")
    for p in sorted(OUT_DIR.rglob("*")):
        if p.is_file() and ".git" not in str(p) and "generate_" not in p.name:
            print(f"  {p.relative_to(OUT_DIR)}")
