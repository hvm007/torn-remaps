module noc_ttv_channel_pack
  #(parameter [0:1] VC_ID = 2'b00,
    parameter VC_INDEX_WIDTH = 2)
  (route_info,
   payload,
   inject_valid,
   contract_valid,
   channel);

   input [0:6] route_info;
   input [0:24] payload;
   input inject_valid;
   input contract_valid;
   output [0:35+VC_INDEX_WIDTH] channel;

   // Stanford head/tail channel, four VCs, link power management enabled:
   // link-active | valid,vc[1:0],head,tail | 32-bit flit data.
   assign channel[0] = 1'b1;
   assign channel[1] = inject_valid & contract_valid;
   assign channel[2 +: VC_INDEX_WIDTH]
     = VC_ID[2-VC_INDEX_WIDTH +: VC_INDEX_WIDTH];
   assign channel[2+VC_INDEX_WIDTH] = 1'b1;
   assign channel[3+VC_INDEX_WIDTH] = 1'b1;
   assign channel[4+VC_INDEX_WIDTH +: 7] = route_info;
   assign channel[11+VC_INDEX_WIDTH +: 25] = payload;

endmodule
