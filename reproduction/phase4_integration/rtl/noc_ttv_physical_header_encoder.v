module noc_ttv_physical_header_encoder
  #(parameter DIM_ORDER = 0,
    parameter SWAP_DEST_XY = 0)
  (physical_source,
   physical_destination,
   route_info,
   route_op,
   route_valid);

   input [0:3] physical_source;
   input [0:3] physical_destination;
   output [0:6] route_info;
   output [0:4] route_op;
   output reg route_valid;

   wire [0:0] route_orc;
   wire [0:3] encoded_destination;
   assign encoded_destination = SWAP_DEST_XY
     ? {physical_destination[2:3], physical_destination[0:1]}
     : physical_destination;
   rtr_routing_logic
     #(.num_message_classes(1),
       .num_resource_classes(1),
       .num_routers_per_dim(4),
       .num_dimensions(2),
       .num_nodes_per_router(1),
       .connectivity(0),
       .routing_type(0),
       .dim_order(DIM_ORDER),
       .reset_type(0))
   route
     (.router_address(physical_source),
      .sel_mc(1'b1),
      .sel_irc(1'b1),
      .dest_info(encoded_destination),
      .route_op(route_op),
      .route_orc(route_orc));

   reg [0:2] route_port;
   always @*
     begin
        route_port = 3'b000;
        route_valid = 1'b1;
        case(route_op)
          5'b10000: route_port = 3'b000;
          5'b01000: route_port = 3'b001;
          5'b00100: route_port = 3'b010;
          5'b00010: route_port = 3'b011;
          5'b00001: route_port = 3'b100;
          default:
            begin
               route_port = 3'b000;
               route_valid = 1'b0;
            end
        endcase
     end

   assign route_info[0:2] = route_port;
   assign route_info[3:6] = encoded_destination;

endmodule
