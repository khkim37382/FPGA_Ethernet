`timescale 1ns/1ps
module tb_n3_bridge;
    logic clk = 0;
    always #10 clk = ~clk;
    logic reset = 1;
    logic [159:0] counter_data = 160'h2000000000000000000000000000000000000001;
    logic [159:0] ivt_data = 160'h8000000000000000000000000000000000000002;
    logic [159:0] sram0_data = 160'he000000000000000000000000000000000000003;
    logic [159:0] sram1_data = 160'he100000000000000000000000000000000000004;
    logic counter_ready = 0, ivt_ready = 0, sram0_ready = 0, sram1_ready = 0;
    logic counter_ack, ivt_ack, sram0_ack, sram1_ack;
    logic [4:0] avs_address = 0;
    logic avs_read = 0, avs_write = 0;
    logic [31:0] avs_writedata = 0, avs_readdata;
    logic avs_waitrequest;
    n3_ethernet_bridge #(.FIFO_DEPTH(4)) dut (.*);
    int trace;
    int mmio_trace;
    logic [223:0] record;
    logic [63:0] previous_timestamp = 0;
    task automatic cycles(input int n);
        repeat (n) begin @(posedge clk); #1; end
    endtask
    task automatic write_reg(input logic [4:0] addr, input logic [31:0] data);
        @(negedge clk); avs_address = addr; avs_writedata = data; avs_write = 1;
        cycles(1);
        @(negedge clk); avs_write = 0;
    endtask
    task automatic check_reg(input logic [4:0] addr, input logic [31:0] expected);
        @(negedge clk); avs_address = addr; avs_read = 1;
        #1;
        assert (avs_readdata == expected)
            else $fatal(1, "register %0d: got %h expected %h", addr, avs_readdata, expected);
        avs_read = 0;
    endtask
    task automatic take_record(input logic [159:0] expected);
        write_reg(4, 1);
        for (int i = 0; i < 7; i++) begin
            @(negedge clk); avs_address = 5'(8+i); avs_read = 1;
            #1; record[i*32 +: 32] = avs_readdata;
        end
        avs_read = 0;
        assert(record[159:0] == expected) else $fatal(1, "truncated/reordered N3 word");
        assert(record[223:160] > previous_timestamp) else $fatal(1, "timestamp order");
        previous_timestamp = record[223:160];
        // A second capture without release must never consume a second word.
        write_reg(4, 1);
        @(negedge clk); avs_address = 8; avs_read = 1;
        #1; assert(avs_readdata == record[31:0]) else $fatal(1, "latch changed");
        avs_read = 0;
        for (int byte_index = 27; byte_index >= 0; byte_index--)
            $fwrite(trace, "%c", record[byte_index*8 +: 8]);
        for (int byte_index = 0; byte_index < 28; byte_index++)
            $fwrite(mmio_trace, "%c", record[byte_index*8 +: 8]);
        write_reg(4, 2);
    endtask
    initial begin
        trace = $fopen("build/rtl_records.bin", "wb");
        mmio_trace = $fopen("build/rtl_mmio_words.bin", "wb");
        assert(trace != 0) else $fatal(1, "trace open failed");
        cycles(3); @(negedge clk); reset = 0;
        {sram1_ready,sram0_ready,ivt_ready,counter_ready} = 4'b1111;
        cycles(8);
        assert({sram1_ack,sram0_ack,ivt_ack,counter_ack} == 0) else $fatal(1, "ack while disabled");
        write_reg(2, 1);
        cycles(10);
        assert({sram1_ack,sram0_ack,ivt_ack,counter_ack} == 15) else $fatal(1, "starved producer");
        check_reg(5, 4); check_reg(16, 4);
        cycles(12); check_reg(16, 4); // held ready must not duplicate records
        @(negedge clk); counter_ready = 0;
        cycles(2);
        @(negedge clk); counter_data = 160'h2000000000000000000000000000000000000005; counter_ready = 1;
        cycles(5);
        assert(!counter_ack) else $fatal(1, "ack on full FIFO");
        // First pop frees a slot for pending word 5; head must still be word 1.
        take_record(160'h2000000000000000000000000000000000000001);
        assert(counter_ack) else $fatal(1, "pending producer did not resume");
        take_record(ivt_data); take_record(sram0_data); take_record(sram1_data); take_record(counter_data);
        check_reg(5, 0); check_reg(16, 5); check_reg(18, 5);
        write_reg(4, 1); check_reg(3, 1); // empty capture cannot fabricate a record
        check_reg(18, 5);
        @(negedge clk); reset = 1;
        cycles(3); check_reg(16, 0); check_reg(5, 0); check_reg(3, 1);
        $fclose(trace);
        $fclose(mmio_trace);
        $display("PASS: four sources, full/backpressure, held-ready, stable capture, timestamp, reset");
        $finish;
    end
    initial begin #100000; $fatal(1, "test timeout"); end
endmodule
