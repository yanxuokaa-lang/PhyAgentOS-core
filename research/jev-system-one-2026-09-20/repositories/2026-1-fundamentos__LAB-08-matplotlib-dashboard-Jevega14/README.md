# Descripción

El archivo `data/shipping-data.csv` contiene información sobre los envios de productos de una empresa. Cree un dashboard estático en HTML que permita visualizar los siguientes campos:

* `Warehouse_block`

* `Mode_of_Shipment`

* `Customer_rating`

* `Weight_in_gms`

El dashboard generado debe ser similar a este:

![dashboard](https://github.com/jdvelasq/LAB_matplotlib_dashboard/blob/main/shipping-dashboard-example.png)

Para ello, siga las instrucciones dadas en el siguiente video:

https://youtu.be/AgbWALiAGVo

Tenga en cuenta los siguientes cambios respecto al video:

* El archivo de datos se encuentra en la carpeta `data`.

* Todos los archivos debe ser creados en la carpeta `docs`.

* Su código debe crear la carpeta `docs` si no existe.

# Configuración en MacOS y Linux

Ejecute los siguientes comandos en el terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
source setup.sh
```

# Configuración en Windows

Ejecute los siguientes comandos en el terminal:

```bash
python3 -m venv .venv
.venv\Scripts\activate
setup
```

# Ejecución de pruebas

Ejecute el siguiente comando en el terminal:

```bash
pytest
```
