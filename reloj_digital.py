from myhdl import block, always, always_comb, Signal, intbv, modbv

SEG = (
    "1111110",
    "0110000",
    "1101101",
    "1111001",
    "0110011",
    "1011011",
    "1011111",
    "1110000",
    "1111111",
    "1111011",
)

SEG_N = tuple(int(p, 2) ^ 0x7F for p in SEG) + (0x7F,) * 6

ROT = tuple((((0xF << i) | (0xF >> (16 - i))) & 0xFFFF) >> 1 for i in range(16))

DECENAS = tuple(i // 10 for i in range(60))
UNIDADES = tuple(i % 10 for i in range(60))


@block
def boton(clk, rst, entrada, pulso, DEB):
    s1 = Signal(bool(0))
    s2 = Signal(bool(0))
    estable = Signal(bool(0))
    previo = Signal(bool(0))
    cnt = Signal(intbv(0, min=0, max=DEB + 1))

    @always(clk.posedge)
    def sincronizar():
        s1.next = entrada
        s2.next = s1

    @always(clk.posedge)
    def antirrebote():
        if rst:
            cnt.next = 0
            estable.next = 0
            previo.next = 0
        else:
            previo.next = estable
            if s2 == estable:
                cnt.next = 0
            elif cnt == DEB - 1:
                estable.next = s2
                cnt.next = 0
            else:
                cnt.next = cnt + 1

    @always_comb
    def flanco_subida():
        pulso.next = estable and not previo

    return sincronizar, antirrebote, flanco_subida


@block
def reloj_core(clk, rst, btn_hora, btn_min, btn_stop, sw_alarma, sw_alarma_on,
               seg, an, dp, audio, led_alarma, leds, hh, mm, ss,
               CLK_HZ=100_000_000, DEB=1_000_000, MUX=50_000, TONE=50_000):

    p_hora = Signal(bool(0))
    p_min = Signal(bool(0))
    p_stop = Signal(bool(0))

    b1 = boton(clk, rst, btn_hora, p_hora, DEB)
    b2 = boton(clk, rst, btn_min, p_min, DEB)
    b3 = boton(clk, rst, btn_stop, p_stop, DEB)

    presc = Signal(intbv(0, min=0, max=CLK_HZ))
    tick = Signal(bool(0))
    beep = Signal(bool(0))

    PASO = CLK_HZ // 10
    tono = Signal(bool(0))
    tono_cnt = Signal(intbv(0, min=0, max=TONE))
    anim = Signal(modbv(0)[4:])
    anim_cnt = Signal(intbv(0, min=0, max=PASO))

    ah = Signal(intbv(0, min=0, max=24))
    am = Signal(intbv(0, min=0, max=60))

    match = Signal(bool(0))
    match_d = Signal(bool(0))
    sonando = Signal(bool(0))

    vh = Signal(intbv(0, min=0, max=24))
    vm = Signal(intbv(0, min=0, max=60))
    dig = Signal(intbv(0)[4:])
    sel = Signal(modbv(0)[2:])
    mux_cnt = Signal(intbv(0, min=0, max=MUX))

    @always_comb
    def fin_de_segundo():
        tick.next = presc == CLK_HZ - 1

    @always(clk.posedge)
    def tiempo():
        if rst:
            presc.next = 0
            hh.next = 0
            mm.next = 0
            ss.next = 0
        elif (not sw_alarma) and (p_hora or p_min):
            if p_hora:
                if hh == 23:
                    hh.next = 0
                else:
                    hh.next = hh + 1
            if p_min:
                if mm == 59:
                    mm.next = 0
                else:
                    mm.next = mm + 1
            ss.next = 0
            presc.next = 0
        elif tick:
            presc.next = 0
            if ss == 59:
                ss.next = 0
                if mm == 59:
                    mm.next = 0
                    if hh == 23:
                        hh.next = 0
                    else:
                        hh.next = hh + 1
                else:
                    mm.next = mm + 1
            else:
                ss.next = ss + 1
        else:
            presc.next = presc + 1

    @always(clk.posedge)
    def ajuste_alarma():
        if rst:
            ah.next = 0
            am.next = 0
        elif sw_alarma:
            if p_hora:
                if ah == 23:
                    ah.next = 0
                else:
                    ah.next = ah + 1
            if p_min:
                if am == 59:
                    am.next = 0
                else:
                    am.next = am + 1

    @always(clk.posedge)
    def parpadeo():
        if rst:
            beep.next = 0
        elif tick:
            beep.next = not beep

    @always_comb
    def coincidencia():
        if sw_alarma_on and hh == ah and mm == am and ss == 0:
            match.next = 1
        else:
            match.next = 0

    @always(clk.posedge)
    def alarma():
        if rst:
            match_d.next = 0
            sonando.next = 0
        else:
            match_d.next = match
            if match and not match_d:
                sonando.next = 1
            elif p_stop or not sw_alarma_on:
                sonando.next = 0

    @always(clk.posedge)
    def generador_tono():
        if rst:
            tono_cnt.next = 0
            tono.next = 0
        elif tono_cnt == TONE - 1:
            tono_cnt.next = 0
            tono.next = not tono
        else:
            tono_cnt.next = tono_cnt + 1

    @always(clk.posedge)
    def animacion():
        if rst:
            anim_cnt.next = 0
            anim.next = 0
        elif anim_cnt == PASO - 1:
            anim_cnt.next = 0
            anim.next = anim + 1
        else:
            anim_cnt.next = anim_cnt + 1

    @always_comb
    def salidas_alarma():
        audio.next = sonando and beep and tono
        led_alarma.next = sw_alarma_on

    @always_comb
    def luces():
        if sonando:
            leds.next = ROT[anim]
        else:
            leds.next = 0

    @always_comb
    def visible():
        if sw_alarma:
            vh.next = ah
            vm.next = am
        else:
            vh.next = hh
            vm.next = mm

    @always(clk.posedge)
    def multiplexor():
        if rst:
            mux_cnt.next = 0
            sel.next = 0
        elif mux_cnt == MUX - 1:
            mux_cnt.next = 0
            sel.next = sel + 1
        else:
            mux_cnt.next = mux_cnt + 1

    @always_comb
    def elegir_digito():
        if sel == 0:
            dig.next = UNIDADES[vm]
            an.next = 0xFE
        elif sel == 1:
            dig.next = DECENAS[vm]
            an.next = 0xFD
        elif sel == 2:
            dig.next = UNIDADES[vh]
            an.next = 0xFB
        else:
            dig.next = DECENAS[vh]
            an.next = 0xF7

    @always_comb
    def decodificador():
        seg.next = SEG_N[dig]

    @always_comb
    def punto():
        if sel == 2 and beep:
            dp.next = 0
        else:
            dp.next = 1

    return (b1, b2, b3, fin_de_segundo, tiempo, ajuste_alarma, parpadeo,
            coincidencia, alarma, generador_tono, animacion, salidas_alarma,
            luces, visible, multiplexor,
            elegir_digito, decodificador, punto)


@block
def main(clk, rst_n, btn_hora, btn_min, btn_stop, sw_alarma, sw_alarma_on,
         seg, an, dp, audio, audio_sd, led_alarma, leds,
         CLK_HZ=100_000_000, DEB=1_000_000, MUX=50_000, TONE=50_000):

    rst = Signal(bool(0))
    hh = Signal(intbv(0, min=0, max=24))
    mm = Signal(intbv(0, min=0, max=60))
    ss = Signal(intbv(0, min=0, max=60))

    nucleo = reloj_core(clk, rst, btn_hora, btn_min, btn_stop, sw_alarma,
                        sw_alarma_on, seg, an, dp, audio, led_alarma, leds,
                        hh, mm, ss, CLK_HZ=CLK_HZ, DEB=DEB, MUX=MUX,
                        TONE=TONE)

    @always_comb
    def reset_activo_bajo():
        rst.next = not rst_n

    @always_comb
    def amplificador():
        audio_sd.next = rst_n

    return nucleo, reset_activo_bajo, amplificador


def generar_verilog(path=".", **params):
    clk = Signal(bool(0))
    rst_n = Signal(bool(1))
    btn_hora = Signal(bool(0))
    btn_min = Signal(bool(0))
    btn_stop = Signal(bool(0))
    sw_alarma = Signal(bool(0))
    sw_alarma_on = Signal(bool(0))
    seg = Signal(intbv(0)[7:])
    an = Signal(intbv(0)[8:])
    dp = Signal(bool(1))
    audio = Signal(bool(0))
    audio_sd = Signal(bool(0))
    led_alarma = Signal(bool(0))
    leds = Signal(intbv(0)[15:])

    inst = main(clk, rst_n, btn_hora, btn_min, btn_stop, sw_alarma,
                sw_alarma_on, seg, an, dp, audio, audio_sd, led_alarma, leds,
                **params)
    inst.convert(hdl="Verilog", name="main", path=path)
    import os
    sobrante = os.path.join(path, "tb_main.v")
    if os.path.exists(sobrante):
        os.remove(sobrante)


if __name__ == "__main__":
    import os
    import sys

    if "--sim" in sys.argv:
        os.makedirs("sim", exist_ok=True)
        generar_verilog(path="sim", CLK_HZ=20, DEB=3, MUX=2, TONE=2)
        print("Generado sim/main.v (version rapida solo para simular)")
    else:
        generar_verilog()
        print("Generado main.v")
