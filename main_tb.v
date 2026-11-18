`timescale 1ns/10ps

module main_tb;

    reg clk = 0;
    reg rst_n = 0;
    reg btn_hora = 0;
    reg btn_min = 0;
    reg btn_stop = 0;
    reg sw_alarma = 0;
    reg sw_alarma_on = 0;
    wire [6:0] seg;
    wire [7:0] an;
    wire dp;
    wire audio;
    wire audio_sd;
    wire [14:0] leds;
    wire led_alarma;

    main dut (
        .clk(clk), .rst_n(rst_n),
        .btn_hora(btn_hora), .btn_min(btn_min), .btn_stop(btn_stop),
        .sw_alarma(sw_alarma), .sw_alarma_on(sw_alarma_on),
        .seg(seg), .an(an), .dp(dp),
        .audio(audio), .audio_sd(audio_sd), .led_alarma(led_alarma), .leds(leds)
    );

    always #5 clk = ~clk;

    integer errores = 0;
    integer i;
    reg sono;
    reg luces_ok;
    reg [6:0] v_fe, v_fd, v_fb, v_f7;

    task revisar;
        input ok;
        input [8*44-1:0] mensaje;
        begin
            if (ok) $display("  ok    %0s", mensaje);
            else begin
                $display("  FALLA %0s", mensaje);
                errores = errores + 1;
            end
        end
    endtask

    task ciclos;
        input integer n;
        integer k;
        begin
            for (k = 0; k < n; k = k + 1) @(posedge clk);
        end
    endtask

    task reiniciar;
        begin
            rst_n = 0;
            ciclos(3);
            rst_n = 1;
            ciclos(2);
        end
    endtask

    task pulsar_hora;
        input integer veces;
        integer k;
        begin
            for (k = 0; k < veces; k = k + 1) begin
                btn_hora = 1; ciclos(8);
                btn_hora = 0; ciclos(8);
            end
        end
    endtask

    task pulsar_min;
        input integer veces;
        integer k;
        begin
            for (k = 0; k < veces; k = k + 1) begin
                btn_min = 1; ciclos(8);
                btn_min = 0; ciclos(8);
            end
        end
    endtask

    task pulsar_stop;
        begin
            btn_stop = 1; ciclos(8);
            btn_stop = 0; ciclos(8);
        end
    endtask

    task esperar_minuto_uno;
        integer k;
        begin
            k = 0;
            while (dut.mm != 1 && k < 20 * 70) begin
                @(posedge clk);
                k = k + 1;
            end
        end
    endtask

    function [6:0] patron_apagado_en_bajo;
        input [3:0] d;
        begin
            case (d)
                0: patron_apagado_en_bajo = 7'b0000001;
                1: patron_apagado_en_bajo = 7'b1001111;
                2: patron_apagado_en_bajo = 7'b0010010;
                3: patron_apagado_en_bajo = 7'b0000110;
                4: patron_apagado_en_bajo = 7'b1001100;
                5: patron_apagado_en_bajo = 7'b0100100;
                6: patron_apagado_en_bajo = 7'b0100000;
                7: patron_apagado_en_bajo = 7'b0001111;
                8: patron_apagado_en_bajo = 7'b0000000;
                9: patron_apagado_en_bajo = 7'b0000100;
                default: patron_apagado_en_bajo = 7'b1111111;
            endcase
        end
    endfunction

    initial begin
        $dumpvars(0, main_tb);

        $display("1. Arranque y cuenta de segundos");
        reiniciar;
        revisar(dut.hh == 0 && dut.mm == 0 && dut.ss == 0, "arranca en 00:00:00");
        ciclos(20 * 3 + 2);
        revisar(dut.ss == 3, "despues de 3 s marca ss = 3");
        ciclos(20 * 57);
        revisar(dut.mm == 1 && dut.ss == 0, "a los 60 s marca 00:01:00");

        $display("2. Ajuste con botones");
        reiniciar;
        pulsar_hora(5);
        pulsar_min(7);
        revisar(dut.hh == 5, "5 pulsaciones de hora -> hh = 5");
        revisar(dut.mm == 7, "7 pulsaciones de minuto -> mm = 7");
        revisar(dut.ss == 0, "ajustar pone los segundos en 0");
        btn_hora = 1;
        ciclos(60);
        btn_hora = 0;
        ciclos(10);
        revisar(dut.hh == 6, "boton sostenido suma solo una vez");

        $display("3. Cambio de dia");
        reiniciar;
        pulsar_hora(23);
        pulsar_min(59);
        revisar(dut.hh == 23 && dut.mm == 59, "23:59 despues de ajustar");
        ciclos(20 * 60 + 2);
        revisar(dut.hh == 0 && dut.mm == 0 && dut.ss == 0, "23:59:59 -> 00:00:00");

        $display("4. Display de 7 segmentos");
        reiniciar;
        pulsar_hora(12);
        pulsar_min(34);
        v_fe = 0; v_fd = 0; v_fb = 0; v_f7 = 0;
        for (i = 0; i < 24; i = i + 1) begin
            @(negedge clk);
            case (an)
                8'hFE: v_fe = seg;
                8'hFD: v_fd = seg;
                8'hFB: v_fb = seg;
                8'hF7: v_f7 = seg;
            endcase
        end
        revisar(v_f7 == patron_apagado_en_bajo(1), "digito 1 (decenas de hora) = 1");
        revisar(v_fb == patron_apagado_en_bajo(2), "digito 2 (unidades de hora) = 2");
        revisar(v_fd == patron_apagado_en_bajo(3), "digito 3 (decenas de minuto) = 3");
        revisar(v_fe == patron_apagado_en_bajo(4), "digito 4 (unidades de minuto) = 4");
        revisar(an[7:4] == 4'b1111, "los 4 displays de la izquierda apagados");

        $display("5. Alarma");
        reiniciar;
        sw_alarma = 1;
        ciclos(2);
        pulsar_min(1);
        sw_alarma = 0;
        sw_alarma_on = 1;
        ciclos(2);
        revisar(led_alarma == 1, "LED 0 encendido con alarma activa");
        revisar(audio == 0, "no suena antes de la hora");
        esperar_minuto_uno;
        sono = 0;
        luces_ok = 1;
        for (i = 0; i < 20 * 3; i = i + 1) begin
            @(negedge clk);
            if (audio) sono = 1;
            if (leds == 0) luces_ok = 0;
        end
        revisar(sono == 1, "suena al llegar a 00:01");
        revisar(luces_ok == 1, "los LEDs de la alarma se prenden");
        pulsar_stop;
        sono = 0;
        for (i = 0; i < 20 * 3; i = i + 1) begin
            @(negedge clk);
            if (audio) sono = 1;
        end
        revisar(sono == 0, "el boton de parar la apaga y no vuelve");
        revisar(leds == 0, "al parar la alarma se apagan los LEDs");
        revisar(audio_sd == 1, "amplificador de audio habilitado");

        $display("6. Alarma desactivada");
        reiniciar;
        sw_alarma_on = 0;
        sw_alarma = 1;
        ciclos(2);
        pulsar_min(1);
        sw_alarma = 0;
        sono = 0;
        for (i = 0; i < 20 * 65; i = i + 1) begin
            @(negedge clk);
            if (audio) sono = 1;
        end
        revisar(sono == 0, "con el switch de alarma abajo no suena");

        if (errores == 0) $display("RESULTADO: TODO OK");
        else $display("RESULTADO: %0d FALLAS", errores);
        $finish;
    end

endmodule
