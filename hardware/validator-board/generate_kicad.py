#!/usr/bin/env python3
"""
KiCad 8 generator for the Output Stage Core Validator (OSCV) board.

This is a minimal 5cm x 8cm board containing just the elements needed to
validate the two core hypotheses:
  A) Master-clock reclock removes upstream jitter
  B) CML constant-current driver decouples output from data content

Components (subset of full output stage):
  - 1× OCXO (CCHD-957 22.5792 MHz)
  - 1× NB7L72M reclock D-FF
  - 1× SY58025U CML driver
  - 1× SC916 pulse transformer
  - 1× BNC output
  - 3× LT3045 LDOs (CLK / DIG / DRV rails)
  - 1× LM317 pre-regulator
  - 1× STM32G031 MCU (PRBS test source)
  - 7× SMA test points
  - Battery / DC input
"""

import json
import sys
import uuid
from pathlib import Path

# Reuse the symbol definitions from the main output-stage generator by
# importing the SYMBOLS dict.
sys.path.insert(0, str(Path(__file__).parent.parent / "output-stage"))
from generate_kicad import (  # type: ignore  # noqa: E402
    SYMBOLS,
    fmt_symbol_inline,
    fmt_global_label,
    uid,
)

OUT_DIR = Path(__file__).parent
SYM_DIR = OUT_DIR / "symbols"

# Component placements for the validator board.
# A2 sheet so labels have room. Components grouped by function.
PLACEMENTS = [
    # ---- Clock source ----
    dict(ref="Y1", lib="digital-transport:OCXO_CCHD957",
         x=120, y=80, val="CCHD-957 22.5792MHz",
         nets={"1": "CLK_EN", "2": "GND_CLK", "3": "MCLK", "4": "+5V_CLK"}),

    # ---- Reclock D-FF ----
    dict(ref="U3", lib="digital-transport:DFF_NB7L72M",
         x=200, y=120, val="NB7L72M (RECLOCK)",
         nets={"7": "D_P", "6": "D_N",
               "9": "MCLK", "8": "MCLK_N",
               "3": "Q_P", "4": "Q_N",
               "2": "+5V_DIG", "1": "GND_DIG"}),

    # ---- CML driver ----
    dict(ref="U4", lib="digital-transport:CML_DRIVER_SY58025U",
         x=265, y=120, val="SY58025U",
         nets={"1": "Q_P", "2": "Q_N",
               "3": "CML_P", "4": "CML_N",
               "5": "+5V_DRV", "6": "GND_DRV"}),

    # ---- Output transformer ----
    dict(ref="T1", lib="digital-transport:TRANSFORMER_PULSE",
         x=325, y=120, val="SC916 SPDIF 75R",
         nets={"1": "CML_P", "3": "CML_N",
               "4": "SPDIF_HOT", "6": "GND_CHASSIS"}),

    # ---- Power supplies (3 rails) ----
    dict(ref="LDO1", lib="digital-transport:LDO_LT3045",
         x=80, y=200, val="LT3045 → +5V_CLK",
         nets={"1": "+6V_PRE", "7": "+5V_CLK", "5": "LDO1_SET", "4": "LDO1_PROG",
               "2": "LDO1_PG", "3": "+6V_PRE", "6": "LDO1_ILIM",
               "8": "LDO1_REFBYP", "13": "GND_CLK"}),
    dict(ref="LDO2", lib="digital-transport:LDO_LT3045",
         x=160, y=200, val="LT3045 → +5V_DIG",
         nets={"1": "+6V_PRE", "7": "+5V_DIG", "5": "LDO2_SET", "4": "LDO2_PROG",
               "2": "LDO2_PG", "3": "+6V_PRE", "6": "LDO2_ILIM",
               "8": "LDO2_REFBYP", "13": "GND_DIG"}),
    dict(ref="LDO3", lib="digital-transport:LDO_LT3045",
         x=240, y=200, val="LT3045 → +5V_DRV",
         nets={"1": "+6V_PRE", "7": "+5V_DRV", "5": "LDO3_SET", "4": "LDO3_PROG",
               "2": "LDO3_PG", "3": "+6V_PRE", "6": "LDO3_ILIM",
               "8": "LDO3_REFBYP", "13": "GND_DRV"}),
]

# All net labels also need a position. We will additionally place global
# labels at each pin tip using the same approach as the main schematic.

