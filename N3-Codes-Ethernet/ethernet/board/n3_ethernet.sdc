# Common 50 MHz acquisition/Avalon clock. HPS DDR and I/O timing comes from
# the regenerated n3_hps QIP's IP-specific timing files.
create_clock -name CLOCK_50 -period 20.000 [get_ports {CLOCK_50}]
derive_pll_clocks
derive_clock_uncertainty

# The Ethernet SRAM controllers use a /21 clock enable on CLOCK_50, rather
# than a derived clock. FFMCU's original long-period trigger generator and
# DUT input/output timing still require review in the fitted timing reports.
# Do not add guessed DUT input/output delays or blanket false paths here.
