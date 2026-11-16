CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror
REF = multi_fpga_receiver/bridge
GHDL ?= ghdl
ZIG ?= zig

.PHONY: all test hdl-check check-all prepare arm clean
all: build/n3_udp_sender

prepare:
	python3 prepare_projects.py
	python3 board/prepare_deployment.py

hdl-check:
	python3 check_hdl.py --ghdl "$(GHDL)"

check-all: test hdl-check

arm: build/arm-linux/n3_udp_sender

build/arm-linux/n3_udp_sender: bridge/n3_udp_sender.c bridge/n3_record.h $(REF)/fpga_udp_bridge.c $(REF)/fpga_udp_bridge.h
	mkdir -p build/arm-linux
	$(ZIG) cc -target arm-linux-musleabihf -mcpu=cortex_a9 -static -s $(CFLAGS) -I$(REF) bridge/n3_udp_sender.c $(REF)/fpga_udp_bridge.c -o $@

build/n3_udp_sender: bridge/n3_udp_sender.c bridge/n3_record.h $(REF)/fpga_udp_bridge.c $(REF)/fpga_udp_bridge.h
	mkdir -p build
	$(CC) $(CFLAGS) -I$(REF) bridge/n3_udp_sender.c $(REF)/fpga_udp_bridge.c -o $@

build/test_n3_word_order: tests/test_n3_word_order.c bridge/n3_record.h
	mkdir -p build
	$(CC) $(CFLAGS) -Ibridge tests/test_n3_word_order.c -o $@

test: all build/test_n3_word_order
	verilator --binary --timing --assert -Wno-fatal --top-module tb_n3_bridge --Mdir build/rtl_test rtl/n3_ethernet_bridge.sv tests/tb_n3_bridge.sv
	./build/rtl_test/Vtb_n3_bridge
	python3 -m unittest discover -s tests -v
	cd multi_fpga_receiver && python3 -m unittest discover -s tests -v

clean:
	$(RM) -r build
