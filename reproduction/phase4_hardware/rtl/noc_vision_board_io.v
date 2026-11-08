module noc_ttv_uart_tx
  #(parameter integer CLOCK_HZ = 100000000,
    parameter integer BAUD = 115200)
  (clk, reset, data_valid, data_ready, data, tx);

   input clk;
   input reset;
   input data_valid;
   output data_ready;
   input [7:0] data;
   output tx;

   localparam integer CLKS_PER_BIT = CLOCK_HZ / BAUD;
   reg [9:0] shift_register;
   reg [31:0] baud_counter;
   reg [3:0] bits_remaining;
   reg busy;

   assign data_ready = !busy;
   assign tx = busy ? shift_register[0] : 1'b1;

   always @(posedge clk or posedge reset)
     if(reset)
       begin
          shift_register <= 10'h3ff;
          baud_counter <= 0;
          bits_remaining <= 0;
          busy <= 1'b0;
       end
     else if(!busy)
       begin
          if(data_valid)
            begin
               // LSB first: one start bit, eight data bits, one stop bit.
               shift_register <= {1'b1, data, 1'b0};
               baud_counter <= CLKS_PER_BIT-1;
               bits_remaining <= 10;
               busy <= 1'b1;
            end
       end
     else if(baud_counter != 0)
       baud_counter <= baud_counter - 1'b1;
     else
       begin
          shift_register <= {1'b1, shift_register[9:1]};
          baud_counter <= CLKS_PER_BIT-1;
          if(bits_remaining == 1)
            begin
               bits_remaining <= 0;
               busy <= 1'b0;
            end
          else
            bits_remaining <= bits_remaining - 1'b1;
       end

endmodule

module noc_ttv_uart_rx
  #(parameter integer CLOCK_HZ = 100000000,
    parameter integer BAUD = 115200)
  (clk, reset, rx, data_valid, data, framing_error);

   input clk;
   input reset;
   input rx;
   output reg data_valid;
   output reg [7:0] data;
   output reg framing_error;

   localparam integer CLKS_PER_BIT = CLOCK_HZ / BAUD;
   localparam [1:0] STATE_IDLE = 0;
   localparam [1:0] STATE_DATA = 1;
   localparam [1:0] STATE_STOP = 2;
   reg rx_meta;
   reg rx_sync;
   reg [1:0] state;
   reg [31:0] baud_counter;
   reg [2:0] bit_index;

   always @(posedge clk or posedge reset)
     if(reset)
       begin
          rx_meta <= 1'b1;
          rx_sync <= 1'b1;
          state <= STATE_IDLE;
          baud_counter <= 0;
          bit_index <= 0;
          data_valid <= 1'b0;
          data <= 0;
          framing_error <= 1'b0;
       end
     else
       begin
          rx_meta <= rx;
          rx_sync <= rx_meta;
          data_valid <= 1'b0;
          case(state)
            STATE_IDLE:
              if(!rx_sync)
                begin
                   state <= STATE_DATA;
                   bit_index <= 0;
                   baud_counter <= CLKS_PER_BIT + (CLKS_PER_BIT/2) - 1;
                end
            STATE_DATA:
              if(baud_counter != 0)
                baud_counter <= baud_counter - 1'b1;
              else
                begin
                   data[bit_index] <= rx_sync;
                   baud_counter <= CLKS_PER_BIT-1;
                   if(bit_index == 7)
                     state <= STATE_STOP;
                   else
                     bit_index <= bit_index + 1'b1;
                end
            default:
              if(baud_counter != 0)
                baud_counter <= baud_counter - 1'b1;
              else
                begin
                   if(rx_sync)
                     data_valid <= 1'b1;
                   else
                     framing_error <= 1'b1;
                   state <= STATE_IDLE;
                end
          endcase
       end

endmodule

