import pandas as pd
from glob import glob
from glob import iglob
import os
from sqlalchemy import create_engine
from time import time

#from __main__ import __file__ as nameMain

def config_engine(file):
    config = open(file, 'r')
    lineas = config.readlines()
    for linea in lineas:
        if 'user:' in linea:
            user = linea.replace('user:', '').replace(' ', '')
        if 'passw:' in linea:
            passw = linea.replace('passw:', '').replace(' ', '')
        if 'IP:' in linea:
            IP = linea.replace('IP:', '').replace(' ', '')
        if 'port:' in linea:
            port = linea.replace('port:', '').replace(' ', '')
        if 'DataBase:' in linea:
            DataBase = linea.replace('DataBase:', '').replace(' ', '')
        # engine = create_engine('postgresql://postgres:vag@10.30.19.227:5432/GAWUSH_DATABASE')
    config.close()
    credenciales = ('postgresql://' + user + ':' + passw + '@' + IP + ':' + port + '/' + DataBase).replace('\n', '')
    return create_engine(credenciales)

def config_tabla(file):
    config = open(file, 'r')
    lineas = config.readlines()
    for linea in lineas:
        if 'Tabla:' in linea:
            tabla = linea.replace('Tabla:', '').replace(' ', '').replace('\n', '')
    config.close()
    return tabla

def config_direccion(file):
    config = open(file, 'r')
    lineas = config.readlines()
    for linea in lineas:
        if 'CarpetaPrincipal:' in linea:
            direccion = linea.replace('CarpetaPrincipal:', '').replace(' ', '').replace('\n', '')
    config.close()
    return direccion

#############################################################################
#############################################################################


def BuscarCarpetasAnio(direc):
    listaAux = os.listdir(direc)
    for elemento in listaAux:
        try:
            int(elemento)
        except:
            listaAux.remove(elemento)
    return listaAux

def BuscarCarpetasMeses(direc):
    listaAux = os.listdir(direc)
    listaUnida = list()
    for elemento in listaAux:
        try:
            if int(elemento) > 12:
                listaAux.remove(elemento)
            else:
                listaUnida.append(os.path.join(direc, elemento))
        except:
            listaAux.remove(elemento)

    return listaUnida

def BuscarCarpetasDias(direc):
    listaAux = os.listdir(direc)
    listaUnida = list()
    for elemento in listaAux:
        try:
            if int(elemento) > 31:
                listaAux.remove(elemento)
            else:
                listaUnida.append(os.path.join(direc, elemento))
        except:
            listaAux.remove(elemento)

    return listaUnida
