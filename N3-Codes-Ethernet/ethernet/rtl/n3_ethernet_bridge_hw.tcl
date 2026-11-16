package require -exact qsys 23.1
set_module_property NAME n3_ethernet_bridge
set_module_property VERSION 1.0
set_module_property GROUP "ISDE"
set_module_property DISPLAY_NAME "N3 Athena record bridge"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
add_fileset synthesis_files QUARTUS_SYNTH ""
set_fileset_property synthesis_files TOP_LEVEL n3_ethernet_bridge
add_fileset_file n3_ethernet_bridge.sv SYSTEM_VERILOG PATH n3_ethernet_bridge.sv TOP_LEVEL_FILE
add_interface clock clock end
add_interface_port clock clk clk Input 1
add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges DEASSERT
add_interface_port reset reset reset Input 1
add_interface avs avalon end
set_interface_property avs associatedClock clock
set_interface_property avs associatedReset reset
set_interface_property avs addressUnits WORDS
set_interface_property avs readLatency 0
set_interface_property avs maximumPendingReadTransactions 0
set_interface_property avs explicitAddressSpan 128
add_interface_port avs avs_address address Input 5
add_interface_port avs avs_read read Input 1
add_interface_port avs avs_write write Input 1
add_interface_port avs avs_writedata writedata Input 32
add_interface_port avs avs_readdata readdata Output 32
add_interface_port avs avs_waitrequest waitrequest Output 1
add_interface records conduit end
set_interface_property records associatedClock clock
set_interface_property records associatedReset reset
foreach source {counter ivt sram0 sram1} {
    add_interface_port records ${source}_data ${source}_data Input 160
    add_interface_port records ${source}_ready ${source}_ready Input 1
    add_interface_port records ${source}_ack ${source}_ack Output 1
}
