`timescale 1ns/1ps
module tb_p36;
   reg clk = 0; reg reset = 1;
   wire record_valid; wire [7:0] record_data; wire done; wire [7:0] status;
   integer byte_count = 0; integer watchdog;
   always #10 clk = ~clk;
   noc_ttv_p36_probe dut (.clk(clk), .reset(reset), .record_valid(record_valid),
      .record_ready(1'b1), .record_data(record_data), .done(done), .status(status));
   always @(posedge clk) if(record_valid) begin
      $display("UART_BYTE %02x", record_data); byte_count = byte_count + 1; end
   initial begin
      repeat(4) @(negedge clk); reset = 0;
      begin: w
         for(watchdog = 0; watchdog < 2000000; watchdog = watchdog + 1) begin
            @(negedge clk); if(done) disable w; end
      end
      if(!done) begin $display("P36_SIM_TIMEOUT bytes=%0d status=%02x", byte_count, status); $finish(2); end
      $display("P36_SIM_DONE bytes=%0d", byte_count); $finish(0);
   end
endmodule
