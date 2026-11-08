// Identity register of one endpoint, written by the update engine and read by test packets.
// EPOCH_W = 0 gives the plain label register; EPOCH_W > 0 adds an epoch tag.
module idreg #(parameter LABEL_W = 4, parameter EPOCH_W = 4)
  (input clk, input rst, input we, input [LABEL_W-1:0] label_in, input [(EPOCH_W>0?EPOCH_W:1)-1:0] epoch_in,
   output reg [LABEL_W-1:0] label, output reg [(EPOCH_W>0?EPOCH_W:1)-1:0] epoch);
   always @(posedge clk)
     if (rst) begin label <= 0; epoch <= 0; end
     else if (we) begin label <= label_in; if (EPOCH_W > 0) epoch <= epoch_in; end
endmodule
// Address table of one interface: 16 entries x 4-bit slot, one write port, one read port.
module addrtab #(parameter N = 16, parameter W = 4)
  (input clk, input we, input [3:0] waddr, input [W-1:0] wdata, input [3:0] raddr, output [W-1:0] rdata);
   reg [W-1:0] t [0:N-1];
   always @(posedge clk) if (we) t[waddr] <= wdata;
   assign rdata = t[raddr];
endmodule
