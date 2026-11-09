# Descripción

El archivo `country_collaboration.py` implementa un un programa que grafica la 
red de colaboraciones entre los `n_countries` países más frecuentes en una base 
de datos bibliografica. La base de datos se encuentra disponible en la 
siguiente ubicación:

https://raw.githubusercontent.com/jdvelasq/datalabs/master/datasets/scopus-papers.csv


Escriba su código en el archivo `country_collaboration.py`.


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