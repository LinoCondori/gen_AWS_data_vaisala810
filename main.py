import os, json, csv, shutil

import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import BaseDeDatos_Lib_v04 as bd




# 🔹 Configuración


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "config.json")) as f:
    config = json.load(f)
    db_conf = config["database"]
    ftp_conf = config["ftp"]
    folder_conf = config["carpetas"]
    DESTINO = folder_conf['destino']
    fecha_inicial = pd.to_datetime(config["database"]["last_date"], format="%Y-%m-%d")


with open("metadatos_aws_ush.txt", "r", encoding="utf-8") as f:
    lineas = f.readlines()
    for linea in lineas:
        if "Descripción de variables:" in linea:
            inicio_index = lineas.index(linea) + 1
        if "Comentarios:" in linea:
            fin_index = lineas.index(linea)
    columnas = list()
    for linea in lineas[inicio_index:fin_index]:
        columnas.append(linea[:linea.index(":")].replace("# ", ''))



# Crear motor SQLAlchemy
engine = create_engine(f"postgresql+psycopg2://{db_conf['user']}:{db_conf['password']}@{db_conf['host']}:{db_conf['port']}/{db_conf['name']}")



# Rutas absolutas
#ORIGEN =  os.path.join(FTP_DIR, folder_conf['cargado'])
#DESTINO = ORIGEN

def procesar_archivos():
    for fecha in pd.date_range(fecha_inicial, pd.to_datetime('today'), freq='D'):
        target_dir = os.path.join(DESTINO, fecha.strftime('%Y'), )

        df_dia = bd.buscarEnBaseDeDatos(engine, "aws810", fecha, fecha + pd.to_timedelta(arg=1, unit="D"))
        df_dia.drop(columns=['DateTime'], inplace=True)

        output_path = os.path.join(target_dir, folder_conf['nombre'] + fecha.strftime("%Y%m%d.csv"))
        # crear la carpeta si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # crear el CSV temporal
        df_dia[columnas].to_csv(output_path, index=False)
        # leer el CSV temporal
        with open(output_path, "r", encoding="utf-8") as archivo:
            contenido = archivo.read()
        # sobreescribir el CSV con el encabezado
        with open(output_path, "w", encoding="utf-8") as archivo:
            archivo.write("".join(lineas) + contenido)


    config["database"]["last_date"] = (fecha - pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    # Sobrescribir el archivo con la nueva información
    with open(os.path.join(BASE_DIR, "config.json"), 'w', ) as file:
        json.dump(config, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    procesar_archivos()


