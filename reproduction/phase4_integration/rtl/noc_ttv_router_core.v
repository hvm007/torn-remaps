module noc_ttv_router_core
  (clk,
   reset,
   physical_router_address,
   injection_channel,
   flow_ctrl_in_op,
   flow_ctrl_out_ip,
   channel_out_op,
   router_error);

   input clk;
   input reset;
   input [0:3] physical_router_address;
   input [0:37] injection_channel;
   input [0:14] flow_ctrl_in_op;
   output [0:14] flow_ctrl_out_ip;
   output [0:189] channel_out_op;
   output router_error;

   wire [0:189] channel_in_ip;
   assign channel_in_ip[0:151] = {152{1'b0}};
   assign channel_in_ip[152:189] = injection_channel;

   router_slice
     #(.topology(0),
       .buffer_size(32),
       .num_message_classes(1),
       .num_resource_classes(1),
       .num_vcs_per_class(4),
       .num_nodes(16),
       .num_dimensions(2),
       .num_nodes_per_router(1),
       .packet_format(0),
       .flow_ctrl_type(0),
       .flow_ctrl_bypass(0),
       .max_payload_length(4),
       .min_payload_length(0),
       .router_type(1),
       .enable_link_pm(1),
       .flit_data_width(32),
       .error_capture_mode(1),
       .restrict_turns(1),
       .predecode_lar_info(1),
       .routing_type(0),
       .dim_order(0),
       .input_stage_can_hold(0),
       .fb_regfile_type(0),
       .fb_mgmt_type(0),
       .explicit_pipeline_register(0),
       .dual_path_alloc(0),
       .dual_path_allow_conflicts(0),
       .dual_path_mask_on_ready(1),
       .precomp_ivc_sel(0),
       .precomp_ip_sel(0),
       .elig_mask(1),
       .vc_alloc_type(0),
       .vc_alloc_arbiter_type(0),
       .vc_alloc_prefer_empty(0),
       .sw_alloc_type(0),
       .sw_alloc_arbiter_type(0),
       .sw_alloc_spec_type(1),
       .crossbar_type(0),
       .reset_type(0))
   router
     (.clk(clk),
      .reset(reset),
      .router_address(physical_router_address),
      .channel_in_ip(channel_in_ip),
      .flow_ctrl_out_ip(flow_ctrl_out_ip),
      .channel_out_op(channel_out_op),
      .flow_ctrl_in_op(flow_ctrl_in_op),
      .error(router_error));

endmodule
