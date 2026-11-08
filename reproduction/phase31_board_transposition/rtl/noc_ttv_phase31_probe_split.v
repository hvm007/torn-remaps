module noc_ttv_phase18_probe
  #(parameter [0:63] PHYSICAL_SLOT_LABELS =
      64'b1110110100100001111111000011000010101011010001011001100001110110,
    parameter HEADER_DIM_ORDER = 0,
    parameter SWAP_DEST_XY = 0,
    parameter ROUTER_DIM_ORDER = 0,
    parameter [0:15] ROUTER_DIM_ORDER_MASK = 16'b0,
    parameter integer ROUTER_NUM_NODES = 16,
    parameter [0:63] HOST_LABELS =
      64'b1110110100100001111111000011000010101011010001011001100001110110,
    parameter [0:63] FABRIC_LABELS =
      64'b1110110100100001111111000011000010101011010001011001100001110110)
  (clk, reset, record_valid, record_ready, record_data, done, status);

   input clk;
   input reset;
   output record_valid;
   input record_ready;
   output [7:0] record_data;
   output reg done;
   output [7:0] status;

   localparam integer NUM_VCS = 2;
   localparam integer VC_INDEX_WIDTH = 1;
   localparam integer CHANNEL_WIDTH = 36 + VC_INDEX_WIDTH;
   localparam integer FLOW_CTRL_WIDTH = 1 + VC_INDEX_WIDTH;
   localparam integer TRACE_CAPACITY = 8;
   localparam integer PACKET_COUNT = 13;
   localparam integer RECORD_BYTES = 23;

   localparam [2:0] STATE_RESET_NOC = 0;
   localparam [2:0] STATE_HEADER = 1;
   localparam [2:0] STATE_INJECT = 2;
   localparam [2:0] STATE_OBSERVE = 3;
   localparam [2:0] STATE_PREP_SEND = 4;
   localparam [2:0] STATE_SEND = 5;
   localparam [2:0] STATE_DONE = 6;

   reg [2:0] state;
   reg noc_reset;
   reg inject_valid;
   reg [2:0] reset_count;
   reg [6:0] observe_count;
   reg [3:0] packet_index;
   reg [4:0] send_index;
   reg [7:0] crc_accumulator;

   reg captured_config_valid;
   reg [3:0] captured_physical_source;
   reg [3:0] captured_encoded_destination;
   reg captured_delivered_valid;
   reg [3:0] captured_delivered_physical;
   reg [3:0] captured_delivered_logical;
   reg captured_timeout;
   reg trace_overflow;
   reg [3:0] trace_length;
   reg [6:0] trace_events [0:TRACE_CAPACITY-1];
   reg [15:0] router_error_seen;
   reg [7:0] captured_observation_cycles;

   wire [3:0] logical_source = packet_source(packet_index);
   wire [3:0] logical_destination = packet_destination(packet_index);
   wire [0:16*CHANNEL_WIDTH-1] injection_channels;
   wire [0:16*FLOW_CTRL_WIDTH-1] injection_flow_ctrl;
   wire [0:16*CHANNEL_WIDTH-1] ejection_channels;
   wire [0:16*FLOW_CTRL_WIDTH-1] ejection_flow_ctrl;
   wire [0:15] router_error;
   wire [0:79] trace_valid;
   wire [0:3] physical_source;
   wire [0:3] physical_destination;
   wire [0:6] route_info;
   wire [0:4] route_op;
   wire [0:CHANNEL_WIDTH-1] packet_channel;
   wire config_valid;
   wire [0:CHANNEL_WIDTH-1] ejection [0:15];

   integer trace_scan;
   reg [6:0] active_trace_count;
   reg [6:0] active_trace_event;
   integer delivery_scan;
   reg [4:0] active_delivery_count;
   reg [3:0] active_delivery_slot;
   integer clear_index;

   reg [3:0] src_rom [0:12];
   reg [3:0] dst_rom [0:12];
   reg use_rom = 1'b0;
   reg [1023:0] rom_file;
   initial begin
      if($value$plusargs("packets=%s", rom_file)) begin
         $readmemh(rom_file, src_rom, 0, 12);
         $readmemh({rom_file, ".dst"}, dst_rom, 0, 12);
         use_rom = 1'b1;
      end
   end

   function [3:0] packet_source;
      input [3:0] index;
      begin
         if(use_rom) packet_source = src_rom[index];
         else
         case(index)
           0: packet_source = 0;
           1: packet_source = 1;
           2: packet_source = 1;
           3: packet_source = 2;
           4: packet_source = 4;
           5: packet_source = 4;
           6: packet_source = 6;
           7: packet_source = 8;
           8: packet_source = 9;
           9: packet_source = 10;
           10: packet_source = 13;
           11: packet_source = 14;
           default: packet_source = 15;
         endcase
      end
   endfunction

   function [3:0] packet_destination;
      input [3:0] index;
      begin
         if(use_rom) packet_destination = dst_rom[index];
         else
         case(index)
           0: packet_destination = 9;
           1: packet_destination = 3;
           2: packet_destination = 4;
           3: packet_destination = 6;
           4: packet_destination = 6;
           5: packet_destination = 14;
           6: packet_destination = 13;
           7: packet_destination = 2;
           8: packet_destination = 1;
           9: packet_destination = 0;
           10: packet_destination = 6;
           11: packet_destination = 6;
           default: packet_destination = 4;
         endcase
      end
   endfunction

   function [7:0] crc8_next;
      input [7:0] prior;
      input [7:0] value;
      integer bit_index;
      reg [7:0] work;
      begin
         work = prior ^ value;
         for(bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
           if(work[7])
             work = (work << 1) ^ 8'h07;
           else
             work = work << 1;
         crc8_next = work;
      end
   endfunction

   function [7:0] trace_byte;
      input [2:0] index;
      begin
         if(index < trace_length)
           trace_byte = {1'b0, trace_events[index]};
         else
           trace_byte = 0;
      end
   endfunction

   function [7:0] record_byte;
      input [4:0] index;
      begin
         case(index)
           0: record_byte = "N";
           1: record_byte = "T";
           2: record_byte = "D";
           3: record_byte = "1";
           4: record_byte = {4'b0, packet_index};
           5: record_byte = {logical_source, logical_destination};
           6: record_byte = {
                3'b0,
                |router_error_seen,
                trace_overflow,
                captured_timeout,
                captured_delivered_valid,
                captured_config_valid};
           7: record_byte = {
                captured_physical_source,
                captured_encoded_destination};
           8: record_byte = captured_delivered_valid
                ? {4'b0, captured_delivered_physical} : 8'hff;
           9: record_byte = captured_delivered_valid
                ? {4'b0, captured_delivered_logical} : 8'hff;
           10: record_byte = {4'b0, trace_length};
           11: record_byte = trace_byte(0);
           12: record_byte = trace_byte(1);
           13: record_byte = trace_byte(2);
           14: record_byte = trace_byte(3);
           15: record_byte = trace_byte(4);
           16: record_byte = trace_byte(5);
           17: record_byte = trace_byte(6);
           18: record_byte = trace_byte(7);
           19: record_byte = router_error_seen[15:8];
           20: record_byte = router_error_seen[7:0];
           21: record_byte = captured_observation_cycles;
           default: record_byte = crc_accumulator;
         endcase
      end
   endfunction

   always @*
     begin
        active_trace_count = 0;
        active_trace_event = 0;
        for(trace_scan = 0; trace_scan < 80; trace_scan = trace_scan + 1)
          if(trace_valid[trace_scan])
            begin
               active_trace_count = active_trace_count + 1'b1;
               active_trace_event = ((trace_scan / 5) << 3) | (trace_scan % 5);
            end
     end

   always @*
     begin
        active_delivery_count = 0;
        active_delivery_slot = 0;
        for(delivery_scan = 0; delivery_scan < 16;
            delivery_scan = delivery_scan + 1)
          if(ejection[delivery_scan][1])
            begin
               active_delivery_count = active_delivery_count + 1'b1;
               active_delivery_slot = delivery_scan;
            end
     end

   noc_ttv_configured_packet_injector
     #(.VC_INDEX_WIDTH(VC_INDEX_WIDTH),
       .HEADER_DIM_ORDER(HEADER_DIM_ORDER),
       .SWAP_DEST_XY(SWAP_DEST_XY))
   injector
     (.physical_slot_labels(HOST_LABELS), .occupied(16'hffff),
      .logical_source(logical_source), .logical_destination(logical_destination),
      .payload(25'h15555), .inject_valid(inject_valid),
      .physical_source(physical_source),
      .physical_destination(physical_destination),
      .route_info(route_info), .route_op(route_op), .channel(packet_channel),
      .config_valid(config_valid));

   genvar endpoint;
   generate
      for(endpoint = 0; endpoint < 16; endpoint = endpoint + 1)
        begin: endpoints
           assign injection_channels[endpoint*CHANNEL_WIDTH +: CHANNEL_WIDTH]
             = physical_source == endpoint ? packet_channel
               : {CHANNEL_WIDTH{1'b0}};
           assign ejection[endpoint]
             = ejection_channels[endpoint*CHANNEL_WIDTH +: CHANNEL_WIDTH];
           assign ejection_flow_ctrl[
             endpoint*FLOW_CTRL_WIDTH +: FLOW_CTRL_WIDTH]
             = {ejection[endpoint][1],
                ejection[endpoint][2 +: VC_INDEX_WIDTH]};
        end
   endgenerate

   noc_ttv_observed_mesh_4x4
     #(.ROUTER_BUFFER_SIZE(4), .ROUTER_IMPLEMENTATION(2),
       .NUM_VCS(NUM_VCS), .VC_INDEX_WIDTH(VC_INDEX_WIDTH),
       .DIM_ORDER(ROUTER_DIM_ORDER),
       .ROUTER_DIM_ORDER_MASK(ROUTER_DIM_ORDER_MASK))
   mesh
     (.clk(clk), .reset(noc_reset),
      .injection_channels(injection_channels),
      .injection_flow_ctrl(injection_flow_ctrl),
      .ejection_channels(ejection_channels),
      .ejection_flow_ctrl(ejection_flow_ctrl),
      .router_error(router_error), .trace_valid(trace_valid));

   assign record_valid = state == STATE_SEND;
   assign record_data = record_byte(send_index);
   assign status = {(|router_error_seen), trace_overflow,
                    packet_index, done, state != STATE_DONE};

   always @(posedge clk or posedge reset)
     if(reset)
       begin
          state <= STATE_RESET_NOC;
          noc_reset <= 1'b1;
          inject_valid <= 1'b0;
          reset_count <= 0;
          observe_count <= 0;
          packet_index <= 0;
          send_index <= 0;
          crc_accumulator <= 0;
          captured_config_valid <= 1'b0;
          captured_physical_source <= 0;
          captured_encoded_destination <= 0;
          captured_delivered_valid <= 1'b0;
          captured_delivered_physical <= 0;
          captured_delivered_logical <= 0;
          captured_timeout <= 1'b0;
          trace_overflow <= 1'b0;
          trace_length <= 0;
          router_error_seen <= 0;
          captured_observation_cycles <= 0;
          done <= 1'b0;
          for(clear_index = 0; clear_index < TRACE_CAPACITY;
              clear_index = clear_index + 1)
            trace_events[clear_index] <= 0;
       end
     else
       case(state)
         STATE_RESET_NOC:
           begin
              noc_reset <= 1'b1;
              inject_valid <= 1'b0;
              observe_count <= 0;
              captured_delivered_valid <= 1'b0;
              captured_delivered_physical <= 0;
              captured_delivered_logical <= 0;
              captured_timeout <= 1'b0;
              trace_overflow <= 1'b0;
              trace_length <= 0;
              router_error_seen <= 0;
              captured_observation_cycles <= 0;
              if(reset_count == 5)
                begin
                   reset_count <= 0;
                   noc_reset <= 1'b0;
                   state <= STATE_HEADER;
                end
              else
                reset_count <= reset_count + 1'b1;
           end
         STATE_HEADER:
           begin
              captured_config_valid <= config_valid;
              captured_physical_source <= physical_source;
              captured_encoded_destination <= route_info[3:6];
              if(config_valid)
                begin
                   inject_valid <= 1'b1;
                   state <= STATE_INJECT;
                end
              else
                state <= STATE_PREP_SEND;
           end
         STATE_INJECT:
           begin
              inject_valid <= 1'b0;
              router_error_seen <= router_error;
              state <= STATE_OBSERVE;
           end
         STATE_OBSERVE:
           begin
              router_error_seen <= router_error_seen | router_error;
              if(active_trace_count != 0)
                begin
                   if(active_trace_count != 1 || trace_length >= TRACE_CAPACITY)
                     trace_overflow <= 1'b1;
                   else
                     begin
                        trace_events[trace_length] <= active_trace_event;
                        trace_length <= trace_length + 1'b1;
                     end
                end
              if(active_delivery_count != 0)
                begin
                   if(active_delivery_count != 1)
                     trace_overflow <= 1'b1;
                   captured_delivered_valid <= 1'b1;
                   captured_delivered_physical <= active_delivery_slot;
                   captured_delivered_logical
                     <= FABRIC_LABELS[active_delivery_slot*4 +: 4];
                   captured_observation_cycles <= observe_count + 1'b1;
                   state <= STATE_PREP_SEND;
                end
              else if(observe_count == 95)
                begin
                   captured_timeout <= 1'b1;
                   captured_observation_cycles <= 96;
                   state <= STATE_PREP_SEND;
                end
              else
                observe_count <= observe_count + 1'b1;
           end
         STATE_PREP_SEND:
           begin
              noc_reset <= 1'b1;
              send_index <= 0;
              crc_accumulator <= 0;
              state <= STATE_SEND;
           end
         STATE_SEND:
           if(record_ready)
             begin
                if(send_index < RECORD_BYTES-1)
                  begin
                     crc_accumulator
                       <= crc8_next(crc_accumulator, record_byte(send_index));
                     send_index <= send_index + 1'b1;
                  end
                else if(packet_index == PACKET_COUNT-1)
                  begin
                     done <= 1'b1;
                     state <= STATE_DONE;
                  end
                else
                  begin
                     packet_index <= packet_index + 1'b1;
                     reset_count <= 0;
                     state <= STATE_RESET_NOC;
                  end
             end
         default:
           begin
              noc_reset <= 1'b1;
              inject_valid <= 1'b0;
              done <= 1'b1;
              state <= STATE_DONE;
           end
       endcase

endmodule


module noc_ttv_phase18_clock
  (clk_100mhz, reset, clk_50mhz, locked);

   input clk_100mhz;
   input reset;
   output clk_50mhz;
   output locked;

`ifdef SYNTHESIS
   wire feedback_unbuffered;
   wire feedback_buffered;
   wire clock_unbuffered;

   MMCME2_BASE
     #(.BANDWIDTH("OPTIMIZED"), .CLKIN1_PERIOD(10.0),
       .DIVCLK_DIVIDE(1), .CLKFBOUT_MULT_F(10.0),
       .CLKOUT0_DIVIDE_F(20.0), .STARTUP_WAIT("FALSE"))
   mmcm
     (.CLKIN1(clk_100mhz), .RST(reset), .PWRDWN(1'b0),
      .CLKFBIN(feedback_buffered), .CLKFBOUT(feedback_unbuffered),
      .CLKOUT0(clock_unbuffered), .LOCKED(locked));

   BUFG feedback_buffer
     (.I(feedback_unbuffered), .O(feedback_buffered));
   BUFG output_buffer
     (.I(clock_unbuffered), .O(clk_50mhz));
`else
   reg divided_clock;
   always @(posedge clk_100mhz or posedge reset)
     if(reset)
       divided_clock <= 1'b0;
     else
       divided_clock <= ~divided_clock;
   assign clk_50mhz = divided_clock;
   assign locked = !reset;
`endif

endmodule


module noc_ttv_phase18_basys3_top
  #(parameter [0:63] PHYSICAL_SLOT_LABELS =
      64'b1110110100100001111111000011000010101011010001011001100001110110,
    parameter HEADER_DIM_ORDER = 0,
    parameter SWAP_DEST_XY = 0,
    parameter ROUTER_DIM_ORDER = 0,
    parameter [0:15] ROUTER_DIM_ORDER_MASK = 16'b0,
    parameter integer ROUTER_NUM_NODES = 16,
    parameter [0:63] HOST_LABELS =
      64'b1110110100100001111111000011000010101011010001011001100001110110,
    parameter [0:63] FABRIC_LABELS =
      64'b1110110100100001111111000011000010101011010001011001100001110110)
  (clk, btnC, RsTx, led);

   input clk;
   input btnC;
   output RsTx;
   output [15:0] led;

   wire noc_clock;
   wire clock_locked;
   /*
    * clock_locked is asynchronous to noc_clock. Assert reset immediately
    * when lock is lost, but release it only after four noc_clock edges.
    * This keeps combinational logic off the asynchronous reset tree and
    * makes reset removal deterministic on hardware.
    */
   (* ASYNC_REG = "TRUE" *) reg [3:0] reset_synchronizer = 4'b1111;
   wire probe_reset = reset_synchronizer[3];
   wire record_valid;
   wire record_ready;
   wire [7:0] record_data;
   wire done;
   wire [7:0] status;

   noc_ttv_phase18_clock clock_generator
     (.clk_100mhz(clk), .reset(btnC),
      .clk_50mhz(noc_clock), .locked(clock_locked));

   always @(posedge noc_clock or negedge clock_locked)
     if(!clock_locked)
       reset_synchronizer <= 4'b1111;
     else
       reset_synchronizer <= {reset_synchronizer[2:0], 1'b0};

   noc_ttv_phase18_probe
     #(.PHYSICAL_SLOT_LABELS(PHYSICAL_SLOT_LABELS),
       .HOST_LABELS(HOST_LABELS),
       .FABRIC_LABELS(FABRIC_LABELS),
       .HEADER_DIM_ORDER(HEADER_DIM_ORDER), .SWAP_DEST_XY(SWAP_DEST_XY),
       .ROUTER_DIM_ORDER(ROUTER_DIM_ORDER),
       .ROUTER_DIM_ORDER_MASK(ROUTER_DIM_ORDER_MASK),
       .ROUTER_NUM_NODES(ROUTER_NUM_NODES))
   probe
     (.clk(noc_clock), .reset(probe_reset),
      .record_valid(record_valid), .record_ready(record_ready),
      .record_data(record_data), .done(done), .status(status));

   noc_ttv_uart_tx
     #(.CLOCK_HZ(50000000), .BAUD(115200))
   transmitter
     (.clk(noc_clock), .reset(probe_reset),
      .data_valid(record_valid), .data_ready(record_ready),
      .data(record_data), .tx(RsTx));

   assign led[7:0] = status;
   assign led[8] = clock_locked;
   assign led[9] = done;
   assign led[15:10] = 0;

endmodule
