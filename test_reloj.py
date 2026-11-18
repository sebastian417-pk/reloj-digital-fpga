import pytest
from myhdl import (Signal, intbv, delay, instance, always, Simulation,
                   StopSimulation, now)

from reloj_digital import reloj_core

PATRONES = ["1111110", "0110000", "1101101", "1111001", "0110011",
            "1011011", "1011111", "1110000", "1111111", "1111011"]
SEG_N = [0x7F ^ int(p, 2) for p in PATRONES]

CLK_HZ = 20
DEB = 3
MUX = 2
TONE = 2


class Banco:
    def __init__(self):
        self.clk = Signal(bool(0))
        self.rst = Signal(bool(1))
        self.btn_hora = Signal(bool(0))
        self.btn_min = Signal(bool(0))
        self.btn_stop = Signal(bool(0))
        self.sw_alarma = Signal(bool(0))
        self.sw_alarma_on = Signal(bool(0))
        self.seg = Signal(intbv(0)[7:])
        self.an = Signal(intbv(0)[8:])
        self.dp = Signal(bool(1))
        self.buzzer = Signal(bool(0))
        self.leds = Signal(intbv(0)[15:])
        self.led = Signal(bool(0))
        self.hh = Signal(intbv(0, min=0, max=24))
        self.mm = Signal(intbv(0, min=0, max=60))
        self.ss = Signal(intbv(0, min=0, max=60))

    def dut(self):
        return reloj_core(self.clk, self.rst, self.btn_hora, self.btn_min,
                          self.btn_stop, self.sw_alarma, self.sw_alarma_on,
                          self.seg, self.an, self.dp, self.buzzer, self.led, self.leds,
                          self.hh, self.mm, self.ss,
                          CLK_HZ=CLK_HZ, DEB=DEB, MUX=MUX, TONE=TONE)

    def ciclos(self, n):
        for _ in range(n):
            yield self.clk.posedge

    def pulsar(self, boton, veces=1):
        for _ in range(veces):
            boton.next = 1
            yield from self.ciclos(DEB + 5)
            boton.next = 0
            yield from self.ciclos(DEB + 5)

    def esperar_hasta(self, condicion, maximo):
        for _ in range(maximo):
            if condicion():
                return
            yield self.clk.posedge
        raise AssertionError("la condición nunca se cumplió")

    def reiniciar(self):
        self.rst.next = 1
        yield from self.ciclos(3)
        self.rst.next = 0
        yield from self.ciclos(2)


def correr(banco, escenario):
    dut = banco.dut()

    @always(delay(5))
    def reloj():
        banco.clk.next = not banco.clk

    @instance
    def estimulo():
        yield from banco.reiniciar()
        yield from escenario(banco)
        raise StopSimulation()

    Simulation(dut, reloj, estimulo).run(quiet=1)


def test_cuenta_segundos():
    def escenario(b):
        yield from b.ciclos(CLK_HZ * 3 + 2)
        assert b.ss == 3
        assert b.mm == 0 and b.hh == 0

    correr(Banco(), escenario)


def test_minuto_completo():
    def escenario(b):
        yield from b.ciclos(CLK_HZ * 60 + 2)
        assert b.mm == 1 and b.ss == 0

    correr(Banco(), escenario)


def test_ajuste_hora_y_minuto_con_botones():
    def escenario(b):
        yield from b.pulsar(b.btn_hora, 5)
        yield from b.pulsar(b.btn_min, 7)
        assert b.hh == 5
        assert b.mm == 7
        assert b.ss == 0

    correr(Banco(), escenario)


def test_boton_sostenido_cuenta_una_sola_vez():
    def escenario(b):
        b.btn_hora.next = 1
        yield from b.ciclos(DEB + 60)
        b.btn_hora.next = 0
        yield from b.ciclos(DEB + 5)
        assert b.hh == 1

    correr(Banco(), escenario)


def test_rebote_corto_se_ignora():
    def escenario(b):
        b.btn_min.next = 1
        yield from b.ciclos(1)
        b.btn_min.next = 0
        yield from b.ciclos(DEB + 10)
        assert b.mm == 0

    correr(Banco(), escenario)


def test_cambio_de_dia():
    def escenario(b):
        yield from b.pulsar(b.btn_hora, 23)
        yield from b.pulsar(b.btn_min, 59)
        assert b.hh == 23 and b.mm == 59 and b.ss == 0
        yield from b.ciclos(CLK_HZ * 60 + 2)
        assert b.hh == 0 and b.mm == 0 and b.ss == 0

    correr(Banco(), escenario)