module noc_vision_uart_frame_loader
  #(parameter integer FRAME_WIDTH = 320,
    parameter integer FRAME_HEIGHT = 240)
  (clk, reset, byte_valid, byte_data, framing_error,
   frame_write_valid, frame_write_address, frame_write_data,
   expected_crc, frame_ready, protocol_error);

   input clk;
   input reset;
   input byte_valid;
   input [7:0] byte_data;
   input framing_error;
   output reg frame_write_valid;
   output reg [16:0] frame_write_address;
   output reg [7:0] frame_write_data;
   output reg [31:0] expected_crc;
   output reg frame_ready;
   output reg protocol_error;

   localparam integer FRAME_PIXELS = FRAME_WIDTH * FRAME_HEIGHT;
   localparam [1:0] PHASE_HEADER = 0;
   localparam [1:0] PHASE_CRC = 1;
   localparam [1:0] PHASE_PIXELS = 2;
   localparam [1:0] PHASE_DONE = 3;
   reg [1:0] phase;
   reg [1:0] field_index;
   reg [16:0] pixel_index;

   function [7:0] header_byte;
      input [1:0] index;
      begin
         case(index)
           0: header_byte = "N";
           1: header_byte = "T";
           2: header_byte = "V";
           default: header_byte = "I";
         endcase
      end
   endfunction

   always @(posedge clk or posedge reset)
     if(reset)
       begin
          frame_write_valid <= 1'b0;
          frame_write_address <= 0;
          frame_write_data <= 0;
          expected_crc <= 0;
          frame_ready <= 1'b0;
          protocol_error <= 1'b0;
          phase <= PHASE_HEADER;
          field_index <= 0;
          pixel_index <= 0;
       end
     else
       begin
          frame_write_valid <= 1'b0;
          if(framing_error)
            protocol_error <= 1'b1;
          if(byte_valid)
            case(phase)
              PHASE_HEADER:
                if(byte_data == header_byte(field_index))
                  begin
                     if(field_index == 3)
                       begin
                          field_index <= 0;
                          phase <= PHASE_CRC;
                       end
                     else
                       field_index <= field_index + 1'b1;
                  end
                else
                  begin
                     protocol_error <= 1'b1;
                     field_index <= byte_data == "N" ? 1 : 0;
                  end
              PHASE_CRC:
                begin
                   case(field_index)
                     0: expected_crc[31:24] <= byte_data;
                     1: expected_crc[23:16] <= byte_data;
                     2: expected_crc[15:8] <= byte_data;
                     default: expected_crc[7:0] <= byte_data;
                   endcase
                   if(field_index == 3)
                     begin
                        field_index <= 0;
                        frame_write_address <= 0;
                        pixel_index <= 0;
                        phase <= PHASE_PIXELS;
                     end
                   else
                     field_index <= field_index + 1'b1;
                end
              PHASE_PIXELS:
                begin
                   frame_write_valid <= 1'b1;
                   frame_write_address <= pixel_index;
                   frame_write_data <= byte_data;
                   if(pixel_index == FRAME_PIXELS-1)
                     begin
                        frame_ready <= 1'b1;
                        phase <= PHASE_DONE;
                     end
                   else
                     pixel_index <= pixel_index + 1'b1;
                end
              default: protocol_error <= 1'b1;
            endcase
       end

endmodule

