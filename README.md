Reloj digital con alarma en FPGA (MyHDL + Nexys4DDR)

Proyecto final del curso Electrónica Digital, Universidad de San Buenaventura, semestre 2026-2.

Es un reloj digital descrito en MyHDL que se convierte a HDL y se programa en la tarjeta Nexys4DDR (Artix-7). Muestra la hora en los displays de 7 segmentos y tiene una alarma configurable. Cuando suena, la alarma activa una salida de audio y prende los LEDs de la tarjeta.

Integrantes
Sebastian Bejarano
(agregar compañeros)

Docente: (nombre del profesor)

Funcionalidades
Conteo de horas, minutos y segundos a partir del reloj de 100 MHz de la tarjeta
Visualización en los displays de 7 segmentos multiplexados
Ajuste de la hora con los botones de la tarjeta
Programación de la hora de la alarma
Alarma con señal de audio y LEDs encendidos al activarse
Hardware y herramientas
Elemento	Uso
Digilent Nexys4DDR (Artix-7)	Tarjeta donde corre el diseño
Python 3 + MyHDL	Descripción y simulación del hardware
pytest	Pruebas unitarias de los módulos
Apio	Síntesis y generación del bitstream
GTKWave (opcional)	Ver las formas de onda de la simulación
Estructura del repositorio

Ajustar a las carpetas reales del proyecto.

.
├── src/          # Módulos MyHDL (divisor de frecuencia, contadores, display, alarma...)
├── tests/        # Pruebas unitarias de cada módulo
├── constraints/  # Archivo de pines de la Nexys4DDR
├── build/        # HDL generado y bitstream
└── README.md
Cómo ejecutarlo
Clonar el repositorio e instalar las dependencias:
bash
git clone <url-del-repo>
cd <carpeta-del-repo>
pip install myhdl pytest
Correr las pruebas unitarias:
bash
pytest tests/
Convertir el diseño de MyHDL a HDL:
bash
python src/top.py
Generar el bitstream y programar la tarjeta (con la Nexys4DDR conectada por USB):
bash
apio build
apio upload
Uso en la tarjeta
Control	Función
BTNC	(ej. cambiar entre modo hora y modo alarma)
BTNU / BTND	(ej. subir / bajar el valor)
BTNL / BTNR	(ej. elegir horas o minutos)
SW0	(ej. activar o desactivar la alarma)
Pruebas

Cada módulo tiene su prueba unitaria en tests/. Las pruebas revisan, entre otras cosas, que los contadores se reinicien en el valor correcto (59 → 00 en minutos y segundos, 23 → 00 en horas), que el decodificador de 7 segmentos entregue el patrón esperado para cada dígito y que la alarma se active cuando la hora actual coincide con la programada.

Estado

El diseño funciona en la tarjeta física: cuenta la hora, la muestra en los displays y dispara la alarma con audio y luces.