# Stock-symbol components: resistors, caps, connectors, MCU, regulator.
PASSIVES = [
    # LM317 pre-regulator
    dict(ref="U_PRE", lib="Regulator_Linear:LM317_TO-220", x=40, y=200, val="LM317 → +6V",
         nets={"1": "LM317_ADJ", "2": "+6V_PRE", "3": "VIN_RAW"}),
    dict(ref="R_LM_top", lib="Device:R", x=30, y=220, val="240R 1%",
         nets={"1": "+6V_PRE", "2": "LM317_ADJ"}),
    dict(ref="R_LM_bot", lib="Device:R", x=30, y=235, val="910R 1%",
         nets={"1": "LM317_ADJ", "2": "GND_PSU"}),
    dict(ref="C_LM_in",  lib="Device:C", x=20, y=205, val="10uF X7R",
         nets={"1": "VIN_RAW", "2": "GND_PSU"}),
    dict(ref="C_LM_out", lib="Device:C", x=55, y=205, val="10uF X7R",
         nets={"1": "+6V_PRE", "2": "GND_PSU"}),

    # LT3045 set resistors (Vout = 100uA * Rset; 50k → 5V)
    dict(ref="R_S1", lib="Device:R", x=70,  y=215, val="50k 0.1%", nets={"1": "LDO1_PROG", "2": "GND_CLK"}),
    dict(ref="R_S2", lib="Device:R", x=150, y=215, val="50k 0.1%", nets={"1": "LDO2_PROG", "2": "GND_DIG"}),
    dict(ref="R_S3", lib="Device:R", x=230, y=215, val="50k 0.1%", nets={"1": "LDO3_PROG", "2": "GND_DRV"}),

    # LT3045 reference bypass (low-leak C0G)
    dict(ref="C_R1", lib="Device:C", x=95,  y=225, val="10nF C0G", nets={"1": "LDO1_REFBYP", "2": "GND_CLK"}),
    dict(ref="C_R2", lib="Device:C", x=175, y=225, val="10nF C0G", nets={"1": "LDO2_REFBYP", "2": "GND_DIG"}),
    dict(ref="C_R3", lib="Device:C", x=255, y=225, val="10nF C0G", nets={"1": "LDO3_REFBYP", "2": "GND_DRV"}),

    # LT3045 output caps
    dict(ref="C_O1", lib="Device:C", x=105, y=225, val="22uF X7R", nets={"1": "+5V_CLK", "2": "GND_CLK"}),
    dict(ref="C_O2", lib="Device:C", x=185, y=225, val="22uF X7R", nets={"1": "+5V_DIG", "2": "GND_DIG"}),
    dict(ref="C_O3", lib="Device:C", x=265, y=225, val="22uF X7R", nets={"1": "+5V_DRV", "2": "GND_DRV"}),

    # OCXO local decoupling
    dict(ref="C_Y1a", lib="Device:C", x=135, y=70, val="100nF X7R", nets={"1": "+5V_CLK", "2": "GND_CLK"}),
    dict(ref="C_Y1b", lib="Device:C", x=145, y=70, val="1nF C0G",   nets={"1": "+5V_CLK", "2": "GND_CLK"}),
    dict(ref="R_Y1_VCC", lib="Device:R", x=125, y=70, val="10R 1%", nets={"1": "+5V_CLK", "2": "+5V_CLK_OCXO"}),

    # OCXO output damping resistor (22Ohm) feeding CK and TP_CK
    dict(ref="R_CK_S", lib="Device:R", x=165, y=80, val="22R 1%", nets={"1": "MCLK", "2": "MCLK_S"}),

    # 100Ohm differential terminations
    dict(ref="R_D_T", lib="Device:R", x=180, y=125, val="100R 0.1% (D term)", nets={"1": "D_P", "2": "D_N"}),
    dict(ref="R_Q_T", lib="Device:R", x=235, y=120, val="100R 0.1% (Q term)", nets={"1": "Q_P", "2": "Q_N"}),
    dict(ref="R_CK_T", lib="Device:R", x=185, y=115, val="100R 0.1% (CK term)", nets={"1": "MCLK", "2": "MCLK_N"}),

    # CML bias pullups to VCC_DRV
    dict(ref="R_CMLp", lib="Device:R", x=295, y=115, val="50R 1%", nets={"1": "CML_P", "2": "+5V_DRV"}),
    dict(ref="R_CMLn", lib="Device:R", x=295, y=125, val="50R 1%", nets={"1": "CML_N", "2": "+5V_DRV"}),

    # SPDIF output termination + BNC
    dict(ref="R_SPDIF", lib="Device:R", x=350, y=120, val="75R 0.1%", nets={"1": "SPDIF_HOT", "2": "GND_CHASSIS"}),
    dict(ref="J_BNC",  lib="Connector:Conn_Coaxial", x=380, y=120, val="BNC 75R out",
         nets={"1": "SPDIF_HOT", "2": "GND_CHASSIS"}),

    # Star ground tie
    dict(ref="R_STAR", lib="Device:R", x=355, y=240, val="10R 0805 star", nets={"1": "GND_STAR", "2": "GND_CHASSIS"}),

    # DC input header (battery or DC jack)
    dict(ref="J_PWR", lib="Connector:Conn_01x02_Pin", x=20, y=185, val="+7V to +12V in",
         nets={"1": "VIN_RAW", "2": "GND_PSU"}),

    # Test SMA points
    dict(ref="J_SMA1", lib="Connector:Conn_Coaxial", x=40, y=40,  val="SMA: D_EXT",
         nets={"1": "D_EXT", "2": "GND_DIG"}),
    dict(ref="J_SMA2", lib="Connector:Conn_Coaxial", x=80, y=40,  val="SMA: TP_CK",
         nets={"1": "MCLK_S", "2": "GND_CLK"}),
    dict(ref="J_SMA3", lib="Connector:Conn_Coaxial", x=120, y=40, val="SMA: TP_DIN",
         nets={"1": "D_P", "2": "GND_DIG"}),
    dict(ref="J_SMA4", lib="Connector:Conn_Coaxial", x=160, y=40, val="SMA: TP_QOUT",
         nets={"1": "Q_P", "2": "GND_DIG"}),
    dict(ref="J_SMA5", lib="Connector:Conn_Coaxial", x=200, y=40, val="SMA: TP_CMLP",
         nets={"1": "CML_P", "2": "GND_DRV"}),
    dict(ref="J_SMA6", lib="Connector:Conn_Coaxial", x=240, y=40, val="SMA: TP_VCC_CLK",
         nets={"1": "+5V_CLK", "2": "GND_CLK"}),
    dict(ref="J_SMA7", lib="Connector:Conn_Coaxial", x=280, y=40, val="SMA: TP_VCC_DRV",
         nets={"1": "+5V_DRV", "2": "GND_DRV"}),

    # 1kΩ scope-probe isolation resistors (placed between probe taps and SMA)
    dict(ref="R_SMA2", lib="Device:R", x=80, y=55,  val="1k 1%", nets={"1": "MCLK", "2": "MCLK_S"}),
    dict(ref="R_SMA3", lib="Device:R", x=120, y=55, val="1k 1%", nets={"1": "D_P", "2": "D_P_TP"}),
    dict(ref="R_SMA4", lib="Device:R", x=160, y=55, val="1k 1%", nets={"1": "Q_P", "2": "Q_P_TP"}),
    dict(ref="R_SMA5", lib="Device:R", x=200, y=55, val="1k 1%", nets={"1": "CML_P", "2": "CML_P_TP"}),

    # PRBS source MCU (STM32G031F8P6) — minimal pinout for test only
    dict(ref="U_M",  lib="Connector:Conn_01x04_Pin", x=20, y=120, val="STM32G031 (PRBS)",
         nets={"1": "+3V3_MCU", "2": "GND_DIG", "3": "PRBS_OUT_P", "4": "PRBS_OUT_N"}),

    # Mode select jumper (3-position) — selects D source for D-FF
    dict(ref="JP_D",  lib="Connector:Conn_01x06_Pin", x=140, y=145, val="D source select",
         nets={"1": "D_EXT",      "2": "D_P",
               "3": "MCLK_DIV",   "4": "D_P",
               "5": "PRBS_OUT_P", "6": "D_P"}),
    dict(ref="JP_DN", lib="Connector:Conn_01x06_Pin", x=140, y=155, val="D# source select",
         nets={"1": "GND_DIG",    "2": "D_N",
               "3": "MCLK_DIV_N", "4": "D_N",
               "5": "PRBS_OUT_N", "6": "D_N"}),

    # Divider tap (will be implemented inside U_M for simplicity; this header
    # exposes a divided clock if a logic divider chip is added later)
    dict(ref="JP_DIV", lib="Connector:Conn_01x02_Pin", x=80, y=120, val="MCLK ÷2 tap",
         nets={"1": "MCLK_DIV", "2": "MCLK"}),
]