module noc_vision_result_uart
  #(parameter integer CLOCK_HZ = 100000000,
    parameter integer BAUD = 115200)
  (clk, reset, done, pass, status, frame_crc, cycle_count, packet_count,
   tx, report_sent);

   input clk;
   input reset;
   input done;
   input pass;
   input [7:0] status;
   input [31:0] frame_crc;
   input [31:0] cycle_count;
   input [31:0] packet_count;
   output tx;
   output reg report_sent;

   reg done_delayed;
   reg active;
   reg [5:0] byte_index;
   reg captured_pass;
   reg [7:0] captured_status;
   reg [31:0] captured_crc;
   reg [31:0] captured_cycles;
   reg [31:0] captured_packets;
   wire uart_ready;
   wire uart_valid = active;
   wire [7:0] uart_data = report_byte(byte_index);

   function [7:0] hex_character;
      input [3:0] nibble;
      begin
         if(nibble < 10)
           hex_character = "0" + nibble;
         else
           hex_character = "A" + nibble - 10;
      end
   endfunction

   // Fixed 48-byte ASCII record:
   // NTV1 P=1 S=40 C=458F7DFD Y=00000000 N=00012350\r\n
   function [7:0] report_byte;
      input [5:0] index;
      begin
         case(index)
           0: report_byte = "N";
           1: report_byte = "T";
           2: report_byte = "V";
           3: report_byte = "1";
           4: report_byte = " ";
           5: report_byte = "P";
           6: report_byte = "=";
           7: report_byte = captured_pass ? "1" : "0";
           8: report_byte = " ";
           9: report_byte = "S";
           10: report_byte = "=";
           11: report_byte = hex_character(captured_status[7:4]);
           12: report_byte = hex_character(captured_status[3:0]);
           13: report_byte = " ";
           14: report_byte = "C";
           15: report_byte = "=";
           16: report_byte = hex_character(captured_crc[31:28]);
           17: report_byte = hex_character(captured_crc[27:24]);
           18: report_byte = hex_character(captured_crc[23:20]);
           19: report_byte = hex_character(captured_crc[19:16]);
           20: report_byte = hex_character(captured_crc[15:12]);
           21: report_byte = hex_character(captured_crc[11:8]);
           22: report_byte = hex_character(captured_crc[7:4]);
           23: report_byte = hex_character(captured_crc[3:0]);
           24: report_byte = " ";
           25: report_byte = "Y";
           26: report_byte = "=";
           27: report_byte = hex_character(captured_cycles[31:28]);
           28: report_byte = hex_character(captured_cycles[27:24]);
           29: report_byte = hex_character(captured_cycles[23:20]);
           30: report_byte = hex_character(captured_cycles[19:16]);
           31: report_byte = hex_character(captured_cycles[15:12]);
           32: report_byte = hex_character(captured_cycles[11:8]);
           33: report_byte = hex_character(captured_cycles[7:4]);
           34: report_byte = hex_character(captured_cycles[3:0]);
           35: report_byte = " ";
           36: report_byte = "N";
           37: report_byte = "=";
           38: report_byte = hex_character(captured_packets[31:28]);
           39: report_byte = hex_character(captured_packets[27:24]);
           40: report_byte = hex_character(captured_packets[23:20]);
           41: report_byte = hex_character(captured_packets[19:16]);
           42: report_byte = hex_character(captured_packets[15:12]);
           43: report_byte = hex_character(captured_packets[11:8]);
           44: report_byte = hex_character(captured_packets[7:4]);
           45: report_byte = hex_character(captured_packets[3:0]);
           46: report_byte = 8'h0d;
           default: report_byte = 8'h0a;
         endcase
      end
   endfunction

   noc_ttv_uart_tx
     #(.CLOCK_HZ(CLOCK_HZ), .BAUD(BAUD))
   uart
     (.clk(clk), .reset(reset), .data_valid(uart_valid),
      .data_ready(uart_ready), .data(uart_data), .tx(tx));

   always @(posedge clk or posedge reset)
     if(reset)
       begin
          done_delayed <= 1'b0;
          active <= 1'b0;
          byte_index <= 0;
          captured_pass <= 1'b0;
          captured_status <= 0;
          captured_crc <= 0;
          captured_cycles <= 0;
          captured_packets <= 0;
          report_sent <= 1'b0;
       end
     else
       begin
          done_delayed <= done;
          if(done && !done_delayed && !active && !report_sent)
            begin
               captured_pass <= pass;
               captured_status <= status;
               captured_crc <= frame_crc;
               captured_cycles <= cycle_count;
               captured_packets <= packet_count;
               byte_index <= 0;
               active <= 1'b1;
            end
          else if(active && uart_ready)
            begin
               if(byte_index == 47)
                 begin
                    active <= 1'b0;
                    report_sent <= 1'b1;
                 end
               else
                 byte_index <= byte_index + 1'b1;
            end
       end

