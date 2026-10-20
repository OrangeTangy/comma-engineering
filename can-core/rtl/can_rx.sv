// Original implementation, 2026. Classical CAN base-frame receive engine.
// sample_en denotes one already-synchronized bus sample per bit.
// This block does not implement physical bit timing or error signalling.
module can_rx (
  input wire clk, rst, sample_en, bus_bit,
  output reg frame_valid, frame_error,
  output reg [2:0] error_code, // 1 stuff, 2 CRC, 3 form, 4 unsupported IDE
  output reg [10:0] identifier,
  output reg remote_frame,
  output reg [3:0] dlc,
  output reg [63:0] data,
  output wire ack_request,
  output wire receiving
);
  localparam IDLE=0, BODY=1, CRC=2, CRC_DELIM=3, ACK=4,
             ACK_DELIM=5, EOF_BITS=6, RECOVER=7;
  reg [3:0] state;
  reg [6:0] pos, data_bits;
  reg [4:0] crc_pos;
  reg [3:0] run_length, tail_count, idle_count;
  reg last_bit;
  reg [14:0] crc_reg, crc_wire;
  reg [10:0] id_work;
  reg rtr_work;
  reg [3:0] dlc_work;
  reg [63:0] data_work;
  reg crc_good;
  wire stuffing = (state == BODY || state == CRC || state == CRC_DELIM);
  assign ack_request = state == ACK && crc_good;
  assign receiving = state != IDLE && state != RECOVER;
  function automatic [14:0] crc_next(input [14:0] c, input b);
    crc_next = {c[13:0],1'b0} ^ ((c[14]^b) ? 15'h4599 : 15'h0);
  endfunction
  task automatic fail(input [2:0] code);
    begin
      frame_error <= 1; error_code <= code; state <= RECOVER;
      idle_count <= 0; crc_good <= 0;
    end
  endtask
  always @(posedge clk) begin
    if (rst) begin
      state<=RECOVER; idle_count<=0; frame_valid<=0; frame_error<=0;
      error_code<=0; identifier<=0; remote_frame<=0; dlc<=0; data<=0;
      pos<=0; data_bits<=0; crc_pos<=0; run_length<=0; tail_count<=0;
      last_bit<=1; crc_reg<=0; crc_wire<=0; crc_good<=0;
      id_work<=0; rtr_work<=0; dlc_work<=0; data_work<=0;
    end else begin
      frame_valid<=0; frame_error<=0;
      if (sample_en) begin
        if (state == RECOVER) begin
          if (!bus_bit) idle_count<=0;
          else if (idle_count == 10) begin state<=IDLE; idle_count<=0; end
          else idle_count<=idle_count+1'b1;
        end else if (state == IDLE) begin
          if (!bus_bit) begin
            state<=BODY; pos<=1; crc_reg<=0; crc_wire<=0; crc_pos<=0;
            run_length<=1; last_bit<=0; crc_good<=0;
            id_work<=0; rtr_work<=0; dlc_work<=0; data_work<=0;
          end
        end else if (stuffing && run_length == 5) begin
          if (bus_bit == last_bit) fail(1);
          else begin run_length<=1; last_bit<=bus_bit; end
        end else begin
          if (state == BODY || state == CRC) begin
            run_length <= bus_bit == last_bit ? run_length+1'b1 : 1;
            last_bit<=bus_bit;
          end
          case (state)
            BODY: begin
              crc_reg<=crc_next(crc_reg,bus_bit);
              pos<=pos+1'b1;
              if (pos<=11) id_work<={id_work[9:0],bus_bit};
              else if (pos==12) rtr_work<=bus_bit;
              else if (pos==13 && bus_bit) fail(4);
              // Reserved r0 is accepted at either polarity by a receiver.
              else if (pos>=15 && pos<=18) begin
                dlc_work<={dlc_work[2:0],bus_bit};
                if (pos==18) begin
                  data_bits <= {dlc_work[2:0],bus_bit}>8 ? 64 : {dlc_work[2:0],bus_bit,3'b000};
                  if (rtr_work || {dlc_work[2:0],bus_bit}==0) state<=CRC;
                end
              end else if (pos>=19) begin
                data_work <= {data_work[62:0],bus_bit};
                if (pos==18+data_bits) state<=CRC;
              end
            end
            CRC: begin
              crc_wire<={crc_wire[13:0],bus_bit};
              if (crc_pos==14) begin
                crc_good <= {crc_wire[13:0],bus_bit}==crc_reg;
                state<=CRC_DELIM;
              end else crc_pos<=crc_pos+1'b1;
            end
            CRC_DELIM: begin
              if (!bus_bit) fail(3);
              else state<=ACK;
            end
            ACK: state<=ACK_DELIM;
            ACK_DELIM: begin
              if (!bus_bit) fail(3);
              else if (!crc_good) fail(2);
              else begin state<=EOF_BITS; tail_count<=0; end
            end
            EOF_BITS: begin
              if (!bus_bit && tail_count<6) fail(3);
              else if (tail_count==6) begin
                frame_valid<=1; identifier<=id_work; remote_frame<=rtr_work;
                dlc<=dlc_work; data<=data_work;
                // Three recessive intermission bits are required before next SOF.
                state<=RECOVER; idle_count<=8;
                if (!bus_bit) idle_count<=0;
              end else tail_count<=tail_count+1'b1;
            end
            default: fail(3);
          endcase
        end
      end
    end
  end
endmodule