#############################################
def BusquedaDeArchivosEnCarpetas(direc, ext, engine, tabla):
    start_time = time()
    listaAnios = BuscarCarpetasAnio(direc)  # Busca y filtra las carpetas con nombres de anio
    listaAnioMes = list()
    for anio in listaAnios:
        listaAnioMes.extend(BuscarCarpetasMeses(os.path.join(direc, anio)))# Busca y filtra las carpetas con numeros de meses
    #print(listaAnioMes)
    listaAnioMesDia = list()
    for mes in listaAnioMes:
        listaAnioMesDia.extend(BuscarCarpetasDias(mes))  # Busca y filtra las carpetas con numeros de meses
    #print(listaAnioMesDia)
    # Generar lista de archivos del formato pedido
    listaArchivo = list()
    listaPeso = list()
    for anioMesDia in listaAnioMesDia:
        #listaArchivo.extend(BuscarArchivosConExtension(os.path.join(direc, anioMesDia), ext))
        aux, size = BuscarArchivosYPesoConExtension(os.path.join(direc, anioMesDia), ext)
        listaArchivo.extend(aux)
        listaPeso.extend(size)
    #for archivo in listaArchivo:
    #    listaPeso.append(os.path.getsize(archivo))

    #for file in iglob(os.path.join(direc,'**','**', '**', '*'), recursive=True):
    #    if file.endswith(ext):
    #        listaArchivo.append(file)
    #        listaPeso.append(os.path.getsize(file))
    elapsed_time = time() - start_time
    print(elapsed_time)
    #print(listaArchivo)

    # Filtrar lista de Archivos, y asi obtener solo los que fueron modificados
    df_listaArchivo_OLD, df_listaArchivo = VerificarUltimaMod(listaArchivo, listaPeso)
    #print(listaArchivo)

    print(len(df_listaArchivo_OLD))
    print(len(df_listaArchivo))


    df_listaArchivo_OLD.to_csv(nameMain.replace('py', 'csv'), index=False)
    i = 0
    for index, row in df_listaArchivo.iterrows():
        # Convierto en un DATAFRAME A LOS Archivo dat y los acumulo
        df = pd.concat([df, DF_Particularidad_Picarro(row.Archivo)], sort=False)
        
        #para no enviar todos los datos juntos, envio cada cien archivos.
        if ((index%100 == 0) & (not df.empty) & (index > 0)) | (index == len(df_listaArchivo)-1):
            print (index)
            Consulta_de_Existencia_Y_Envio(df, engine, tabla)
            if index == len(df_listaArchivo)-1:
                print("Ultimo Index")
                print(df_listaArchivo[i:index])
                break


                
            df_listaArchivo[i:index].to_csv(nameMain.replace('py', 'csv'), mode='a+', header=False, index=False)
            i = index
            df = pd.DataFrame()
                        
    if not df.empty:
        print("Evento RARO!!!")
        Consulta_de_Existencia_Y_Envio(df, engine, tabla)
    
    return df_listaArchivo

def Consulta_de_Existencia_Y_Envio(df, engine, tabla):
    df_temp = DF_DateTime_Picarro(df)
    #Consulta la existencia de los index
    INDEX = consulta_index_Base_Datos(engine, tabla, df_temp.index)
    df_temp = df_temp.reindex(df_temp.index.difference(INDEX))
    #Subo los archivos nuevos
    df_temp = df_temp.loc[df_temp.index.dropna()]
    if df_temp.empty:
        return
    print("Se carga: ")
    print(df_temp)
    df_temp.to_sql(tabla, engine, if_exists='append')

def Consulta_de_Existencia_Y_Envio_General(df, engine, tabla):
    #
    if df.empty:
        return
    #Consulta la existencia de los index
    INDEX = consulta_index_Base_Datos(engine, tabla, df.index)
    df_temp = df.reindex(df.index.difference(INDEX))
    #Subo los archivos nuevos
    df_temp = df_temp.loc[df_temp.index.dropna()]
    if df_temp.empty:
        return
    print("Se carga: ")
    print(df_temp)
    df_temp.to_sql(tabla, engine, if_exists='append')

def Consulta_de_Existencia_Y_Envio_DIAxDIA(df, engine, tabla):
    #
    #Consulta la existencia de los index
    for dia in pd.date_range(df.index[0].floor('D'), df.index[-1].ceil('D'), freq='D', inclusive='left'):
        print(dia)
        Consulta_de_Existencia_Y_Envio_General(df.loc[df.index.floor('D') == dia], engine, tabla)

def Update_General(df, engine, tabla):
    #

    #Subo los archivos nuevos
    df_temp = df.loc[df.index.dropna()]
    if df_temp.empty:
        return
    print("Se carga: ")
    print(df_temp)
    df_temp.to_sql(tabla, engine, if_exists='replace')

def DF_Particularidad_Picarro(archivo):
    return pd.read_csv(archivo, sep='\s+')

def DF_DateTime_Picarro(df):
    df['DateTime'] = pd.to_datetime(df.DATE + ' ' + df.TIME)
    df.set_index('DateTime', inplace=True)
    return df

def BuscarArchivosConExtension(direc, ext):
    listaAux = glob(os.path.join(direc, '*' + ext))
    return listaAux

