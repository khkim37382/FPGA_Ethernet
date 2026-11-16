"""Generate standalone Ethernet Quartus revisions from local N3/vendor sources.

No network access or original sibling repository is used. Re-running this
script deterministically replaces generated Ethernet files only.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VARIANTS = json.loads((HERE / "variants.json").read_text())
VENDOR = HERE / "board/terasic"


def read(path: Path) -> str:
    return path.read_text().replace("\\r\\n", "\n")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def prepare_hps() -> None:
    original = ET.fromstring(read(ROOT / VARIANTS[0]["directory"] / "loan_io.qsys"))
    vendor = ET.fromstring(read(VENDOR / "soc_system.qsys"))
    old_hps = original.find("module[@name='hps_0']")
    hps = deepcopy(vendor.find("module[@name='hps_0']"))
    hps.set("version", old_hps.get("version"))
    old_params = {p.get("name"): p for p in old_hps.findall("parameter")}
    # Keep the vendor board's complete memory/pin/clock preset, while exposing
    # only the lightweight HPS master needed here. No orphan fabric inputs.
    fabric_only = {"S2F_Width", "F2S_Width", "F2SDRAM_Type", "F2SDRAM_Width",
                   "F2SINTERRUPT_Enable", "STM_Enable", "F2SCLK_COLDRST_Enable",
                   "F2SCLK_WARMRST_Enable", "F2SCLK_DBGRST_Enable"}
    for parameter in hps.findall("parameter"):
        name = parameter.get("name")
        if name in fabric_only:
            replacement = old_params[name]
            parameter.attrib.clear()
            parameter.attrib.update(replacement.attrib)
            parameter.text = replacement.text
    original.remove(old_hps)
    original.append(hps)
    for interface in list(original.findall("interface")):
        if interface.get("name") == "loan_io":
            original.remove(interface)
    ET.SubElement(original, "interface", name="hps_reset", internal="hps_0.h2f_reset",
                  type="reset", dir="start")
    ET.SubElement(original, "interface", name="n3_records", internal="n3_bridge.records",
                  type="conduit", dir="end")
    ET.SubElement(original, "module", name="n3_bridge", kind="n3_ethernet_bridge",
                  version="1.0", enabled="1")
    for kind, start, end in [
        ("clock", "clk_0.clk", "n3_bridge.clock"),
        ("reset", "clk_0.clk_reset", "n3_bridge.reset"),
        ("reset", "hps_0.h2f_reset", "n3_bridge.reset"),
    ]:
        ET.SubElement(original, "connection", kind=kind, version="23.1", start=start, end=end)
    bus = ET.SubElement(original, "connection", kind="avalon", version="23.1",
                        start="hps_0.h2f_lw_axi_master", end="n3_bridge.avs")
    for name, value in (("baseAddress", "0x00010000"), ("arbitrationPriority", "1"),
                        ("defaultConnection", "false")):
        ET.SubElement(bus, "parameter", name=name, value=value)
    for parameter in original.findall("parameter"):
        if parameter.get("name") == "projectName":
            parameter.set("value", "N3_Ethernet.qpf")
        if parameter.get("name") in {"generationId", "systemHash"}:
            parameter.set("value", "0")
    ET.indent(original, space=" ")
    write(HERE / "board/n3_hps.qsys", '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(original, encoding="unicode") + "\n")


def hps_connections(producer: str) -> str:
    reference = read(VENDOR / "DE10_Standard_GHRD.v")
    pairs = re.findall(r"\.(\w+)\s*\(\s*(HPS_\w+(?:\[\d+\])?)\s*\)", reference)
    ports = [(name.replace("hps_0_hps_io_", "hps_io_"), signal)
             for name, signal in pairs if name.startswith(("memory_", "hps_0_hps_io_"))]
    ports[:0] = [("clk_clk", "CLOCK_50"), ("reset_reset_n", "KEY[0]"),
                 ("hps_reset_reset_n", "hps_fpga_reset_n")]
    for source, prefix in (("counter", producer), ("ivt", "ivt"),
                           ("sram0", "sram0"), ("sram1", "sram1")):
        data = f"sram_data{source[-1]}" if source.startswith("sram") else f"{prefix}_data"
        ready = f"sram_xmit_ready{source[-1]}" if source.startswith("sram") else f"{prefix}_xmit_ready"
        ack = f"sram_xmit_ack{source[-1]}" if source.startswith("sram") else f"{prefix}_xmit_ack"
        ports.extend([(f"n3_records_{source}_data", data),
                      (f"n3_records_{source}_ready", ready), (f"n3_records_{source}_ack", ack)])
    assert len({name for name, _ in ports}) == len(ports)
    return "n3_hps u0 (\n" + ",\n".join(f"    .{name}({signal})" for name, signal in ports) + "\n);\n"


def prepare_top(variant: dict) -> None:
    directory = ROOT / variant["directory"]
    text = read(directory / "DE10_TOP.v")
    text = text.replace("//`define ENABLE_HPS", "`define ENABLE_HPS")
    # The legacy tail duplicates the UART and declares an incompatible x8
    # memory bus. Use the complete HPS port group already in the Terasic top.
    start = text.index("      inout [7:0] memory_mem_dq")
    end = text.index(");", start)
    text = text[:start] + text[end:]
    text = re.sub(r"\s*///////// IR /////////.*?input\s+IRDA_RXD,", "", text, flags=re.S)
    text = re.sub(r"(output\s+HPS_USB_STP),", r"\1", text)
    start = text.index("wire uart_tx;")
    end = text.index("//  Structural coding", start)
    end = text.index("\n", end) + 1
    end = text.index("\n", end) + 1
    reset = '''// Reset acquisition and the HPS bridge together. Assert asynchronously;
// release on CLOCK_50 after the HPS has released its FPGA reset.
wire hps_fpga_reset_n;
wire raw_reset_n = KEY[0] & hps_fpga_reset_n;
(* ASYNC_REG = "TRUE" *) reg [1:0] reset_release = 2'b00;
always @(posedge CLOCK_50 or negedge raw_reset_n)
    if (!raw_reset_n) reset_release <= 2'b00;
    else reset_release <= {reset_release[0], 1'b1};
wire n3_reset_n = reset_release[1];

'''
    text = text[:start] + reset + hps_connections(variant["producer"]) + text[end:]
    start = text.index("xmit_mux serial_xmit")
    end = text.index("endmodule", start)
    clock_start = text.index("Clock2_5MHz slow_clock", start)
    clock_end = text.index("singlepulse pulse1", clock_start)
    # LSB uses clk2_5 to drive the external DUT's PISO clock. Preserve this
    # board clock even though the new SRAM FSMs use synchronous clock enables.
    clock = text[clock_start:clock_end]
    text = text[:start] + "// Complete records are buffered by n3_hps; UART mux is not instantiated.\n\n" + clock + text[end:]
    text = text.replace(".reset(KEY[0])", ".reset(n3_reset_n)")
    text = text.replace(".reset(KEY[1])", ".reset(KEY[1] & n3_reset_n)")
    text = text.replace("wire [160-1:0] counter;", "wire [59:0] counter;")
    text = text.replace(".enable(1)", ".enable(1'b1)")
    if not re.search(r"wire\s+SRAM1_status\s*;", text):
        text = text.replace("wire [1:0] SRAM_data_select;", "wire [1:0] SRAM_data_select;\nwire SRAM1_status;")
    # Verilog string literals are ASCII vectors, not VHDL bit strings. The
    # legacy \"1\" was 8'h31 and width truncation depended on the generic.
    for bits in ("0000", "0001", "0000000", "1"):
        text = text.replace(f'("{bits}")', f"({len(bits)}'b{bits})")
    text = "// Generated by ethernet/prepare_projects.py; edit the generator/source variant.\n" + text
    write(directory / "DE10_TOP_Ethernet.v", text)


def repair_sram_addressing(text: str, puf: bool) -> str:
    if not puf:
        # An N-bit address cannot reach 2**N. Use its representable last
        # address and enter the existing waiting state between complete scans.
        text = text.replace("addr >= 2**num_addrbits", "addr = to_unsigned(2**num_addrbits-1, num_addrbits)")
        text = text.replace("to_unsigned(2**num_addrbits, num_addrbits)", "to_unsigned(2**num_addrbits-1, num_addrbits)")
        text = text.replace("waitcount > waitlimit", "waitcount >= waitlimit")
        text = text.replace("waitcount <= waitcount + 1;", "if waitcount < waitlimit then waitcount <= waitcount + 1; end if;")
    return text


def prepare_sram(variant: dict) -> str:
    """Preserve the /21 FSM cadence using a CLOCK_50 clock enable.

    The original divider first rises on edge 11 and repeats every 21 edges.
    This removes the derived-clock ready/ack crossing at the Ethernet boundary.
    """
    text = repair_sram_addressing(read(ROOT / variant["source_directory"] / "SRAM_main.vhd"), variant["puf"])
    if variant["puf"]:
        # PUF waits on an external trigger, not waitcount. The unused timer
        # otherwise overflows while waiting for the next acquisition.
        text = text.replace("waitcount <= waitcount + 1;", "null; -- PUF waits on sram_trigger_latch, not a free-running timer")
    text, count = re.subn(r"\s*clockdown\s*:\s*Clock2_5MHz\s+port map\s*\(.*?\);", "", text, count=1, flags=re.I | re.S)
    assert count == 1
    text = text.replace("signal slow_clock : std_logic;", "signal slow_tick : std_logic;\n    signal divider_count : integer range 0 to 20 := 0;")
    text = text.replace("process (slow_clock, reset)", "process (sys_clk, reset)")
    text = text.replace("elsif (rising_edge(slow_clock)) then", "elsif rising_edge(sys_clk) then\n            if slow_tick = '1' then")
    # The first process using this slow clock ends immediately before any
    # later trigger or output processes. Close the new clock-enable condition.
    fsm_start = text.index("process (sys_clk, reset)")
    end = re.search(r"end process\s*;", text[fsm_start:], flags=re.I)
    assert end
    position = fsm_start + end.start()
    # Existing end if closes the reset/clock condition. Insert an additional
    # end if before it so this remains valid for the original source layout.
    previous = text.rfind("end if", fsm_start, position)
    text = text[:previous] + "end if; -- slow_tick clock enable\n        " + text[previous:]
    divider = '''
    -- Equivalent to Clock2_5MHz's original 21-cycle divider, without a new clock.
    slow_tick <= '1' when divider_count = 10 else '0';
    process(sys_clk)
    begin
        if rising_edge(sys_clk) then
            if divider_count = 20 then divider_count <= 0;
            else divider_count <= divider_count + 1;
            end if;
        end if;
    end process;
'''
    begin = re.search(r"\bbegin\b", text, flags=re.I).end()
    text = text[:begin] + divider + text[begin:]
    target = HERE / "acquisition" / variant["name"] / "SRAM_main.vhd"
    write(target, "-- Generated Ethernet acquisition variant; cadence checked against the original.\n" + text)
    return f"../../ethernet/acquisition/{variant['name']}/SRAM_main.vhd"


def prepare_compatibility_sources(variant: dict) -> dict[str, str]:
    """Keep portability/reset fixes isolated from the upstream source files."""
    outputs = {}
    names = ["i2c_master.vhd", "powerdata.vhd"]
    if variant["producer"] == "lsb":
        names += ["main_controller.vhd", "count_12bit.vhd"]
    for name in names:
        text = read(ROOT / variant["source_directory"] / name)
        if name == "i2c_master.vhd":
            # Generic-dependent case choices are accepted by Quartus, but
            # not locally static in standard VHDL. Equivalent comparisons
            # are portable and keep the exact quarter-cycle timing.
            start = text.index("CASE count IS")
            end = text.index("END CASE;", start) + len("END CASE;")
            section = text[start:end]
            section = section.replace("CASE count IS", "IF count < divider THEN")
            section = re.sub(r"WHEN 0 TO divider-1 =>", "", section)
            section = re.sub(r"WHEN divider TO divider\*2-1 =>", "ELSIF count < divider*2 THEN", section)
            section = re.sub(r"WHEN divider\*2 TO divider\*3-1 =>", "ELSIF count < divider*3 THEN", section)
            section = section.replace("WHEN OTHERS =>", "ELSE").replace("END CASE;", "END IF;")
            text = text[:start] + section + text[end:]
        elif name == "powerdata.vhd":
            # Reset during transmission must not leave a pending stale word.
            text, count = re.subn(r"(if\s*\(rising_edge\(clk\)\)\s*then)",
                                  r"\1\n    if reset = '0' then\n        state <= rst;\n        out_ready <= '0';\n        wait_cnt <= 0;\n        ena <= '0';\n    else", text, count=1, flags=re.I)
            assert count == 1
            last_case = list(re.finditer(r"end case\s*;", text, flags=re.I))[-1].end()
            text = text[:last_case] + "\n    end if; -- synchronous reset" + text[last_case:]
        elif name == "main_controller.vhd":
            # A constrained counter cannot exceed its upper bound. Reaching
            # the limit should trigger the original periodic acquisition.
            text = text.replace("delay_time > delay_val", "delay_time >= delay_val")
            text = text.replace("state <= reset_state;", "state <= reset_state;\n                xmit_index := 0;")
        elif name == "count_12bit.vhd":
            # The shipped SharedFiles entity has an integer Q, while its
            # actual lsb_counter component requires a 12-bit vector. Match
            # that interface and make hardware modulo-4096 overflow explicit.
            text = '''library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;
entity count_12bit is
    port(clk, reset, enable : in std_logic;
         q : out std_logic_vector(NUM_COUNTER_BITS-1 downto 0));
end entity;
architecture rtl of count_12bit is
    signal count : unsigned(NUM_COUNTER_BITS-1 downto 0) := (others => '0');
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if reset = '0' then count <= (others => '0');
            elsif enable = '1' then count <= count + 1;
            end if;
        end if;
    end process;
    q <= std_logic_vector(count);
end architecture;
'''
        write(HERE / "acquisition" / variant["name"] / name,
              "-- Generated Ethernet compatibility/reset fixes; see prepare_projects.py.\n" + text)
        outputs[name] = f"../../ethernet/acquisition/{variant['name']}/{name}"
    return outputs


def prepare_qsf(variant: dict, sram_path: str) -> None:
    directory = ROOT / variant["directory"]
    text = read(directory / f"{variant['original_revision']}.qsf")
    lines = []
    for line in text.splitlines():
        if re.search(r"-name (?:VHDL_FILE|VERILOG_FILE|SYSTEMVERILOG_FILE|QIP_FILE|SDC_FILE|IP_SEARCH_PATHS|PROJECT_OUTPUT_DIRECTORY|VHDL_INPUT_VERSION)\b", line):
            continue
        if any(word in line for word in ("memory_mem_", "memory_oct_", "HPS_", "__hps_sdram")):
            continue
        lines.append(line)
    lines.extend(line for line in read(VENDOR / "DE10_Standard_GHRD.qsf").splitlines()
                 if re.search(r"-to HPS_", line))
    source_dir = Path("..") / Path(variant["source_directory"]).name
    common = ["my_arrays.vhd", "i2c_master.vhd", "powerdata.vhd", "Clock2_5MHz.vhd"]
    if variant["producer"] == "lsb":
        common += ["main_controller.vhd", "count_12bit.vhd", "lsb_counter.vhd", "lsb_main.vhd"]
    else:
        common += ["ffmcu_trigger_clk.vhd", "ffmcu_controller.vhd", "ffmcu_main.vhd"]
    lines += ["", "# Standalone Ethernet revision: local N3 sources and common HPS board system.",
              "set_global_assignment -name VHDL_INPUT_VERSION VHDL_2008",
              'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY "output_files/ethernet"',
              'set_global_assignment -name IP_SEARCH_PATHS "../../ethernet/rtl/**/*"',
              'set_global_assignment -name VERILOG_FILE DE10_TOP_Ethernet.v']
    compatibility = prepare_compatibility_sources(variant)
    lines += [f"set_global_assignment -name VHDL_FILE {compatibility.get(name, str(source_dir / name))}" for name in common]
    lines += [f"set_global_assignment -name VHDL_FILE {sram_path}",
              "set_global_assignment -name QIP_FILE ../../ethernet/board/n3_hps/synthesis/n3_hps.qip",
              "set_global_assignment -name SDC_FILE N3_Ethernet.sdc"]
    write(directory / "N3_Ethernet.qsf", "\n".join(lines) + "\n")
    write(directory / "N3_Ethernet.qpf", 'QUARTUS_VERSION = "23.1"\nPROJECT_REVISION = "N3_Ethernet"\n')
    sdc = 'source ../../ethernet/board/n3_ethernet.sdc\n'
    if variant["producer"] == "lsb":
        sdc += '# Original /21 DUT PISO clock: 11 cycles high, 10 low.\ncreate_generated_clock -name dut_piso -source [get_ports {CLOCK_50}] -edges {21 43 63} [get_ports {HSMC_RX_D_P[7]}]\n'
    write(directory / "N3_Ethernet.sdc", sdc)
    write(directory / "ETHERNET_REVISION.txt", "Open N3_Ethernet.qpf. Read ../../ethernet/README.md. Regenerate ethernet/board/n3_hps before compilation.\n")


def main() -> None:
    prepare_hps()
    for variant in VARIANTS:
        prepare_top(variant)
        prepare_qsf(variant, prepare_sram(variant))
        print(f"Prepared {variant['name']}/N3_Ethernet.qpf")


if __name__ == "__main__":
    main()
