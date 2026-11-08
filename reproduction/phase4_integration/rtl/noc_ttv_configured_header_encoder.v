module noc_ttv_configured_header_encoder
  #(parameter SITE_COUNT = 16,
    parameter LABEL_WIDTH = 4,
    parameter HEADER_DIM_ORDER = 0,
    parameter SWAP_DEST_XY = 0)
  (physical_slot_labels,
   occupied,
   logical_source,
   logical_destination,
   physical_source,
   physical_destination,
   route_info,
   route_op,
   config_valid,
   source_found,
   destination_found,
   source_ambiguous,
   destination_ambiguous);

   input [0:SITE_COUNT*LABEL_WIDTH-1] physical_slot_labels;
   input [0:SITE_COUNT-1]             occupied;
   input [0:LABEL_WIDTH-1]            logical_source;
   input [0:LABEL_WIDTH-1]            logical_destination;
   output [0:LABEL_WIDTH-1]           physical_source;
   output [0:LABEL_WIDTH-1]           physical_destination;
   output [0:6]                       route_info;
   output [0:4]                       route_op;
   output                             config_valid;
   output                             source_found;
   output                             destination_found;
   output                             source_ambiguous;
   output                             destination_ambiguous;

   noc_ttv_config_adapter source_adapter
     (.physical_slot_labels(physical_slot_labels),
      .occupied(occupied),
      .logical_address(logical_source),
      .physical_address(physical_source),
      .found(source_found),
      .ambiguous(source_ambiguous));

   noc_ttv_config_adapter destination_adapter
     (.physical_slot_labels(physical_slot_labels),
      .occupied(occupied),
      .logical_address(logical_destination),
      .physical_address(physical_destination),
      .found(destination_found),
      .ambiguous(destination_ambiguous));

   wire route_valid;
   noc_ttv_physical_header_encoder
     #(.DIM_ORDER(HEADER_DIM_ORDER),
       .SWAP_DEST_XY(SWAP_DEST_XY))
   header
     (.physical_source(physical_source),
      .physical_destination(physical_destination),
      .route_info(route_info),
      .route_op(route_op),
      .route_valid(route_valid));

   assign config_valid
     = source_found & destination_found &
       ~source_ambiguous & ~destination_ambiguous & route_valid;

endmodule