def BuscarArchivosYPesoConExtension(direc, ext):
    listaAux = glob(os.path.join(direc, '*' + ext))
    listaSize =[]
    for file in listaAux:
        listaSize.append(os.path.getsize(file))
    return listaAux, listaSize


def VerificarUltimaMod(lista, peso):
    #global DF_AUX
    if len(lista) > 0:
        #Creo un DATAFRAME de los archivos con sus pesos actuales
        df_listaArchivo = pd.DataFrame(lista,columns=['Archivo'])
        df_listaArchivo['BYTE'] = peso
        df_listaArchivo.set_index('Archivo', inplace=True)
        df_listaArchivo = df_listaArchivo[~df_listaArchivo.index.duplicated(keep='first')]
        print('df_listaArchivo - Creado')
        try:
            #Leo el anterior registro
            print('Leo el anterior registro')
            df_listaArchivo_old = pd.read_csv(nameMain.replace('py', 'csv'))
            df_listaArchivo_old.set_index('Archivo', inplace=True)
            # Genero una DF de los archivos nuevos
            print('Genero una DF de los archivos nuevos')
            start_time = time()
            df_New = df_listaArchivo.reindex(df_listaArchivo.index.difference(df_listaArchivo_old.index))
            elapsed_time = time() - start_time
            # Genero un DF de los archivos viejos, para verificar si fue modificado
            print('Genero un DF de los archivos viejos')
            df_Old = df_listaArchivo.reindex(df_listaArchivo_old.index)
            #print(df_Old)
            df_Comp = df_Old.loc[df_Old.BYTE != df_listaArchivo_old.BYTE]
            df_Old = df_Old.reindex(df_Old.index.difference(df_Comp.index))
            print("Se actualizo: ")
            print(df_Comp)
            df_listaNew = pd.concat([df_Comp, df_New])
            #DF_AUX = df_listaArchivo  # .to_csv('listaArchivo.csv')
            df_Old.reset_index(inplace=True)
            df_listaNew.reset_index(inplace=True)
            return df_Old, df_listaNew
        except Exception as e:
            print(e)
        #DF_AUX = df_listaArchivo#.to_csv('listaArchivo.csv')
        df_listaArchivo.reset_index(inplace=True)
        return df_listaArchivo.head(0), df_listaArchivo
        #return
#######################################################
def consulta_index_Base_Datos(engine, tabla, INDEX):
    Consulta = 'select "DateTime" from "' + tabla + '" where "DateTime" IN ' + '(\'' + '\', \''.join(INDEX.strftime('%Y-%m-%d %H:%M:%S').tolist()) + '\')'
    dt_DB = pd.read_sql_query(Consulta, con=engine)
    return dt_DB.DateTime.values

def buscarEnBaseDeDatos(engine, Tabla, inicio, fin):
    try:
        consulta = 'Select * from "' + Tabla + '" where "DateTime" >= \'' + inicio._repr_base + '\' and "DateTime" < \'' + fin._repr_base + '\' order by "DateTime"'
        print(consulta)
        df_aux = pd.read_sql_query(consulta, con=engine)
        df_aux.DateTime = pd.to_datetime(df_aux.DateTime)
        df_aux.set_index(['DateTime'], inplace=True)
        df_aux['DateTime'] = df_aux.index
        df_aux.index.name = 'DateTime'
        # df_aux.rename({'TambC': 'TempA', 'Hr': 'HR', 'PrhPa': 'Pres', 'VdGrad': 'Dir'}, axis=1, inplace=True)
    except:
        print("No se pudo Obtener Datos de " + inicio._repr_base)
        df_aux = pd.DataFrame()
    # print(df_aux)
    return df_aux

def SeleccionarTodaLaBaseDeDatos(engine, Tabla,):
    try:
        consulta = 'Select * from "' + Tabla +'"'
        print(consulta)
        df_aux = pd.read_sql_query(consulta, con=engine)
    except:
        print("No se pudo Obtener Datos de " + Tabla)
        df_aux = pd.DataFrame()
    # print(df_aux)
    return df_aux