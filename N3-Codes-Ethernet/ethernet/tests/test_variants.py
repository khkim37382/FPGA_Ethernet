import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from n3_analysis import VARIANTS, decode_fields


def load_tool(name):
    specification = importlib.util.spec_from_file_location(name, HERE / "board" / (name + ".py"))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class VariantTests(unittest.TestCase):
    def test_all_four_revisions_have_local_source_graph_and_correct_producer(self):
        for variant in VARIANTS.values():
            with self.subTest(variant=variant["name"]):
                directory = ROOT / variant["directory"]
                text = (directory / "N3_Ethernet.qsf").read_text()
                self.assertIn("VHDL_INPUT_VERSION VHDL_2008", text)
                paths = re.findall(r"-name (?:VHDL_FILE|VERILOG_FILE|SDC_FILE) (.+)", text)
                for path in paths:
                    self.assertTrue((directory / path).is_file(), path)
                self.assertNotIn("loan_io/synthesis", text)
                self.assertNotIn("xmit_mux", text)
                self.assertNotIn("memory_mem_", text)
                self.assertIn("n3_hps/synthesis/n3_hps.qip", text)
                top = (directory / "DE10_TOP_Ethernet.v").read_text()
                producer = variant["producer"]
                self.assertIn(f".n3_records_counter_data({producer}_data)", top)
                self.assertIn(f".n3_records_counter_ack({producer}_xmit_ack)", top)
                self.assertNotIn("xmit_mux serial_xmit", top)
                self.assertIn(".memory_mem_dq(HPS_DDR3_DQ)", top)
                self.assertIn("wire n3_reset_n", top)
                if variant["puf"]:
                    self.assertIn(".sram_trigger(clk_sr)", top)
                    self.assertIn(".sram_trigger(SRAM2_trigger)", top)
                if variant["name"].startswith("Zeus"):
                    self.assertIn(".am_i_tcam(1'b1)", top)
                if variant["producer"] == "lsb":
                    self.assertIn("Clock2_5MHz slow_clock", top)
                    self.assertIn("assign clk_piso = clk2_5;", top)
                    self.assertIn("-edges {21 43 63}", (directory / "N3_Ethernet.sdc").read_text())

    def test_hps_memory_and_pin_configuration_matches_the_sourced_board_preset(self):
        def parameters(path):
            hps = ET.parse(path).getroot().find("module[@name='hps_0']")
            return {p.get("name"): p.get("value", p.text) for p in hps.findall("parameter")}
        actual = parameters(HERE / "board/n3_hps.qsys")
        reference = parameters(HERE / "board/terasic/soc_system.qsys")
        for name in reference:
            if name.startswith(("MEM_", "TIMING_", "CTL_")) or name.endswith(("_Mode", "_PinMuxing")) or name in {"REF_CLK_FREQ", "GPIO_Enable", "LOANIO_Enable"}:
                self.assertEqual(actual[name], reference[name], name)
        self.assertEqual(actual["MEM_DQ_WIDTH"], "32")
        self.assertEqual(actual["EMAC1_Mode"], "RGMII")
        self.assertEqual(actual["LWH2F_Enable"], "true")
        self.assertEqual(actual["S2F_Width"], "0")

    def test_variant_specific_full_width_sram_and_ff_snapshot_decoding(self):
        for name, variant in VARIANTS.items():
            for index in (0, 1):
                width = variant[f"sram{index}_data_bits"]
                address_bits = variant[f"sram{index}_address_bits"]
                data = (1 << width) - 1
                address = (1 << address_bits) - 1
                raw = (((0xe0 + index) << 152) | address << width | data).to_bytes(20, "big")
                decoded = decode_fields(raw, name)
                self.assertEqual(decoded["address"], address)
                self.assertEqual(int(decoded["data_hex"], 16), data)
                self.assertEqual(decoded["data_meaning"], "raw_power_on_word" if variant["puf"] else "xor_error_mask")
            raw = ((0x60 << 152) | (0x1abcde << 64) | 0xfedcba987654321).to_bytes(20, "big")
            self.assertEqual(decode_fields(raw, name)["frame_address"], 0x1abcde)
            self.assertEqual(decode_fields(raw, name)["ff_bits_hex"], "fedcba987654321")
        counter = ((0x20 << 152) | (59 << 12) | 4095).to_bytes(20, "big")
        self.assertEqual(decode_fields(counter, "Athena_DE10_LSB")["count"], 4095)

    def test_mixed_variant_deployment_has_unique_addresses_and_ids(self):
        tool = load_tool("prepare_deployment")
        names = list(VARIANTS)
        assignments = {str(i): names[(i-1) % 4] for i in range(1, 13)}
        with tempfile.TemporaryDirectory() as temp:
            boards = tool.generate(Path(temp), names[0], assignments)
            self.assertEqual(len({b["ip"] for b in boards}), 12)
            self.assertEqual([b["id"] for b in boards], list(range(1, 13)))
            self.assertEqual([b["variant"] for b in boards], [assignments[str(i)] for i in range(1, 13)])
            self.assertTrue(all(b["uio_device"] is None for b in boards))
            self.assertIn("Address=192.168.1.112/24", (Path(temp) / "board_12/10-n3-eth0.network").read_text())

    def test_uio_address_is_derived_from_metadata_and_old_system_is_rejected(self):
        tool = load_tool("generate_uio")
        # Deliberately differs from the common DE10 address. The generator
        # must use the supplied HPS view rather than a hardcoded SOC address.
        xml = '''<EnsembleReport name="n3_hps">
          <module name="n3_bridge" kind="n3_ethernet_bridge" />
          <module name="hps_0_arm_a9_0"><interface name="altera_axi_master">
          <memoryBlock><moduleName>n3_bridge</moduleName><slaveName>avs</slaveName>
          <baseAddress>0xabcd0000</baseAddress><span>128</span></memoryBlock>
          </interface></module></EnsembleReport>'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "n3_hps.sopcinfo"
            path.write_text(xml)
            self.assertEqual(tool.generate(path, Path(temp) / "output"), (0xabcd0000, 128))
            self.assertIn("0xabcd0000", (Path(temp) / "output/n3-uio.dtsi").read_text())
            path.write_text(xml.replace('name="n3_hps"', 'name="loan_io"'))
            with self.assertRaises(ValueError): tool.resolve_address(path)
            path.write_text(xml.replace("0xabcd0000", "0xabcd0004"))
            with self.assertRaises(ValueError): tool.resolve_address(path)

    def test_uio_composes_generated_bridge_window_with_relative_slave_offset(self):
        tool = load_tool("generate_uio")
        xml = '''<EnsembleReport name="n3_hps">
          <module name="n3_bridge" kind="n3_ethernet_bridge" />
          <module name="hps_0_arm_a9_0"><interface>
          <memoryBlock><isBridge>true</isBridge><slaveName>axi_h2f_lw</slaveName>
          <baseAddress>0x80000000</baseAddress><span>2097152</span></memoryBlock>
          </interface></module>
          <module name="hps_0"><interface name="h2f_lw_axi_master">
          <memoryBlock><moduleName>n3_bridge</moduleName><slaveName>avs</slaveName>
          <baseAddress>65536</baseAddress><span>128</span></memoryBlock>
          </interface></module></EnsembleReport>'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "n3_hps.sopcinfo"; path.write_text(xml)
            self.assertEqual(tool.resolve_address(path)[:2], (0x80010000, 128))

    def test_quartus_workflow_dry_run_lists_all_four_projects(self):
        result = subprocess.run([sys.executable, str(HERE / "build_quartus.py"), "--dry-run"], check=True, capture_output=True, text=True)
        for variant in VARIANTS.values(): self.assertIn(variant["directory"], result.stdout)
        self.assertIn("qsys-generate", result.stdout)
        self.assertIn("generate_uio.py", result.stdout)

    @unittest.skipUnless(shutil.which("dtc"), "dtc is optional; install it to check overlay syntax")
    def test_generated_polling_uio_overlay_compiles(self):
        tool = load_tool("generate_uio")
        xml = '''<EnsembleReport name="n3_hps"><module name="n3_bridge" kind="n3_ethernet_bridge" />
        <module name="hps_0_arm_a9_0"><interface><memoryBlock><moduleName>n3_bridge</moduleName>
        <slaveName>avs</slaveName><baseAddress>0xabcd0000</baseAddress><span>128</span>
        </memoryBlock></interface></module></EnsembleReport>'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.sopcinfo"; path.write_text(xml)
            output = Path(temp) / "output"; tool.generate(path, output)
            result = subprocess.run(["dtc", "-@", "-I", "dts", "-O", "dtb", "-o", str(output / "test.dtbo"),
                                     str(output / "n3-uio.dtso")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater((output / "test.dtbo").stat().st_size, 0)
