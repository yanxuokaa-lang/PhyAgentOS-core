jEV
===

Nodo control de electrovalvulas mediante Arduino Nano 328, en redes IP (ENC28J60), con sensor
de corriente (ACS712 5A) y sensor de temperatura I2C (DS18B20).

Por defecto usa la IP 192.168.2.12, y los comandos que acepta son ev1_on, ev1_off, ev2_on, ev2_off,
ev3_on, ev3_off, all_on, all_off, por ejemplo:

http://192.168.2.12/ev1_on

http://192.168.2.12/ev1_on&ev2_off

