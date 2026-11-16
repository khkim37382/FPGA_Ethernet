`timescale 1ns/1ps
// Athena LSB's four level/ack producers and Avalon bus all use CLOCK_50.
// No source is acknowledged until its complete 160-bit word is buffered.
module n3_ethernet_bridge #(
    parameter int FIFO_DEPTH = 1024,
    localparam int PTR_W = $clog2(FIFO_DEPTH)
) (
    input logic clk, reset,
    input logic [159:0] counter_data, ivt_data, sram0_data, sram1_data,
    input logic counter_ready, ivt_ready, sram0_ready, sram1_ready,
    output logic counter_ack, ivt_ack, sram0_ack, sram1_ack,
    input logic [4:0] avs_address, // WORD address: byte offset / 4
    input logic avs_read, avs_write,
    input logic [31:0] avs_writedata,
    output logic [31:0] avs_readdata,
    output logic avs_waitrequest
);
    initial begin
        if (FIFO_DEPTH < 4 || (FIFO_DEPTH & (FIFO_DEPTH-1)) != 0)
            $error("FIFO_DEPTH must be a power of two >= 4");
    end
    logic [223:0] memory [0:FIFO_DEPTH-1];
    logic [223:0] latched;
    logic [PTR_W-1:0] wr_ptr, rd_ptr;
    logic [PTR_W:0] level;
    logic [63:0] ticks, accepted, consumed, stalled_cycles;
    logic enabled, record_latched;
    logic [3:0] ready, ack;
    logic [1:0] next_source, selected;
    logic found, push, pop;
    logic [159:0] selected_data;

    assign ready = {sram1_ready, sram0_ready, ivt_ready, counter_ready};
    assign {sram1_ack, sram0_ack, ivt_ack, counter_ack} = ack;
    assign avs_waitrequest = 1'b0;
    // Explicit capture command avoids DATA0 first-read/stale-latch ambiguity.
    assign pop = avs_write && avs_address == 5'd4 && avs_writedata[0]
                 && !record_latched && level != 0;
    assign push = enabled && found && int'(level) < FIFO_DEPTH;

    always_comb begin
        found = 1'b0;
        selected = next_source;
        for (int i = 0; i < 4; i++) begin
            if (!found && ready[2'(int'(next_source) + i)]
                       && !ack[2'(int'(next_source) + i)]) begin
                selected = 2'(int'(next_source) + i);
                found = 1'b1;
            end
        end
        case (selected)
            0: selected_data = counter_data;
            1: selected_data = ivt_data;
            2: selected_data = sram0_data;
            3: selected_data = sram1_data;
        endcase
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            wr_ptr <= '0; rd_ptr <= '0; level <= '0;
            ticks <= '0; accepted <= '0; consumed <= '0; stalled_cycles <= '0;
            enabled <= 1'b0; record_latched <= 1'b0; latched <= '0;
            ack <= '0; next_source <= '0;
        end else begin
            ticks <= ticks + 1'b1;
            // Hold ack until the producer has lowered ready (four-phase handshake).
            ack <= ack & ready;
            if (avs_write && avs_address == 5'd2) enabled <= avs_writedata[0];
            if (enabled && found && int'(level) == FIFO_DEPTH)
                stalled_cycles <= stalled_cycles + 1'b1;
            if (push) begin
                memory[wr_ptr] <= {ticks, selected_data};
                wr_ptr <= wr_ptr + 1'b1;
                ack[selected] <= 1'b1;
                next_source <= selected + 1'b1;
                accepted <= accepted + 1'b1;
            end
            if (pop) begin
                latched <= memory[rd_ptr];
                record_latched <= 1'b1;
                rd_ptr <= rd_ptr + 1'b1;
                consumed <= consumed + 1'b1;
            end else if (avs_write && avs_address == 5'd4 && avs_writedata[1])
                record_latched <= 1'b0;
            case ({push, pop})
                2'b10: level <= level + 1'b1;
                2'b01: level <= level - 1'b1;
                default: ;
            endcase
        end
    end

    always_comb begin
        avs_readdata = '0;
        case (avs_address)
            0: avs_readdata = 32'h4e334531; // N3E1
            1: avs_readdata = 32'h00010000;
            2: avs_readdata = {31'd0, enabled};
            3: avs_readdata = {29'd0, record_latched, (int'(level) == FIFO_DEPTH), (level == 0)};
            5: avs_readdata = 32'(level);
            8,9,10,11,12,13,14: avs_readdata = latched[(int'(avs_address)-8)*32 +: 32];
            16: avs_readdata = accepted[31:0];
            17: avs_readdata = accepted[63:32];
            18: avs_readdata = consumed[31:0];
            19: avs_readdata = consumed[63:32];
            20: avs_readdata = stalled_cycles[31:0];
            21: avs_readdata = stalled_cycles[63:32];
            22: avs_readdata = 32'd50000000;
            default: ;
        endcase
    end
    // avs_read is supplied for the Avalon interface; reads have no side effects.
endmodule
