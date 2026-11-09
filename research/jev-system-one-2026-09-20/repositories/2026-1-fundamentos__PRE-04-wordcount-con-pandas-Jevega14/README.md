# Descipción

El archivo `word_count.py` implementa un un programa que cuenta la frecuencia 
de las palabras que aparecen en los archivos de texto almacenados en un 
directorio usando Pandas. El programa toma como argumentos el directorio de 
entrada y el directorio de salida. El programa lee todos los archivos ubicados 
en la carpeta de entrada, realiza el conteo de palabras usando Pandas y guarda 
el resultado en un archivo de texto en la carpeta de salida.

Complete el código siguiendo las instrucciones que aparecen en `word_count.py`.

# Configuración en MacOS y Linux

## Instalación del ambiante de desarrollo

Ejecute los siguientes comandos en el terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
source setup.sh
```

## Calificación del laboratorio

Ejecute los siguientes comandos en el terminal:

```bash
./tests/run.sh
```

# Configuración en Windows

## Instalación del ambiante de desarrollo

Ejecute los siguientes comandos en el terminal:

```bash
python3 -m venv .venv
.venv\Scripts\activate
setup
```

## Calificación del laboratorio

Ejecute los siguientes comandos en el terminal:

```bash
tests\run
```