endmodule

module noc_vision_vga_scanout
  #(parameter integer PIXEL_DIVIDE = 4,
    parameter integer H_VISIBLE = 640,
    parameter integer H_FRONT = 16,
    parameter integer H_SYNC = 96,
    parameter integer H_BACK = 48,
    parameter integer V_VISIBLE = 480,
    parameter integer V_FRONT = 10,
    parameter integer V_SYNC = 2,
    parameter integer V_BACK = 33,
    parameter integer SCALE_SHIFT = 1,
    parameter integer FRAME_WIDTH = 320)
  (clk, reset, display_enable, frame_data, frame_address,
   source_x, source_y, display_active,
   vgaRed, vgaGreen, vgaBlue, Hsync, Vsync);

   input clk;
   input reset;
   input display_enable;
   input [7:0] frame_data;
   output [16:0] frame_address;
   output [8:0] source_x;
   output [7:0] source_y;
   output display_active;
   output reg [3:0] vgaRed;
   output reg [3:0] vgaGreen;
   output reg [3:0] vgaBlue;
   output reg Hsync;
   output reg Vsync;

   localparam integer H_TOTAL = H_VISIBLE + H_FRONT + H_SYNC + H_BACK;
   localparam integer V_TOTAL = V_VISIBLE + V_FRONT + V_SYNC + V_BACK;
   reg [9:0] horizontal_count;
   reg [9:0] vertical_count;
   reg [7:0] pixel_divider;
   wire pixel_tick = pixel_divider == PIXEL_DIVIDE-1;
   wire visible_now
     = horizontal_count < H_VISIBLE && vertical_count < V_VISIBLE;
   wire hsync_now
     = !((horizontal_count >= H_VISIBLE+H_FRONT) &&
         (horizontal_count < H_VISIBLE+H_FRONT+H_SYNC));
   wire vsync_now
     = !((vertical_count >= V_VISIBLE+V_FRONT) &&
         (vertical_count < V_VISIBLE+V_FRONT+V_SYNC));

   assign source_x = horizontal_count >> SCALE_SHIFT;
   assign source_y = vertical_count >> SCALE_SHIFT;
   assign frame_address = source_y * FRAME_WIDTH + source_x;
   assign display_active = visible_now;

   always @(posedge clk or posedge reset)
     if(reset)
       begin
          horizontal_count <= 0;
          vertical_count <= 0;
          pixel_divider <= 0;
          vgaRed <= 0;
          vgaGreen <= 0;
          vgaBlue <= 0;
          Hsync <= 1'b1;
          Vsync <= 1'b1;
       end
     else
       begin
          if(pixel_tick)
            begin
               pixel_divider <= 0;
               Hsync <= hsync_now;
               Vsync <= vsync_now;
               if(visible_now && display_enable)
                 begin
                    vgaRed <= frame_data[7:4];
                    vgaGreen <= frame_data[7:4];
                    vgaBlue <= frame_data[7:4];
                 end
               else
                 begin
                    vgaRed <= 0;
                    vgaGreen <= 0;
                    vgaBlue <= 0;
                 end
               if(horizontal_count == H_TOTAL-1)
                 begin
                    horizontal_count <= 0;
                    if(vertical_count == V_TOTAL-1)
                      vertical_count <= 0;
                    else
                      vertical_count <= vertical_count + 1'b1;
                 end
               else
                 horizontal_count <= horizontal_count + 1'b1;
            end
          else
            pixel_divider <= pixel_divider + 1'b1;
       end

endmodule
