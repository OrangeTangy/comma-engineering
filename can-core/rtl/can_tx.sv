// Original implementation. Classical CAN base-frame transmitter at bit boundaries.
// drive_en precedes sample_en in each bit; start is accepted only when ready.
// Caller must grant bus access after intermission. Retry/error frame policy is external.
module can_tx (
  input wire clk, rst, drive_en, sample_en, start, bus_bit,
  input wire [10:0] identifier,
  input wire remote_frame,
  input wire [3:0] dlc,
  input wire [63:0] data,
  output wire ready,
  output reg tx_bit, done, arbitration_lost, tx_error,
  output reg [2:0] error_code // 1 invalid DLC, 2 ACK missing, 3 bit error
);
  localparam IDLE=0, BODY=1, CRC=2, CRC_DELIM=3, ACK=4,
             ACK_DELIM=5, EOF_BITS=6, INTERMISSION=7;
  reg [3:0] state;
  reg [10:0] id_latch;
  reg rtr_latch;
  reg [3:0] dlc_latch;
  reg [63:0] data_latch;
  reg [6:0] pos;
  reg [4:0] crc_pos;
  reg [3:0] run_length, tail_count;
  reg last_bit, sent_stuff, pending_sample;
  reg [14:0] crc_reg;
  reg next_bit;
  wire stuffed_region = state == BODY || state == CRC || state == CRC_DELIM;
  assign ready = state == IDLE;
  function automatic [14:0] crc_next(input [14:0] c, input b);
    crc_next = {c[13:0],1'b0} ^ ((c[14]^b) ? 15'h4599 : 15'h0);
  endfunction
  always @* begin
    next_bit=1;
    case (state)
      BODY: begin
        if (pos==0) next_bit=0;
        else if (pos<=11) next_bit=id_latch[11-pos];
        else if (pos==12) next_bit=rtr_latch;
        else if (pos==13 || pos==14) next_bit=0;
        else if (pos<=18) next_bit=dlc_latch[18-pos];
        else next_bit=data_latch[63-(pos-19)];
      end
      CRC: next_bit=crc_reg[14-crc_pos];
      default: next_bit=1;
    endcase
    if (stuffed_region && run_length==5) next_bit=~last_bit;
  end
  always @(posedge clk) begin
    if (rst) begin
      state<=IDLE; tx_bit<=1; done<=0; arbitration_lost<=0; tx_error<=0;
      error_code<=0; id_latch<=0; rtr_latch<=0; dlc_latch<=0; data_latch<=0;
      pos<=0; crc_pos<=0; run_length<=0; tail_count<=0; last_bit<=1;
      sent_stuff<=0; pending_sample<=0; crc_reg<=0;
    end else begin
      done<=0; arbitration_lost<=0; tx_error<=0;
      if (state==IDLE) begin
        if (drive_en) tx_bit<=1;
        if (start) begin
          if (dlc>8) begin tx_error<=1; error_code<=1; end
          else begin
            state<=BODY; id_latch<=identifier; rtr_latch<=remote_frame;
            dlc_latch<=dlc; data_latch<=data;
            pos<=0; crc_pos<=0; run_length<=0; crc_reg<=0;
          end
        end
      end else begin
        if (drive_en) begin
          tx_bit<=next_bit; pending_sample<=1;
          sent_stuff<=stuffed_region && run_length==5;
        end
        if (sample_en && pending_sample) begin
          pending_sample<=0;
          if (state==BODY && pos>=1 && pos<=12 && tx_bit && !bus_bit) begin
            arbitration_lost<=1; state<=IDLE;
          end else if (state==ACK && bus_bit) begin
            tx_error<=1; error_code<=2; state<=IDLE;
          end else if (state!=ACK && tx_bit!=bus_bit) begin
            tx_error<=1; error_code<=3; state<=IDLE;
          end else if (sent_stuff) begin
            run_length<=1; last_bit<=tx_bit;
          end else begin
            if (state==BODY || state==CRC) begin
              run_length<=tx_bit==last_bit ? run_length+1'b1 : 1;
              last_bit<=tx_bit;
            end
            case(state)
              BODY: begin
                crc_reg<=crc_next(crc_reg,tx_bit);
                if ((pos==18 && (rtr_latch || dlc_latch==0)) ||
                    (pos>=19 && pos==18+{dlc_latch,3'b000})) state<=CRC;
                else pos<=pos+1'b1;
              end
              CRC: if (crc_pos==14) state<=CRC_DELIM; else crc_pos<=crc_pos+1'b1;
              CRC_DELIM: state<=ACK;
              ACK: state<=ACK_DELIM;
              ACK_DELIM: begin state<=EOF_BITS; tail_count<=0; end
              EOF_BITS: if(tail_count==6) begin
                done<=1; state<=INTERMISSION; tail_count<=0;
              end else tail_count<=tail_count+1'b1;
              INTERMISSION: if(tail_count==2) state<=IDLE; else tail_count<=tail_count+1'b1;
              default: state<=IDLE;
            endcase
          end
        end
      end
    end
  end
endmodule
