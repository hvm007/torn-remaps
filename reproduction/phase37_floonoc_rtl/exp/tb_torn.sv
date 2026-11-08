// Torn-remap experiment on FlooNoC (AXI 4x4 mesh from floogen/examples/axi_mesh_xy.yml).
// Every cluster interface owns a run-time copy of the system address map (SAM); every subordinate
// port answers reads with its identity register (label of the region it believes it serves) and
// an epoch.  For each campaign and interruption point k the testbench applies the first k writes
// of the update (or all but write k), then issues the test reads and prints one record per read:
//   REC c k p src region port label epoch timeout
`include "axi/typedef.svh"
module tb_torn;
  import floo_pkg::*;
  import floo_axi_mesh_noc_pkg::*;
  `include "tb_data.svh"

  logic clk = 1'b0, rst_n = 1'b0;
  always #1 clk = ~clk;

  axi_in_req_t  [3:0][3:0] in_req;
  axi_in_rsp_t  [3:0][3:0] in_rsp;
  axi_out_req_t [3:0][3:0] cl_req;
  axi_out_rsp_t [3:0][3:0] cl_rsp;
  axi_out_req_t [3:0]      hbm_req;
  axi_out_rsp_t [3:0]      hbm_rsp;
  sam_rule_t [SamNumRules-1:0] sam [3:0][3:0];

  // identity registers of the 20 subordinate ports (cluster (x,y) -> 4x+y, HBM k -> 16+k)
  logic [4:0] id_label [20];
  logic [3:0] id_epoch [20];

  floo_axi_mesh_noc i_noc (
    .clk_i(clk), .rst_ni(rst_n), .test_enable_i(1'b0),
    .cluster_axi_in_req_i(in_req), .cluster_axi_in_rsp_o(in_rsp),
    .cluster_axi_out_req_o(cl_req), .cluster_axi_out_rsp_i(cl_rsp),
    .hbm_axi_out_req_o(hbm_req), .hbm_axi_out_rsp_i(hbm_rsp),
    .cluster_sam_i(sam));

  // ---------------------------------------------------------------- subordinate responders
  // One outstanding read per port: accept AR, answer one R beat carrying {port, epoch, label}.
  logic        busy [20];
  axi_out_id_t rid  [20];
  function automatic axi_out_req_t sreq(int p);
    return (p < 16) ? cl_req[p/4][p%4] : hbm_req[p-16];
  endfunction
  for (genvar p = 0; p < 20; p++) begin : gen_sbr
    axi_out_rsp_t rsp;
    always_comb begin
      rsp = '0;
      rsp.aw_ready = 1'b1; rsp.w_ready = 1'b1;
      rsp.ar_ready = !busy[p];
      rsp.r_valid  = busy[p];
      rsp.r.id     = rid[p];
      rsp.r.data   = {40'h0, 3'(0), 5'(p), 4'h0, id_epoch[p], 3'h0, id_label[p]};
      rsp.r.resp   = axi_pkg::RESP_OKAY;
      rsp.r.last   = 1'b1;
    end
    if (p < 16) begin : gen_cl
      assign cl_rsp[p/4][p%4] = rsp;
    end else begin : gen_hbm
      assign hbm_rsp[p-16] = rsp;
    end
    always_ff @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        busy[p] <= 1'b0; rid[p] <= '0;
      end else if (!busy[p] && sreq(p).ar_valid) begin
        busy[p] <= 1'b1; rid[p] <= sreq(p).ar.id;
      end else if (busy[p] && sreq(p).r_ready) begin
        busy[p] <= 1'b0;
      end
    end
  end

  // ---------------------------------------------------------------- torn-state application
  function automatic id_t port_id(int p);  // the generated SAM entry of region p names port p
    return Sam[p].idx;
  endfunction
  task automatic apply_state(int c, int k);
    int remap = CAMP_REMAP[c], order = CAMP_ORDER[c];
    bit written [64];
    for (int j = 0; j < 64; j++) written[j] = 1'b0;
    for (int j = 0; j < ORDER_LEN[order]; j++)
      if (CAMP_DROP[c] ? (j != k) : (j < k)) written[ORDER[order][j]] = 1'b1;
    for (int i = 0; i < 16; i++) begin                       // tables A_i
      sam[i/4][i%4] = Sam;
      if (written[i])
        for (int r = 0; r < 20; r++) sam[i/4][i%4][r].idx = port_id(TAU[remap][r]);
    end
    for (int p = 0; p < 20; p++) begin                       // registers B_p
      id_label[p] = 5'(p); id_epoch[p] = 4'd0;
      if (written[32 + p])
        for (int r = 0; r < 20; r++) if (TAU[remap][r] == p) begin
          id_label[p] = 5'(r); id_epoch[p] = 4'd1;
        end
    end
  endtask

  // ---------------------------------------------------------------- read driver
  task automatic do_read(int src, int region, output int port, output int label, output int epoch,
                         output bit timeout);
    int x = src / 4, y = src % 4, n;
    in_req[x][y].ar = '0;
    in_req[x][y].ar.addr  = Sam[region].start_addr;
    in_req[x][y].ar.size  = 3'd3;
    in_req[x][y].ar.burst = axi_pkg::BURST_INCR;
    in_req[x][y].ar_valid = 1'b1;
    timeout = 1'b0;
    for (n = 0; n < 400; n++) begin
      @(posedge clk);
      if (in_rsp[x][y].ar_ready) break;
    end
    @(negedge clk);
    in_req[x][y].ar_valid = 1'b0;
    in_req[x][y].r_ready  = 1'b1;
    for (n = 0; n < 400; n++) begin
      @(posedge clk);
      if (in_rsp[x][y].r_valid) break;
    end
    if (n == 400) timeout = 1'b1;
    port  = int'(in_rsp[x][y].r.data[20:16]);
    epoch = int'(in_rsp[x][y].r.data[11:8]);
    label = int'(in_rsp[x][y].r.data[4:0]);
    @(negedge clk);
    in_req[x][y].r_ready = 1'b0;
    repeat (4) @(negedge clk);
  endtask

  initial begin
    int port, label, epoch, kmax;
    bit to;
    in_req = '0;
    for (int i = 0; i < 16; i++) sam[i/4][i%4] = Sam;
    for (int p = 0; p < 20; p++) begin id_label[p] = 5'(p); id_epoch[p] = 4'd0; end
    repeat (5) @(negedge clk);
    rst_n = 1'b1;
    repeat (5) @(negedge clk);
    for (int c = 0; c < NCAMP; c++) begin
      kmax = CAMP_DROP[c] ? ORDER_LEN[CAMP_ORDER[c]] - 1 : ORDER_LEN[CAMP_ORDER[c]];
      for (int k = 0; k <= kmax; k++) begin
        apply_state(c, k);
        repeat (3) @(negedge clk);
        for (int p = 0; p < SUITE_LEN[CAMP_SUITE[c]]; p++) begin
          do_read(SUITE_SRC[CAMP_SUITE[c]][p], SUITE_REG[CAMP_SUITE[c]][p], port, label, epoch, to);
          $display("REC %0d %0d %0d %0d %0d %0d %0d %0d %0d", c, k, p, SUITE_SRC[CAMP_SUITE[c]][p],
                   SUITE_REG[CAMP_SUITE[c]][p], port, label, epoch, to);
        end
      end
    end
    $display("TORN_SIM_DONE");
    $finish;
  end
endmodule
