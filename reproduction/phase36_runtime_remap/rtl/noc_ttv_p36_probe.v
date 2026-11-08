// Phase 36 -- runtime remap with real, sequential configuration writes.
//
// Unlike phases 31-35, nothing about the remap is a synthesis parameter.
// Every source network interface i has its own address table tbl[i]
// (slot -> label vector, 16 x 4 bits), every slot s has an identity
// register (4-bit label + 4-bit epoch).  An update engine writes the remap
// one component per clock cycle in a fixed order (table A_i = whole table,
// register B_s = label + epoch).  A campaign sweeps the interruption point k:
// for each k the state is reset to the old map, the first k writes are
// applied (or, in drop mode, every write except write k), and a test suite is
// sent.  One reset of the board runs every campaign and every k.
//
// Packets are addressed physically: source slot i, destination label l.
// The source's own table gives the destination slot d; the injector is driven
// with the identity slot->label vector so that logical == physical.
//
// Record (23 bytes): 'N''T''D''2', campaign, k, packet, {src,label_req},
// delivered slot, {epoch,label_reported}, flags, {table_dst,trace_len},
// 8 trace events, router_error, observation cycles, CRC-8.
// End record: 'N''T''E''2', record count (2 bytes), zeros, CRC-8.
module noc_ttv_p36_probe
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
   localparam integer RECORD_BYTES = 23;
   localparam integer NUM_CAMPAIGNS = 7;

   // old map (slot -> label), identical to every earlier phase
   localparam [0:63] OLD_MAP = 64'he_d_2_1_f_c_3_0_a_b_4_5_9_8_7_6;
   // R0: swap slots 0,1   R1: swap slots 0,1 and 5,12
   localparam [0:63] NEW_MAP0 = 64'hd_e_2_1_f_c_3_0_a_b_4_5_9_8_7_6;
   localparam [0:63] NEW_MAP1 = 64'hd_e_2_1_f_9_3_0_a_b_4_5_c_8_7_6;
   localparam [0:63] IDENTITY = 64'h0_1_2_3_4_5_6_7_8_9_a_b_c_d_e_f;

   localparam [3:0] S_RUN_INIT = 0;
   localparam [3:0] S_UPDATE = 1;
   localparam [3:0] S_LOOKUP = 2;
   localparam [3:0] S_RESET_NOC = 3;
   localparam [3:0] S_HEADER = 4;
   localparam [3:0] S_INJECT = 5;
   localparam [3:0] S_OBSERVE = 6;
   localparam [3:0] S_PREP_SEND = 7;
   localparam [3:0] S_SEND = 8;
   localparam [3:0] S_END_SEND = 9;
   localparam [3:0] S_DONE = 10;

   // ------------------------------------------------------------ ROMs
   // campaign -> {remap, order, suite, mode}
   function [0:0] camp_remap; input [2:0] c;
      case(c) 0,1,2: camp_remap = 0; default: camp_remap = 1; endcase
   endfunction
   function [1:0] camp_order; input [2:0] c;
      case(c) 0: camp_order = 0; 1,2: camp_order = 1; default: camp_order = 2; endcase
   endfunction
   function [2:0] camp_suite; input [2:0] c;
      case(c) 0,1: camp_suite = 0; 2: camp_suite = 1; 3: camp_suite = 2;
              4,6: camp_suite = 3; default: camp_suite = 4; endcase
   endfunction
   function camp_drop; input [2:0] c;
      camp_drop = (c == 6);
   endfunction
   function [4:0] order_len; input [1:0] o;
      order_len = (o == 2) ? 20 : 18;
   endfunction
   // component ids: 0..15 = table A_i, 16+s = register B_s
   function [4:0] order_item; input [1:0] o; input [4:0] j;
      begin
         order_item = 0;
         case(o)
           0: case(j)   // sentinel: B0 first, A7 last
                0: order_item = 16; 1: order_item = 0; 2: order_item = 1;
                3: order_item = 2; 4: order_item = 3; 5: order_item = 4;
                6: order_item = 5; 7: order_item = 6; 8: order_item = 8;
                9: order_item = 9; 10: order_item = 10; 11: order_item = 11;
                12: order_item = 12; 13: order_item = 13; 14: order_item = 14;
                15: order_item = 15; 16: order_item = 17; default: order_item = 7;
              endcase
           1: case(j)   // tables first (A2..A15, A0, A1), then B0, B1
                14: order_item = 0; 15: order_item = 1; 16: order_item = 16;
                17: order_item = 17; default: order_item = j + 2;
              endcase
           default: case(j)   // grouped: G1 tables, B0, B1, G2 tables, B5, B12
                0: order_item = 2; 1: order_item = 3; 2: order_item = 4;
                3: order_item = 5; 4: order_item = 6; 5: order_item = 7;
                6: order_item = 12; 7: order_item = 15; 8: order_item = 16;
                9: order_item = 17; 10: order_item = 0; 11: order_item = 1;
                12: order_item = 8; 13: order_item = 9; 14: order_item = 10;
                15: order_item = 11; 16: order_item = 13; 17: order_item = 14;
                18: order_item = 21; default: order_item = 28;
              endcase
         endcase
      end
   endfunction
   function [4:0] suite_len; input [2:0] s;
      case(s) 0: suite_len = 1; 1: suite_len = 2; 2: suite_len = 16;
              3: suite_len = 17; default: suite_len = 1; endcase
   endfunction
   // packet -> {source slot, destination label}
   function [7:0] suite_item; input [2:0] s; input [4:0] p;
      begin
         suite_item = 8'h7e;
         case(s)
           0: suite_item = 8'h7e;                       // (7,14)
           1: suite_item = (p == 0) ? 8'h7e : 8'h2d;    // (7,14), (2,13)
           4: suite_item = 8'h8d;                       // witness (8,13)
           default: case(p)                             // split / bridged
                0: suite_item = 8'h2e; 1: suite_item = 8'h3d; 2: suite_item = 8'h4e;
                3: suite_item = 8'h5d; 4: suite_item = 8'h6e; 5: suite_item = 8'h7d;
                6: suite_item = 8'hce; 7: suite_item = 8'hfd; 8: suite_item = 8'h0c;
                9: suite_item = 8'h19; 10: suite_item = 8'h8c; 11: suite_item = 8'h99;
                12: suite_item = 8'hac; 13: suite_item = 8'hb9; 14: suite_item = 8'hdc;
                15: suite_item = 8'he9; default: suite_item = 8'h2c;  // bridge (2,12)
              endcase
         endcase
      end
   endfunction

   // ------------------------------------------------------------ state
   reg [3:0] state;
   reg [0:63] tbl [0:15];
   reg [3:0] id_label [0:15];
   reg [3:0] id_epoch [0:15];
   reg [2:0] campaign;
   reg [4:0] k;
   reg [4:0] j;
   reg [4:0] pkt;
   reg [3:0] dst_slot;
   reg [15:0] record_count;

   reg noc_reset;
   reg inject_valid;
   reg [2:0] reset_count;
   reg [6:0] observe_count;
   reg [4:0] send_index;
   reg [7:0] crc_accumulator;
   reg captured_config_valid;
   reg captured_delivered_valid;
   reg [3:0] captured_delivered_physical;
   reg [3:0] captured_label;
   reg [3:0] captured_epoch;
   reg captured_timeout;
   reg trace_overflow;
   reg [3:0] trace_length;
   reg [6:0] trace_events [0:TRACE_CAPACITY-1];
   reg [15:0] router_error_seen;
   reg [7:0] captured_observation_cycles;
   integer n;

   wire remap = camp_remap(campaign);
   wire [1:0] order = camp_order(campaign);
   wire [2:0] suite = camp_suite(campaign);
   wire drop = camp_drop(campaign);
   wire [4:0] olen = order_len(order);
   wire [4:0] kmax = drop ? olen - 1 : olen;
   wire [4:0] slen = suite_len(suite);
   wire [7:0] item = suite_item(suite, pkt);
   wire [3:0] src_slot = item[7:4];
   wire [3:0] req_label = item[3:0];
   wire [0:63] new_map = remap ? NEW_MAP1 : NEW_MAP0;
   wire [4:0] comp = order_item(order, j);
   wire apply_write = drop ? (j != k) : (j < k);
   wire [0:63] src_table = tbl[src_slot];
   wire last_packet = (pkt == slen - 1);
   wire last_run = last_packet && (k == kmax);

   // destination slot from the source's own table
   reg [3:0] lookup_slot;
   integer q;
   always @* begin
      lookup_slot = 0;
      for(q = 15; q >= 0; q = q - 1)
        if(src_table[q*4 +: 4] == req_label) lookup_slot = q;
   end

   // ------------------------------------------------------------ NoC
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

   always @* begin
      active_trace_count = 0; active_trace_event = 0;
      for(trace_scan = 0; trace_scan < 80; trace_scan = trace_scan + 1)
        if(trace_valid[trace_scan]) begin
           active_trace_count = active_trace_count + 1'b1;
           active_trace_event = ((trace_scan / 5) << 3) | (trace_scan % 5);
        end
   end
   always @* begin
      active_delivery_count = 0; active_delivery_slot = 0;
      for(delivery_scan = 0; delivery_scan < 16; delivery_scan = delivery_scan + 1)
        if(ejection[delivery_scan][1]) begin
           active_delivery_count = active_delivery_count + 1'b1;
           active_delivery_slot = delivery_scan;
        end
   end

   noc_ttv_configured_packet_injector
     #(.VC_INDEX_WIDTH(VC_INDEX_WIDTH), .HEADER_DIM_ORDER(0), .SWAP_DEST_XY(0))
   injector
     (.physical_slot_labels(IDENTITY), .occupied(16'hffff),
      .logical_source(src_slot), .logical_destination(dst_slot),
      .payload(25'h15555), .inject_valid(inject_valid),
      .physical_source(physical_source), .physical_destination(physical_destination),
      .route_info(route_info), .route_op(route_op), .channel(packet_channel),
      .config_valid(config_valid));

   genvar endpoint;
   generate
      for(endpoint = 0; endpoint < 16; endpoint = endpoint + 1) begin: endpoints
         assign injection_channels[endpoint*CHANNEL_WIDTH +: CHANNEL_WIDTH]
           = physical_source == endpoint ? packet_channel : {CHANNEL_WIDTH{1'b0}};
         assign ejection[endpoint] = ejection_channels[endpoint*CHANNEL_WIDTH +: CHANNEL_WIDTH];
         assign ejection_flow_ctrl[endpoint*FLOW_CTRL_WIDTH +: FLOW_CTRL_WIDTH]
           = {ejection[endpoint][1], ejection[endpoint][2 +: VC_INDEX_WIDTH]};
      end
   endgenerate

   noc_ttv_observed_mesh_4x4
     #(.ROUTER_BUFFER_SIZE(4), .ROUTER_IMPLEMENTATION(2), .NUM_VCS(NUM_VCS),
       .VC_INDEX_WIDTH(VC_INDEX_WIDTH), .DIM_ORDER(0), .ROUTER_DIM_ORDER_MASK(16'b0))
   mesh
     (.clk(clk), .reset(noc_reset),
      .injection_channels(injection_channels), .injection_flow_ctrl(injection_flow_ctrl),
      .ejection_channels(ejection_channels), .ejection_flow_ctrl(ejection_flow_ctrl),
      .router_error(router_error), .trace_valid(trace_valid));

   // ------------------------------------------------------------ records
   function [7:0] crc8_next; input [7:0] prior; input [7:0] value;
      integer b; reg [7:0] w;
      begin
         w = prior ^ value;
         for(b = 0; b < 8; b = b + 1) w = w[7] ? ((w << 1) ^ 8'h07) : (w << 1);
         crc8_next = w;
      end
   endfunction
   function [7:0] trace_byte; input [2:0] index;
      trace_byte = (index < trace_length) ? {1'b0, trace_events[index]} : 8'd0;
   endfunction
   function [7:0] record_byte; input [4:0] index;
      begin
         if(state == S_END_SEND)
           case(index)
             0: record_byte = "N"; 1: record_byte = "T"; 2: record_byte = "E"; 3: record_byte = "2";
             4: record_byte = record_count[15:8]; 5: record_byte = record_count[7:0];
             22: record_byte = crc_accumulator; default: record_byte = 0;
           endcase
         else
           case(index)
             0: record_byte = "N"; 1: record_byte = "T"; 2: record_byte = "D"; 3: record_byte = "2";
             4: record_byte = {5'b0, campaign};
             5: record_byte = {3'b0, k};
             6: record_byte = {3'b0, pkt};
             7: record_byte = {src_slot, req_label};
             8: record_byte = captured_delivered_valid ? {4'b0, captured_delivered_physical} : 8'hff;
             9: record_byte = captured_delivered_valid ? {captured_epoch, captured_label} : 8'hff;
             10: record_byte = {2'b0, last_run, last_packet, |router_error_seen, captured_timeout,
                                captured_delivered_valid, captured_config_valid};
             11: record_byte = {dst_slot, trace_length};
             12: record_byte = trace_byte(0); 13: record_byte = trace_byte(1);
             14: record_byte = trace_byte(2); 15: record_byte = trace_byte(3);
             16: record_byte = trace_byte(4); 17: record_byte = trace_byte(5);
             18: record_byte = trace_byte(6); 19: record_byte = trace_byte(7);
             20: record_byte = {trace_overflow, 6'b0, |router_error_seen};
             21: record_byte = captured_observation_cycles;
             default: record_byte = crc_accumulator;
           endcase
      end
   endfunction

   assign record_valid = (state == S_SEND) || (state == S_END_SEND);
   assign record_data = record_byte(send_index);
   assign status = {campaign, k};

   always @(posedge clk or posedge reset)
     if(reset) begin
        state <= S_RUN_INIT;
        campaign <= 0; k <= 0; j <= 0; pkt <= 0; dst_slot <= 0;
        record_count <= 0; noc_reset <= 1'b1; inject_valid <= 1'b0;
        reset_count <= 0; observe_count <= 0; send_index <= 0; crc_accumulator <= 0;
        captured_config_valid <= 0; captured_delivered_valid <= 0;
        captured_delivered_physical <= 0; captured_label <= 0; captured_epoch <= 0;
        captured_timeout <= 0; trace_overflow <= 0; trace_length <= 0;
        router_error_seen <= 0; captured_observation_cycles <= 0; done <= 1'b0;
        for(n = 0; n < 16; n = n + 1) begin
           tbl[n] <= OLD_MAP; id_label[n] <= OLD_MAP[n*4 +: 4]; id_epoch[n] <= 0;
        end
        for(n = 0; n < TRACE_CAPACITY; n = n + 1) trace_events[n] <= 0;
     end
     else
       case(state)
         S_RUN_INIT: begin              // every run starts from the old map
            for(n = 0; n < 16; n = n + 1) begin
               tbl[n] <= OLD_MAP; id_label[n] <= OLD_MAP[n*4 +: 4]; id_epoch[n] <= 0;
            end
            j <= 0; pkt <= 0; noc_reset <= 1'b1;
            state <= S_UPDATE;
         end
         S_UPDATE: begin                // one configuration write per cycle
            if(j == olen)
              state <= S_LOOKUP;
            else begin
               if(apply_write) begin
                  if(comp[4]) begin
                     id_label[comp[3:0]] <= new_map[comp[3:0]*4 +: 4];
                     id_epoch[comp[3:0]] <= 4'd1;
                  end
                  else
                    tbl[comp[3:0]] <= new_map;
               end
               j <= j + 1'b1;
            end
         end
         S_LOOKUP: begin
            dst_slot <= lookup_slot;
            reset_count <= 0;
            state <= S_RESET_NOC;
         end
         S_RESET_NOC: begin
            noc_reset <= 1'b1; inject_valid <= 1'b0; observe_count <= 0;
            captured_delivered_valid <= 0; captured_delivered_physical <= 0;
            captured_label <= 0; captured_epoch <= 0; captured_timeout <= 0;
            trace_overflow <= 0; trace_length <= 0; router_error_seen <= 0;
            captured_observation_cycles <= 0;
            if(reset_count == 5) begin
               reset_count <= 0; noc_reset <= 1'b0; state <= S_HEADER;
            end
            else reset_count <= reset_count + 1'b1;
         end
         S_HEADER: begin
            captured_config_valid <= config_valid;
            if(config_valid) begin inject_valid <= 1'b1; state <= S_INJECT; end
            else state <= S_PREP_SEND;
         end
         S_INJECT: begin
            inject_valid <= 1'b0; router_error_seen <= router_error; state <= S_OBSERVE;
         end
         S_OBSERVE: begin
            router_error_seen <= router_error_seen | router_error;
            if(active_trace_count != 0) begin
               if(active_trace_count != 1 || trace_length >= TRACE_CAPACITY) trace_overflow <= 1'b1;
               else begin
                  trace_events[trace_length] <= active_trace_event;
                  trace_length <= trace_length + 1'b1;
               end
            end
            if(active_delivery_count != 0) begin
               if(active_delivery_count != 1) trace_overflow <= 1'b1;
               captured_delivered_valid <= 1'b1;
               captured_delivered_physical <= active_delivery_slot;
               captured_label <= id_label[active_delivery_slot];
               captured_epoch <= id_epoch[active_delivery_slot];
               captured_observation_cycles <= observe_count + 1'b1;
               state <= S_PREP_SEND;
            end
            else if(observe_count == 95) begin
               captured_timeout <= 1'b1; captured_observation_cycles <= 96; state <= S_PREP_SEND;
            end
            else observe_count <= observe_count + 1'b1;
         end
         S_PREP_SEND: begin
            noc_reset <= 1'b1; send_index <= 0; crc_accumulator <= 0; state <= S_SEND;
         end
         S_SEND:
           if(record_ready) begin
              if(send_index < RECORD_BYTES-1) begin
                 crc_accumulator <= crc8_next(crc_accumulator, record_byte(send_index));
                 send_index <= send_index + 1'b1;
              end
              else begin
                 record_count <= record_count + 1'b1;
                 if(!last_packet) begin
                    pkt <= pkt + 1'b1; state <= S_LOOKUP;
                 end
                 else if(k != kmax) begin
                    k <= k + 1'b1; state <= S_RUN_INIT;
                 end
                 else if(campaign != NUM_CAMPAIGNS-1) begin
                    campaign <= campaign + 1'b1; k <= 0; state <= S_RUN_INIT;
                 end
                 else begin
                    send_index <= 0; crc_accumulator <= 0; state <= S_END_SEND;
                 end
              end
           end
         S_END_SEND:
           if(record_ready) begin
              if(send_index < RECORD_BYTES-1) begin
                 crc_accumulator <= crc8_next(crc_accumulator, record_byte(send_index));
                 send_index <= send_index + 1'b1;
              end
              else begin done <= 1'b1; state <= S_DONE; end
           end
         default: begin noc_reset <= 1'b1; inject_valid <= 1'b0; done <= 1'b1; end
       endcase
endmodule

module noc_ttv_p36_clock (clk_100mhz, reset, clk_50mhz, locked);
   input clk_100mhz; input reset; output clk_50mhz; output locked;
`ifdef SYNTHESIS
   wire feedback_unbuffered, feedback_buffered, clock_unbuffered;
   MMCME2_BASE #(.BANDWIDTH("OPTIMIZED"), .CLKIN1_PERIOD(10.0), .DIVCLK_DIVIDE(1),
                 .CLKFBOUT_MULT_F(10.0), .CLKOUT0_DIVIDE_F(20.0), .STARTUP_WAIT("FALSE"))
   mmcm (.CLKIN1(clk_100mhz), .RST(reset), .PWRDWN(1'b0), .CLKFBIN(feedback_buffered),
         .CLKFBOUT(feedback_unbuffered), .CLKOUT0(clock_unbuffered), .LOCKED(locked));
   BUFG feedback_buffer (.I(feedback_unbuffered), .O(feedback_buffered));
   BUFG output_buffer (.I(clock_unbuffered), .O(clk_50mhz));
`else
   reg divided_clock;
   always @(posedge clk_100mhz or posedge reset)
     if(reset) divided_clock <= 1'b0; else divided_clock <= ~divided_clock;
   assign clk_50mhz = divided_clock;
   assign locked = !reset;
`endif
endmodule

// Board top: same pins as phases 31-35 (clk, btnC, RsTx, led).
module noc_ttv_p36_basys3_top (clk, btnC, RsTx, led);
   input clk; input btnC; output RsTx; output [15:0] led;
   wire noc_clock, clock_locked;
   (* ASYNC_REG = "TRUE" *) reg [3:0] reset_synchronizer = 4'b1111;
   wire probe_reset = reset_synchronizer[3];
   wire record_valid, record_ready, done;
   wire [7:0] record_data, status;
   noc_ttv_p36_clock clock_generator
     (.clk_100mhz(clk), .reset(btnC), .clk_50mhz(noc_clock), .locked(clock_locked));
   always @(posedge noc_clock or negedge clock_locked)
     if(!clock_locked) reset_synchronizer <= 4'b1111;
     else reset_synchronizer <= {reset_synchronizer[2:0], 1'b0};
   noc_ttv_p36_probe probe
     (.clk(noc_clock), .reset(probe_reset), .record_valid(record_valid),
      .record_ready(record_ready), .record_data(record_data), .done(done), .status(status));
   noc_ttv_uart_tx #(.CLOCK_HZ(50000000), .BAUD(115200)) transmitter
     (.clk(noc_clock), .reset(probe_reset), .data_valid(record_valid),
      .data_ready(record_ready), .data(record_data), .tx(RsTx));
   assign led[7:0] = status;
   assign led[8] = clock_locked;
   assign led[9] = done;
   assign led[15:10] = 0;
endmodule
