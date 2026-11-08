module noc_ttv_config_adapter
  #(parameter SITE_COUNT = 16,
    parameter LABEL_WIDTH = 4)
  (physical_slot_labels,
   occupied,
   logical_address,
   physical_address,
   found,
   ambiguous);

   input [0:SITE_COUNT*LABEL_WIDTH-1] physical_slot_labels;
   input [0:SITE_COUNT-1]             occupied;
   input [0:LABEL_WIDTH-1]            logical_address;
   output reg [0:LABEL_WIDTH-1]       physical_address;
   output reg                         found;
   output reg                         ambiguous;

   integer slot;
   always @*
     begin
        physical_address = {LABEL_WIDTH{1'b0}};
        found = 1'b0;
        ambiguous = 1'b0;
        for(slot = 0; slot < SITE_COUNT; slot = slot + 1)
          if(occupied[slot] &&
             (physical_slot_labels[slot*LABEL_WIDTH +: LABEL_WIDTH]
              == logical_address))
            begin
               if(found)
                 ambiguous = 1'b1;
               else
                 begin
                    physical_address = slot;
                    found = 1'b1;
                 end
            end
     end

endmodule
