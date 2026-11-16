# Import scope

This repository imports the modified `N3-Codes-Ethernet` project, keeping that
folder name so the existing relative build paths continue to work. The sibling
original `N3-Codes` project and unrelated workspace projects are not included.

Included:

- Four DE10 Ethernet revisions, shared/generated acquisition sources, original
  source inputs, Qsys configuration and Terasic reference/provenance files.
- Common FIFO/Avalon bridge, HPS sender source, receiver, decoder, tests,
  deployment templates, legacy parsers, and reference documentation.
- The previously cross-built ARM Linux sender and its `BUILD.json` provenance.
  This executable has not been exercised on a physical board.

Excluded:

- Historical measurement CSVs and PNG plots (several gigabytes locally).
- Quartus outputs/databases/reports, historical bitstreams, generated `loan_io/`
  and HPS handoff directories, backup files, Python caches and macOS metadata.
- Host-native executables, generated simulation outputs and local test logs.

The original source `loan_io.qsys` files remain because project preparation
reads them. Generated `loan_io/` outputs are stale and are excluded. Generate
fresh `n3_hps` IP, UIO metadata and matching HPS boot artifacts for hardware use.

`ethernet/VALIDATION.md` records the earlier local validation, including local
log paths. Those logs are reproducible with the documented commands and are
not distributed in this import. The original README's reference to
`COPY_AUDIT.json` concerns the earlier local copy; that audit file was not
present in the supplied folder.

## Import verification — 2026-11-16

The imported copy passed `make test` on macOS: the self-checking Verilator
bridge simulation, 13 N3/configuration tests and seven receiver tests passed.
Localhost UDP socket permissions were required for transport tests. The
all-four-variant `build_quartus.py --dry-run` succeeded and links in the new
repository README/testing guide were checked.

GHDL synthesis/simulation was not repeated during this import; the earlier
results remain documented in `ethernet/VALIDATION.md`. Quartus and physical
hardware testing remain outstanding.