def fmt_component(comp):
    ref = comp["ref"]
    lib = comp["lib"]
    x, y = comp["x"], comp["y"]
    val = comp["val"]
    nets = comp["nets"]
    comp_uid = uid()

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

    labels = []
    lib_short = lib.split(":")[1] if ":" in lib else lib
    if lib_short in SYMBOLS:
        pin_coords = {p[0]: (p[2], p[3], p[4]) for p in SYMBOLS[lib_short]["pins"]}
        for pin_num, net in nets.items():
            if pin_num in pin_coords:
                px, py, orient = pin_coords[pin_num]
                if orient == 0:
                    tip_x = x + px - 2.54
                    tip_y = y - py
                elif orient == 180:
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
        offset_y = -5
        for pin_num, net in nets.items():
            labels.append(fmt_global_label(net, x, y + offset_y))
            offset_y += 5
    return sym + "\n" + "\n".join(labels)


def generate_lib_symbols_inline():
    # Only inline the symbols we actually use on this board.
    used = {"OCXO_CCHD957", "DFF_NB7L72M", "CML_DRIVER_SY58025U",
            "TRANSFORMER_PULSE", "LDO_LT3045"}
    return "\n".join(fmt_symbol_inline(n, SYMBOLS[n]) for n in used if n in SYMBOLS)


