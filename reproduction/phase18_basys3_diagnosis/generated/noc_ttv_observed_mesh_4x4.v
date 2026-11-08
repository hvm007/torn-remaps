module noc_ttv_observed_mesh_4x4
  #(parameter ROUTER_BUFFER_SIZE = 32,
    parameter ROUTER_IMPLEMENTATION = 1,
    parameter ROUTER_ERROR_CAPTURE_MODE = 1,
    parameter NUM_VCS = 4,
    parameter VC_INDEX_WIDTH = 2,
    parameter CHANNEL_WIDTH = 36 + VC_INDEX_WIDTH,
    parameter FLOW_CTRL_WIDTH = 1 + VC_INDEX_WIDTH,
    parameter DIM_ORDER = 0,
    // A set bit models one router instance elaborated against the alternate
    // dimension-order contract.  The all-zero default is the original mesh.
    parameter [0:15] ROUTER_DIM_ORDER_MASK = 16'b0)
  (clk,
   reset,
   injection_channels,
   injection_flow_ctrl,
   ejection_channels,
   ejection_flow_ctrl,
   router_error,
   trace_valid);

   input clk;
   input reset;
   input [0:16*CHANNEL_WIDTH-1] injection_channels;
   output [0:16*FLOW_CTRL_WIDTH-1] injection_flow_ctrl;
   output [0:16*CHANNEL_WIDTH-1] ejection_channels;
   input [0:16*FLOW_CTRL_WIDTH-1] ejection_flow_ctrl;
   output [0:15] router_error;
   output [0:79] trace_valid;

   // Stanford port order is west, east, north, south, local.  Routers are
   // indexed by their four-bit physical address {x[1:0], y[1:0]}, so adjacent
   // x coordinates differ by four and adjacent y coordinates differ by one.
   wire [0:CHANNEL_WIDTH-1] channel_in [0:15][0:4];
   wire [0:CHANNEL_WIDTH-1] channel_out [0:15][0:4];
   wire [0:FLOW_CTRL_WIDTH-1] flow_from_router [0:15][0:4];
   wire [0:FLOW_CTRL_WIDTH-1] flow_to_router [0:15][0:4];

   genvar router_index;
   generate
      for(router_index = 0; router_index < 16; router_index = router_index + 1)
        begin: routers
           localparam [0:3] ROUTER_ADDRESS = router_index;
           localparam ROUTER_DIM_ORDER
             = DIM_ORDER ^ ROUTER_DIM_ORDER_MASK[router_index];

           if(router_index >= 4)
             begin: has_west
                assign channel_in[router_index][0]
                  = channel_out[router_index-4][1];
                assign flow_to_router[router_index][0]
                  = flow_from_router[router_index-4][1];
             end
           else
             begin: west_boundary
                assign channel_in[router_index][0] = {CHANNEL_WIDTH{1'b0}};
                assign flow_to_router[router_index][0] = {FLOW_CTRL_WIDTH{1'b0}};
             end

           if(router_index < 12)
             begin: has_east
                assign channel_in[router_index][1]
                  = channel_out[router_index+4][0];
                assign flow_to_router[router_index][1]
                  = flow_from_router[router_index+4][0];
             end
           else
             begin: east_boundary
                assign channel_in[router_index][1] = {CHANNEL_WIDTH{1'b0}};
                assign flow_to_router[router_index][1] = {FLOW_CTRL_WIDTH{1'b0}};
             end

           if((router_index % 4) != 0)
             begin: has_north
                assign channel_in[router_index][2]
                  = channel_out[router_index-1][3];
                assign flow_to_router[router_index][2]
                  = flow_from_router[router_index-1][3];
             end
           else
             begin: north_boundary
                assign channel_in[router_index][2] = {CHANNEL_WIDTH{1'b0}};
                assign flow_to_router[router_index][2] = {FLOW_CTRL_WIDTH{1'b0}};
             end

           if((router_index % 4) != 3)
             begin: has_south
                assign channel_in[router_index][3]
                  = channel_out[router_index+1][2];
                assign flow_to_router[router_index][3]
                  = flow_from_router[router_index+1][2];
             end
           else
             begin: south_boundary
                assign channel_in[router_index][3] = {CHANNEL_WIDTH{1'b0}};
                assign flow_to_router[router_index][3] = {FLOW_CTRL_WIDTH{1'b0}};
             end

           assign channel_in[router_index][4]
             = injection_channels[router_index*CHANNEL_WIDTH +: CHANNEL_WIDTH];
           assign flow_to_router[router_index][4]
             = ejection_flow_ctrl[router_index*FLOW_CTRL_WIDTH +: FLOW_CTRL_WIDTH];
           assign injection_flow_ctrl[router_index*FLOW_CTRL_WIDTH +: FLOW_CTRL_WIDTH]
             = flow_from_router[router_index][4];
           assign ejection_channels[router_index*CHANNEL_WIDTH +: CHANNEL_WIDTH]
             = channel_out[router_index][4];

           router_slice
             #(.topology(0),
               .buffer_size(ROUTER_BUFFER_SIZE),
               .num_message_classes(1),
               .num_resource_classes(1),
               .num_vcs_per_class(NUM_VCS),
               .num_nodes(16),
               .num_dimensions(2),
               .num_nodes_per_router(1),
               .packet_format(0),
               .flow_ctrl_type(0),
               .flow_ctrl_bypass(0),
               .max_payload_length(4),
               .min_payload_length(0),
               .router_type(ROUTER_IMPLEMENTATION),
               .enable_link_pm(1),
               .flit_data_width(32),
               .error_capture_mode(ROUTER_ERROR_CAPTURE_MODE),
               .restrict_turns(1),
               .predecode_lar_info(1),
               .routing_type(0),
               .dim_order(ROUTER_DIM_ORDER),
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
              .router_address(ROUTER_ADDRESS),
              .channel_in_ip({channel_in[router_index][0],
                              channel_in[router_index][1],
                              channel_in[router_index][2],
                              channel_in[router_index][3],
                              channel_in[router_index][4]}),
              .flow_ctrl_out_ip({flow_from_router[router_index][0],
                                 flow_from_router[router_index][1],
                                 flow_from_router[router_index][2],
                                 flow_from_router[router_index][3],
                                 flow_from_router[router_index][4]}),
              .channel_out_op({channel_out[router_index][0],
                               channel_out[router_index][1],
                               channel_out[router_index][2],
                               channel_out[router_index][3],
                               channel_out[router_index][4]}),
              .flow_ctrl_in_op({flow_to_router[router_index][0],
                                flow_to_router[router_index][1],
                                flow_to_router[router_index][2],
                                flow_to_router[router_index][3],
                                flow_to_router[router_index][4]}),
              .error(router_error[router_index]));
        end
   endgenerate



   // Phase 18 adds passive observation only.  Each bit is the valid bit of
   // one frozen router output channel: index = router * 5 + output_port.
   genvar trace_router;
   genvar trace_port;
   generate
      for(trace_router = 0; trace_router < 16; trace_router = trace_router + 1)
        begin: observed_routers
           for(trace_port = 0; trace_port < 5; trace_port = trace_port + 1)
             begin: observed_ports
                assign trace_valid[trace_router*5 + trace_port]
                  = channel_out[trace_router][trace_port][1];
             end
        end
   endgenerate
endmodule
