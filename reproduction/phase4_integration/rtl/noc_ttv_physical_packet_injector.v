module noc_ttv_physical_packet_injector
  #(parameter [0:1] VC_ID = 2'b00,
    parameter VC_INDEX_WIDTH = 2,
    parameter HEADER_DIM_ORDER = 0,
    parameter SWAP_DEST_XY = 0)
  (physical_source,
   physical_destination,
   payload,
   inject_valid,
   route_info,
   route_op,
   channel,
   route_valid);

   input [0:3] physical_source;
   input [0:3] physical_destination;
   input [0:24] payload;
   input inject_valid;
   output [0:6] route_info;
   output [0:4] route_op;
   output [0:35+VC_INDEX_WIDTH] channel;
   output route_valid;

   noc_ttv_physical_header_encoder
     #(.DIM_ORDER(HEADER_DIM_ORDER),
       .SWAP_DEST_XY(SWAP_DEST_XY))
   header
     (.physical_source(physical_source),
      .physical_destination(physical_destination),
      .route_info(route_info),
      .route_op(route_op),
      .route_valid(route_valid));

   noc_ttv_channel_pack
     #(.VC_ID(VC_ID),
       .VC_INDEX_WIDTH(VC_INDEX_WIDTH))
   pack
     (.route_info(route_info),
      .payload(payload),
      .inject_valid(inject_valid),
      .contract_valid(route_valid),
      .channel(channel));

endmodule
