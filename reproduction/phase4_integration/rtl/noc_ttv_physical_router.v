module noc_ttv_physical_router
  (clk,
   reset,
   physical_source,
   physical_destination,
   payload,
   inject_valid,
   flow_ctrl_in_op,
   flow_ctrl_out_ip,
   channel_out_op,
   route_valid,
   router_error);

   input clk;
   input reset;
   input [0:3] physical_source;
   input [0:3] physical_destination;
   input [0:24] payload;
   input inject_valid;
   input [0:14] flow_ctrl_in_op;
   output [0:14] flow_ctrl_out_ip;
   output [0:189] channel_out_op;
   output route_valid;
   output router_error;

   wire [0:6] route_info;
   wire [0:4] route_op;
   wire [0:37] injection_channel;
   noc_ttv_physical_packet_injector injector
     (.physical_source(physical_source),
      .physical_destination(physical_destination),
      .payload(payload),
      .inject_valid(inject_valid),
      .route_info(route_info),
      .route_op(route_op),
      .channel(injection_channel),
      .route_valid(route_valid));

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
