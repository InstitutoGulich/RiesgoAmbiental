# RiesgoAmbiental

El archivo python principal es el RA.py, en tanto que RA_GUI tiene la definición de la interfaz.

* Seleccionar shape file: Shape que tiene las localidades sobre las cuales se desea determinar el Riesgo Ambiental o sobre las que se desea descargar info de los satélities disponibles en este momento.

* Campo Clave: campo clave de las localidades

* Campo Riesgo: campo que tiene la info del riesgo (o como se llame; a definir)

* Satélites: Satélites cuya info se quiere descargar sobre las localidades: Por el momento los disponbles son:
  1. Terra MODIS, banda LST_Day_1km. Requerido si se quiere determinar el Riesgo Ambiental.
  2. CHIRPS, banda Precip_Day_1km
  3. IMERG, banda precipitationCal

* Riesgo Ambiental: si se quire calcular o no.

* Año: Año para el que se descargarán los datos y eventualmente calculará el RA

