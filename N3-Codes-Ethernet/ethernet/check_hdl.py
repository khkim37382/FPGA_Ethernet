"""Analyze/synthesize real VHDL and check all Ethernet top-level connections.

Requires GHDL with synthesis support and Verilator. Intel's HPS is represented
by its sourced port contract for structural lint only, never by a functional
Ethernet/DDR model. This does not replace Quartus generation, fitting or STA.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from prepare_projects import repair_sram_addressing

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FLAGS = ["--std=08", "-fsynopsys", "-frelaxed-rules"]


def run(command, work, label, output=None):
    result = subprocess.run([str(x) for x in command], cwd=work, capture_output=True, text=True)
    (work / (label + ".log")).write_text("$ " + " ".join(str(x) for x in command) + "\n" + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{label} failed:\n{result.stderr[-6000:]}\n{result.stdout[-1000:]}")
    if output:
        output.write_text(result.stdout)
    return result.stdout


def entity_ports(source):
    text = re.sub(r"--[^\n]*", "", source)
    start = re.search(r"\bport\s*\(", text, re.I).end()
    depth = 1
    end = start
    while depth:
        if text[end] == "(": depth += 1
        if text[end] == ")": depth -= 1
        end += 1
    declaration = text[start:end-1]
    names = []
    for item in declaration.split(";"):
        if item.strip():
            names += [name.strip() for name in item.split(":", 1)[0].split(",")]
    return declaration, names


def sram_wrapper(variant, index, original_source):
    ports, names = entity_ports(original_source)
    puf = variant["puf"]
    generics = {
        "num_addrbits": str(variant[f"sram{index}_address_bits"]),
        "num_databits": str(variant[f"sram{index}_data_bits"]),
        "num_rmbits": "7" if variant["name"].startswith("Zeus") and index == 0 else "5",
        "waitlimit": "5000000", "sram_number": f'"000{index}"',
        "read_margin": '"0000000"',
        "am_i_tcam": '"1"' if variant["name"].startswith("Zeus") and index == 0 else '"0"',
    }
    return f'''library ieee;
use ieee.std_logic_1164.all;
use work.my_arrays.all;
entity n3_sram{index} is port({ports}); end;
architecture forwarding of n3_sram{index} is begin
    dut : entity work.SRAM_main
        generic map({', '.join(f'{name} => {value}' for name, value in generics.items())})
        port map({', '.join(f'{name} => {name}' for name in names)});
end architecture;
'''


def sram_equivalence(variant, original_source):
    _, names = entity_ports(original_source)
    outputs = ["reading_status", "RCLK", "ME", "RE", "WE", "MCLK", "SE_D", "SE_ADR", "SE_Q",
               "SE_RM", "SI_D", "SI_ADR", "SI_Q", "SI_RM", "LED_err", "LED_read", "LED_init", "load_q"]
    if variant["puf"]: outputs += ["sram_done"]
    inputs = {"sys_clk": "clk", "reset": "reset_n", "enable": "enable_in", "data_select": '"11"',
              "sram_addr_select": "'0'", "SO_Q": "serial_input", "SO_ADR": "'0'",
              "SO_D": "'0'", "SO_RM": "'0'", "sram_trigger": "trigger"}
    mappings = []
    for prefix in ("reference", "candidate"):
        pairs = []
        for name in names:
            if name in outputs: target = f"{prefix}_control({outputs.index(name)})"
            elif name == "serial_out": target = f"{prefix}_data"
            elif name == "xmit_ready": target = f"{prefix}_ready"
            elif name == "xmit_ack": target = "ack"
            else: target = inputs[name]
            pairs.append(f"{name} => {target}")
        mappings.append(", ".join(pairs))
    address_bits = variant["sram0_address_bits"]
    data_bits = variant["sram0_data_bits"]
    rm = 7 if variant["name"].startswith("Zeus") else 5
    tcam = "1" if variant["name"].startswith("Zeus") else "0"
    limit = 5000000 if variant["puf"] else 8
    generic = f'num_addrbits => {address_bits}, num_databits => {data_bits}, num_rmbits => {rm}, waitlimit => {limit}, am_i_tcam => "{tcam}"'
    # The PUF wait timer is unused. A tiny candidate bound stresses the fixed
    # long-wait path against the untouched reference's normal timer bound.
    candidate_generic = generic.replace("waitlimit => 5000000", "waitlimit => 8") if variant["puf"] else generic
    return f'''library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;
entity tb_sram_equivalence is end;
architecture test of tb_sram_equivalence is
    signal clk : std_logic := '0';
    signal reset_n, ack, trigger, serial_input : std_logic := '0';
    signal enable_in : std_logic := '0';
    signal reference_control, candidate_control : std_logic_vector({len(outputs)-1} downto 0);
    signal reference_data, candidate_data : std_logic_vector(159 downto 0);
    signal reference_ready, candidate_ready : std_logic;
begin
    clk <= not clk after 10 ns;
    reference : entity work.SRAM_reference generic map({generic}) port map({mappings[0]});
    candidate : entity work.SRAM_main generic map({candidate_generic}) port map({mappings[1]});
    process
        variable samples : integer := 0;
        variable hold_cycles : integer := 0;
        variable accepted : boolean := false;
        variable expected_address : integer := 0;
    begin
        for cycle in 0 to 200000 loop
            wait until falling_edge(clk);
            if cycle < 4 or cycle = 231 or cycle = 4298 then reset_n <= '0';
            else reset_n <= '1'; end if;
            if cycle mod 10000 < 50 then trigger <= '1'; else trigger <= '0'; end if;
            if cycle < 1000 then enable_in <= '0'; else enable_in <= '1'; end if;
            if cycle mod 10 < 5 then serial_input <= '1'; else serial_input <= '0'; end if;
            wait until rising_edge(clk); wait for 1 ns;
            if reset_n = '0' then expected_address := 0; end if;
            assert reference_control = candidate_control report "SRAM control timing changed at cycle " & integer'image(cycle) severity failure;
            assert reference_ready = candidate_ready report "SRAM ready cadence changed" severity failure;
            if reference_ready = '1' then
                assert reference_data = candidate_data report "SRAM full record changed" severity failure;
                hold_cycles := hold_cycles + 1;
                if hold_cycles >= 40 then
                    ack <= '1';
                    if not accepted then
                        assert to_integer(unsigned(candidate_data({data_bits+address_bits-1} downto {data_bits}))) = expected_address
                            report "SRAM skipped/repeated an address or failed to wrap" severity failure;
                        expected_address := (expected_address + 1) mod {2**address_bits};
                        samples := samples + 1; accepted := true;
                    end if;
                end if;
            else
                ack <= '0'; hold_cycles := 0; accepted := false;
            end if;
            if samples >= 6 then
                report "PASS: SRAM clock-enable equivalence, GPIO cadence, complete records and reset";
                finish;
            end if;
        end loop;
        assert false report "no SRAM records generated" severity failure;
    end process;
end architecture;
'''


def hps_stub():
    text = (HERE / "board/terasic/soc_system_bb.v").read_text()
    ports = []
    for direction, width, name in re.findall(r"\b(input|output|inout)\s*(\[[^\]]+\])?\s*(\w+)\s*;", text):
        if name.startswith(("memory_", "hps_0_hps_io_")) or name in {"clk_clk", "reset_reset_n", "hps_0_h2f_reset_reset_n"}:
            name = name.replace("hps_0_hps_io_", "hps_io_").replace("hps_0_h2f_reset_reset_n", "hps_reset_reset_n")
            ports.append(f"{direction} {width} {name}")
    assert len(ports) > 80, "vendor HPS interface extraction incomplete"
    for source in ("counter", "ivt", "sram0", "sram1"):
        ports += [f"input [159:0] n3_records_{source}_data", f"input n3_records_{source}_ready",
                  f"output n3_records_{source}_ack"]
    return "// STRUCTURAL LINT ONLY: vendor HPS port contract; no DDR/Ethernet behavior.\nmodule n3_hps (\n" + ",\n".join(ports) + "\n); endmodule\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghdl", default=os.environ.get("GHDL", "ghdl"))
    parser.add_argument("--variant", help="limit to a variant name while developing")
    args = parser.parse_args()
    variants = json.loads((HERE / "variants.json").read_text())
    if args.variant: variants = [v for v in variants if v["name"] == args.variant]
    if not variants: parser.error("unknown variant")
    report = {"hps_model": "vendor port contract only; no hardware validation", "variants": {}}
    for variant in variants:
        name = variant["name"]
        print(f"Checking {name}", flush=True)
        directory = ROOT / variant["directory"]
        work = HERE / "build" / name / "hdl_check"
        work.mkdir(parents=True, exist_ok=True)
        qsf = (directory / "N3_Ethernet.qsf").read_text()
        sources = [directory / path for path in re.findall(r"^set_global_assignment -name VHDL_FILE (.+)$", qsf, re.M)]
        run([args.ghdl, "-a", *FLAGS, *sources], work, "analyze")
        template = (HERE / "tests/tb_n3_producer.vhd.in").read_text()
        if variant["producer"] == "lsb":
            expected = 'expected(159 downto 152) := x"20"; expected(18 downto 12) := std_logic_vector(to_unsigned(index, 7));'
            last, extra = "59", ""
        else:
            expected = 'expected(159 downto 152) := x"60"; expected(88 downto 64) := std_logic_vector(to_unsigned(index, 25)); expected(59 downto 0) := inputs;'
            last, extra = "127", "sr_clk => open,"
        producer = variant["producer"] + "_main"
        bench = template.replace("__PRODUCER__", producer).replace("__LAST_INDEX__", last).replace("__EXTRA_PORTS__", extra).replace("__EXPECTED_WORD__", expected)
        (work / "tb_n3_producer.vhd").write_text(bench)
        run([args.ghdl, "-a", *FLAGS, "tb_n3_producer.vhd"], work, "producer_analyze")
        run([args.ghdl, "-e", *FLAGS, "tb_n3_producer"], work, "producer_elaborate")
        print(run([args.ghdl, "-r", *FLAGS, "tb_n3_producer", "--assert-level=error"], work, "producer_run").strip(), flush=True)
        if variant["producer"] == "lsb":
            run([args.ghdl, "-a", *FLAGS, HERE / "tests/tb_count_rollover.vhd"], work, "counter_analyze")
            run([args.ghdl, "-e", *FLAGS, "tb_count_rollover"], work, "counter_elaborate")
            run([args.ghdl, "-r", *FLAGS, "tb_count_rollover", "--assert-level=error"], work, "counter_run")
        original_sram = (ROOT / variant["source_directory"] / "SRAM_main.vhd").read_text()
        # Compare divider timing against the original architecture with only
        # the intentional scan-address repair applied equally. Independent
        # scoreboarding above verifies address order and wrap.
        reference = re.sub(r"\bSRAM_main\b", "SRAM_reference", repair_sram_addressing(original_sram, variant["puf"]), flags=re.I)
        (work / "SRAM_reference.vhd").write_text(reference)
        (work / "tb_sram_equivalence.vhd").write_text(sram_equivalence(variant, original_sram))
        run([args.ghdl, "-a", *FLAGS, ROOT / variant["source_directory"] / "Clock2_5MHz.vhd",
             "SRAM_reference.vhd", "tb_sram_equivalence.vhd"], work, "sram_analyze")
        run([args.ghdl, "-e", *FLAGS, "tb_sram_equivalence"], work, "sram_elaborate")
        sram_result = run([args.ghdl, "-r", *FLAGS, "tb_sram_equivalence", "--assert-level=error"], work, "sram_run")
        print("\n".join(sram_result.strip().splitlines()[-2:]), flush=True)
        compact = dict(variant, sram0_address_bits=2)
        compact_bench = sram_equivalence(compact, original_sram).replace("tb_sram_equivalence", "tb_sram_rollover")
        (work / "tb_sram_rollover.vhd").write_text(compact_bench)
        run([args.ghdl, "-a", *FLAGS, "tb_sram_rollover.vhd"], work, "sram_rollover_analyze")
        run([args.ghdl, "-e", *FLAGS, "tb_sram_rollover"], work, "sram_rollover_elaborate")
        run([args.ghdl, "-r", *FLAGS, "tb_sram_rollover", "--assert-level=error"], work, "sram_rollover_run")
        verilog = []
        for module in (producer, "powerdata", "Clock2_5MHz"):
            path = work / f"{module}.v"
            run([args.ghdl, "--synth", *FLAGS, "--out=verilog", module], work, f"synth_{module}", path)
            verilog.append(path)
        for index in (0, 1):
            (work / f"n3_sram{index}.vhd").write_text(sram_wrapper(variant, index, original_sram))
            run([args.ghdl, "-a", *FLAGS, f"n3_sram{index}.vhd"], work, f"analyze_sram{index}")
            path = work / f"n3_sram{index}.v"
            run([args.ghdl, "--synth", *FLAGS, "--out=verilog", f"n3_sram{index}"], work, f"synth_sram{index}", path)
            verilog.append(path)
        # The two VHDL generic specializations have already been checked by
        # GHDL. Replace only their generic syntax in this lint-only top copy.
        top = (directory / "DE10_TOP_Ethernet.v").read_text()
        top = re.sub(r"//[^\n]*", "", top)
        for index in (0, 1):
            top, count = re.subn(r"SRAM_main\s*#\(.*?\)sram_test" + str(index+1),
                                 f"n3_sram{index} sram_test{index+1}", top, count=1, flags=re.S)
            assert count == 1
        # VHDL is case insensitive; preserve each synthesized module's exact
        # Verilog port spelling when checking the original mixed-language top.
        for module, instance in [(producer, producer + "_test"), ("powerdata", "power"), ("Clock2_5MHz", "slow_clock"),
                                 ("n3_sram0", "sram_test1"), ("n3_sram1", "sram_test2")]:
            source = (work / (module + ".v")).read_text()
            header = re.search(r"module " + module + r"\s*\((.*?)\);", source, re.S).group(1)
            port_names = re.findall(r"(?:input|output|inout)\s*(?:\[[^\]]+\])?\s*(\w+)", header)
            spelling = {port.lower(): port for port in port_names}
            start = re.search(r"\b" + module + r"\s+" + instance + r"\s*\(", top).end()
            end = top.index(");", start)
            region = re.sub(r"\.(\w+)\s*\(", lambda m: "." + spelling.get(m[1].lower(), m[1]) + "(", top[start:end])
            top = top[:start] + region + top[end:]
        (work / "top_for_lint.v").write_text(top)
        (work / "hps_for_lint.v").write_text(hps_stub())
        run(["verilator", "--lint-only", "--top-module", "DE10_TOP", "-Wno-fatal", "-Wno-PINMISSING",
             "-Werror-WIDTH", "-Werror-IMPLICIT", "-Werror-UNSIGNED", "top_for_lint.v", "hps_for_lint.v", *verilog], work, "top_lint")
        report["variants"][name] = {"vhdl_analysis": "passed", "producer_simulation": "passed",
            "sram_equivalence": "passed (same intended address repair on reference)", "sram_address_rollover": "passed", "vhdl_synthesis": "passed", "top_structural_lint": "passed",
            "counter_rollover": "passed" if variant["producer"] == "lsb" else "not applicable"}
        print(f"PASS {name}: producer, SRAM equivalence, VHDL synthesis and top structural lint", flush=True)
    output = HERE / "build/hdl_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