def write_symbol_library():
    SYM_DIR.mkdir(exist_ok=True)
    used = {"OCXO_CCHD957", "DFF_NB7L72M", "CML_DRIVER_SY58025U",
            "TRANSFORMER_PULSE", "LDO_LT3045"}
    from generate_kicad import fmt_symbol  # type: ignore
    syms = "\n".join(fmt_symbol(n, SYMBOLS[n]) for n in used if n in SYMBOLS)
    content = f'''(kicad_symbol_lib
  (version 20231120)
  (generator "kicad_symbol_editor")
{syms}
)
'''
    (SYM_DIR / "digital-transport.kicad_sym").write_text(content)


def write_schematic():
    sheet_uid = uid()
    components_s = "\n".join(fmt_component(c) for c in PLACEMENTS + PASSIVES)
    content = f'''(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (uuid {sheet_uid})
  (paper "A3")
  (title_block
    (title "Output Stage Core Validator (OSCV)")
    (date "")
    (rev "v0.1")
    (company "Top-Tier Digital Transport — Validation Board")
    (comment 1 "5cm x 8cm subset of the output stage for jitter / decoupling validation")
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
    (OUT_DIR / "validator-board.kicad_sch").write_text(content)


def write_project_file():
    project = {
        "board": {"design_settings": {}, "layer_presets": [], "viewports": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": ["digital-transport"]},
        "meta": {"filename": "validator-board.kicad_pro", "version": 1},
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": 0.2, "track_width": 0.25,
                 "via_diameter": 0.6, "via_drill": 0.3},
                {"name": "ClockDiff100", "clearance": 0.2, "track_width": 0.18,
                 "diff_pair_gap": 0.18, "diff_pair_width": 0.18,
                 "via_diameter": 0.5, "via_drill": 0.25},
                {"name": "SPDIF75", "clearance": 0.3, "track_width": 0.30,
                 "via_diameter": 0.6, "via_drill": 0.3},
                {"name": "Power", "clearance": 0.25, "track_width": 0.5,
                 "via_diameter": 0.8, "via_drill": 0.4},
            ]
        },
        "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "",
                                  "specctra_dsn": "", "step": "", "vrml": ""},
                   "page_layout_descr_file": ""},
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {"dashed_lines_dash_length_ratio": 12.0,
                        "dashed_lines_gap_length_ratio": 3.0,
                        "default_line_thickness": 6.0,
                        "default_text_size": 50.0,
                        "default_bus_thickness": 12.0,
                        "default_wire_thickness": 6.0,
                        "field_names": [],
                        "label_size_ratio": 0.375,
                        "pin_symbol_size": 25.0,
                        "text_offset_ratio": 0.15},
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
    (OUT_DIR / "validator-board.kicad_pro").write_text(json.dumps(project, indent=2))


def write_sym_lib_table():
    content = '''(sym_lib_table
  (lib (name "digital-transport")(type "KiCad")(uri "${KIPRJMOD}/symbols/digital-transport.kicad_sym")(options "")(descr "Custom symbols for digital transport"))
)
'''
    (OUT_DIR / "sym-lib-table").write_text(content)


if __name__ == "__main__":
    write_symbol_library()
    write_schematic()
    write_project_file()
    write_sym_lib_table()
    print("Generated validator board files:")
    for p in sorted(OUT_DIR.rglob("*")):
        if p.is_file() and ".git" not in str(p) and "generate_" not in p.name:
            print(f"  {p.relative_to(OUT_DIR)}")
