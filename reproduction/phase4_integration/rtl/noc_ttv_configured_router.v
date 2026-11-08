module noc_ttv_configured_router
  (clk,
   reset,
   physical_slot_labels,
   occupied,
   logical_source,
   logical_destination,
   payload,
   inject_valid,
   flow_ctrl_in_op,
   flow_ctrl_out_ip,
   channel_out_op,
   config_valid,
   router_error);

   input clk;
   input reset;
   input [0:63] physical_slot_labels;
   input [0:15] occupied;
   input [0:3] logical_source;
   input [0:3] logical_destination;
   input [0:24] payload;
   input inject_valid;
   input [0:14] flow_ctrl_in_op;
   output [0:14] flow_ctrl_out_ip;
   output [0:189] channel_out_op;
   output config_valid;
   output router_error;

   wire [0:3] physical_source;
   wire [0:3] physical_destination;
   wire [0:6] route_info;
   wire [0:4] route_op;
   wire [0:37] injection_channel;
   noc_ttv_configured_packet_injector injector
     (.physical_slot_labels(physical_slot_labels),
      .occupied(occupied),
      .logical_source(logical_source),
      .logical_destination(logical_destination),
      .payload(payload),
      .inject_valid(inject_valid),
      .physical_source(physical_source),
      .physical_destination(physical_destination),
      .route_info(route_info),
      .route_op(route_op),
      .channel(injection_channel),
      .config_valid(config_valid));

   noc_ttv_router_core core
     (.clk(clk),
      .reset(reset),
      .physical_router_address(physical_source),
      .injection_channel(injection_channel),
      .flow_ctrl_in_op(flow_ctrl_in_op),
      .flow_ctrl_out_ip(flow_ctrl_out_ip),
      .channel_out_op(channel_out_op),
      .router_error(router_error));

endmodule
