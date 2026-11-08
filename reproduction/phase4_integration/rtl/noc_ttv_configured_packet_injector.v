module noc_ttv_configured_packet_injector
  #(parameter [0:1] VC_ID = 2'b00,
    parameter VC_INDEX_WIDTH = 2,
    parameter HEADER_DIM_ORDER = 0,
    parameter SWAP_DEST_XY = 0)
  (physical_slot_labels,
   occupied,
   logical_source,
   logical_destination,
   payload,
   inject_valid,
   physical_source,
   physical_destination,
   route_info,
   route_op,
   channel,
   config_valid);

   input [0:63] physical_slot_labels;
   input [0:15] occupied;
   input [0:3] logical_source;
   input [0:3] logical_destination;
   input [0:24] payload;
   input inject_valid;
   output [0:3] physical_source;
   output [0:3] physical_destination;
   output [0:6] route_info;
   output [0:4] route_op;
   output [0:35+VC_INDEX_WIDTH] channel;
   output config_valid;

   wire source_found;
   wire destination_found;
   wire source_ambiguous;
   wire destination_ambiguous;
   noc_ttv_configured_header_encoder
     #(.HEADER_DIM_ORDER(HEADER_DIM_ORDER),
       .SWAP_DEST_XY(SWAP_DEST_XY))
   header
     (.physical_slot_labels(physical_slot_labels),
      .occupied(occupied),
      .logical_source(logical_source),
      .logical_destination(logical_destination),
      .physical_source(physical_source),
      .physical_destination(physical_destination),
      .route_info(route_info),
      .route_op(route_op),
      .config_valid(config_valid),
      .source_found(source_found),
      .destination_found(destination_found),
      .source_ambiguous(source_ambiguous),
      .destination_ambiguous(destination_ambiguous));

   noc_ttv_channel_pack
     #(.VC_ID(VC_ID),
       .VC_INDEX_WIDTH(VC_INDEX_WIDTH))
   pack
     (.route_info(route_info),
      .payload(payload),
      .inject_valid(inject_valid),
      .contract_valid(config_valid),
      .channel(channel));

endmodule