def test_display_muestra_hora():
    def escenario(b):
        yield from b.pulsar(b.btn_hora, 12)
        yield from b.pulsar(b.btn_min, 34)
        visto = {}
        for _ in range(MUX * 4 * 2 + 2):
            yield b.clk.negedge
            visto[int(b.an)] = int(b.seg)
        assert visto[0xFE] == SEG_N[4]
        assert visto[0xFD] == SEG_N[3]
        assert visto[0xFB] == SEG_N[2]
        assert visto[0xF7] == SEG_N[1]

    correr(Banco(), escenario)


def test_display_muestra_alarma_con_switch():
    def escenario(b):
        yield from b.pulsar(b.btn_hora, 6)
        b.sw_alarma.next = 1
        yield from b.ciclos(2)
        yield from b.pulsar(b.btn_hora, 8)
        yield from b.pulsar(b.btn_min, 15)
        assert b.hh == 6
        visto = {}
        for _ in range(MUX * 4 * 2 + 2):
            yield b.clk.negedge
            visto[int(b.an)] = int(b.seg)
        assert visto[0xF7] == SEG_N[0]
        assert visto[0xFB] == SEG_N[8]
        assert visto[0xFD] == SEG_N[1]
        assert visto[0xFE] == SEG_N[5]

    correr(Banco(), escenario)


def test_alarma_suena_y_se_apaga():
    def escenario(b):
        b.sw_alarma.next = 1
        yield from b.ciclos(2)
        yield from b.pulsar(b.btn_min, 1)
        b.sw_alarma.next = 0
        b.sw_alarma_on.next = 1
        yield from b.ciclos(2)
        assert b.buzzer == 0
        yield from b.esperar_hasta(lambda: b.mm == 1, CLK_HZ * 70)
        sono = False
        patrones = set()
        for _ in range(CLK_HZ * 3):
            yield b.clk.negedge
            patrones.add(int(b.leds))
            if b.buzzer == 1:
                sono = True
        assert sono
        assert len(patrones) > 3 and 0 not in patrones
        yield from b.pulsar(b.btn_stop)
        for _ in range(CLK_HZ * 3):
            yield b.clk.negedge
            assert b.buzzer == 0
            assert b.leds == 0

    correr(Banco(), escenario)


def test_alarma_desactivada_no_suena():
    def escenario(b):
        b.sw_alarma.next = 1
        yield from b.ciclos(2)
        yield from b.pulsar(b.btn_min, 1)
        b.sw_alarma.next = 0
        yield from b.ciclos(2)
        for _ in range(CLK_HZ * 65):
            yield b.clk.negedge
            assert b.buzzer == 0

    correr(Banco(), escenario)


def test_alarma_no_se_repite_tras_apagarla():
    def escenario(b):
        b.sw_alarma.next = 1
        yield from b.ciclos(2)
        yield from b.pulsar(b.btn_min, 1)
        b.sw_alarma.next = 0
        b.sw_alarma_on.next = 1
        yield from b.esperar_hasta(lambda: b.mm == 1, CLK_HZ * 70)
        yield from b.pulsar(b.btn_stop)
        assert b.ss == 0
        for _ in range(CLK_HZ * 5):
            yield b.clk.negedge
            assert b.buzzer == 0

    correr(Banco(), escenario)


def test_luces_apagadas_sin_alarma():
    def escenario(b):
        for _ in range(CLK_HZ * 3):
            yield b.clk.negedge
            assert b.leds == 0
            assert b.buzzer == 0

    correr(Banco(), escenario)


def test_tono_tiene_la_frecuencia_configurada():
    def escenario(b):
        b.sw_alarma.next = 1
        yield from b.ciclos(2)
        yield from b.pulsar(b.btn_min, 1)
        b.sw_alarma.next = 0
        b.sw_alarma_on.next = 1
        yield from b.esperar_hasta(lambda: b.buzzer == 1, CLK_HZ * 70)
        flancos = 0
        previo = int(b.buzzer)
        for _ in range(CLK_HZ // 2 - 2):
            yield b.clk.posedge
            if int(b.buzzer) != previo:
                flancos += 1
                previo = int(b.buzzer)
        assert flancos >= 4

    correr(Banco(), escenario)
