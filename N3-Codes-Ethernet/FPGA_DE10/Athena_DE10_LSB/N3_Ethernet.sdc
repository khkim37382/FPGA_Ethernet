source ../../ethernet/board/n3_ethernet.sdc
# Original /21 DUT PISO clock: 11 cycles high, 10 low.
create_generated_clock -name dut_piso -source [get_ports {CLOCK_50}] -edges {21 43 63} [get_ports {HSMC_RX_D_P[7]}]
