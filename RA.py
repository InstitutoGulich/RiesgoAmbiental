# Código Original (IDL): De Elia Estefania 
# Última modificación: 2011_08_16

# Código Modificado (Python): Rubio Jorge
# Última modificación: 2021-08-03

# Standard library imports
from datetime import datetime, timedelta
import math
import sys
import numpy as np
import os

# Third party imports
from PyQt5 import QtWidgets
import ee 
import geopandas as gpd
import pandas as pd

# Local application imports
from RA_GUI import Ui_MainWindow  # importing our generated file

ee.Initialize()

previousYear = datetime.now().year - 1

class mywindow(QtWidgets.QMainWindow):

    def __init__(self):

        super(mywindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.lb_Anyo.setText("2000")
        self.ui.hs_Anyo.setMaximum(previousYear)
        
        self.ui.bt_Shape.clicked.connect(self.selectShape)
        
        self.ui.rb_RA_SI.toggled.connect(self.onClickedRA)
        self.ui.rb_RA_NO.toggled.connect(self.onClickedRA)

        self.ui.cb_Terra.stateChanged.connect(self.changeTerra)
        self.ui.cb_Chirps.stateChanged.connect(self.changeChirps)
        self.ui.cb_Imerg.stateChanged.connect(self.changeImerg)
        self.ui.hs_Anyo.valueChanged[int].connect(self.changeSlider)
        
        self.ui.buttonBox.accepted.connect(self.selectAccept)
        self.ui.buttonBox.rejected.connect(self.selectCancel)
        
    def selectShape(self):
        self.ui.cBox_Fields.clear()
        dlg = QtWidgets.QFileDialog(self)
        dlg.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dlg.setNameFilters(["Shape files (*.shp)"])
#        filenames = QStringList()
        if dlg.exec_():
            filenames = dlg.selectedFiles()
            if len(filenames) > 0:
                self.ui.lb_Warning.setText('')
                self.ui.lb_Shape.setText(filenames[0])
                gpd_locs = gpd.read_file(filenames[0])
                self.ui.cBox_Fields.addItems(gpd_locs.columns)
                self.ui.cBox_Fields_2.addItems(gpd_locs.columns)
        
    def onClickedRA(self):
        if self.ui.rb_RA_SI.isChecked():
            self.ui.cb_Terra.setChecked(True)
            
    def changeTerra(self, value):
        if self.ui.cb_Terra.isChecked() == False:
            self.ui.rb_RA_NO.setChecked(True)
        else:
            self.ui.lb_Warning.setText('')

    def changeChirps(self, value):
        self.ui.lb_Warning.setText('')

    def changeImerg(self, value):
        self.ui.lb_Warning.setText('')
            
    def changeSlider(self, value):
        self.ui.lb_Anyo.setText(str(value))

    def selectAccept(self):
        RA(self)
        
    def selectCancel(self):
        self.close()
    

#####
##### FUNCIONES
#####

def set_dates(start_date, end_date):
    startTime = start_date.strftime("%Y-%m-%d")
    endTime = (end_date+pd.to_timedelta(pd.np.ceil(2), unit="D")).strftime("%Y-%m-%d")
    anyo = start_date.strftime("%Y")
    
    return startTime, endTime, anyo

def _getInfo(image_collection, point):
    return image_collection.getRegion(point,1500).getInfo()

def get_data(which,x,point,row,key_in):
    # Reshape lst data 
    header = x[0]
    data = np.array(x[1:])
    iTime = header.index('time')
    # datetime.fromtimestamp() is correct, except you are probably having timestamp in miliseconds 
    # (like in JavaScript), but fromtimestamp() expects Unix timestamp, in seconds
    time = [datetime.fromtimestamp(i/1000).strftime("%Y-%m-%d") for i in (data[0:,iTime].astype(int))]

    if which == 'LST':
        band = 'LST_Day_1km'
        
    if which == 'CHIRPS':
        band = 'precipitation'

    if which == 'IMERG':
        band = 'precipitationCal'

    iBands = [header.index(band)]
    img_data = data[0:,iBands].astype(float)

    if which == 'LST':
        # Kelvin to Celsius
        img_data = img_data*.02-273

    df = pd.DataFrame(data = img_data, index = time, columns = [band])
              
    # interpolation for empty data
    df[band] = df[band].interpolate(method ='linear', limit_direction ='both') 

    df['date'] = df.index
    
    dayly_data = df
    dayly_data[key_in] = row[key_in]
    dayly_data['x'] = point['coordinates'][0]
    dayly_data['y'] = point['coordinates'][1]

    return dayly_data

def get_rambiental(df_loc, gpd_locs,key_in):
    # Parametros constantes
    reseteo_total = 5  # grados centigrados que hacen que se resetee toda la cuenta de ciclos para el tramo que viene calculando
    T_minima = 12      # umbral termico para eclosion de huevos
    diasT_min = 20     # numeros de dias con grados superiores al umbral termico para eclosion de huevos
    beta_cero = -91.7  # parametro de función EIP vs T
    beta_uno = 10374   # parametro de función EIP vs T
    T_VidaMax= 20      # dias de tiempo de vida del adulto

    # Contadores
    sum_PEIP = 0.      # setea la suma en cada pixel diferente
    dias_20gt12 = 0    # setea los dias acumulados en cada pixel diferente
    count = 0          # setea el count en cada pixel diferente
    
    ciclos = 0
    dias_20gt12 = 0
    dia = 0
    
    for index, row in df_loc.iterrows():
        dia += 1
        if row['LST_Day_1km'] >= T_minima:
            count += 1
            if count >= diasT_min: 
                if dias_20gt12 == 0:
                    dias_20gt12 = dia
                
                # EIP= periodo de incubación (Función de T) según EIP(i)= beta_cero + (beta_uno/T(i))
                EIP = (beta_cero + (beta_uno / row['LST_Day_1km'])) / 24 

                # PEIP= proporción periodo de incubación cumplido ese día
                PEIP = 1 / EIP                                         

                sum_PEIP = sum_PEIP + PEIP
                if ((dia-dias_20gt12) != 0) and ((dia-dias_20gt12) % T_VidaMax == 0):
                    if sum_PEIP >= 0.99:
                        ciclos += 1
                        sum_PEIP = 0.
        else:
            if row['LST_Day_1km'] < reseteo_total:
                count = 0
                dias_20gt12 = 0
                sum_PEIP = 0
    
    res = pd.DataFrame()
    res = res.append({key_in:df_loc.iloc[0][key_in], 'ciclos':ciclos}, ignore_index=True)
    return res
    
def updateLabel(self):
    self.ui.lb_Warning.clear()


def RA(self):
    updateLabel(self)
    
    #Leer los datos de la ventana principal
    shape = self.ui.lb_Shape.text()
    if shape == ".shp para filtar imágenes":
        self.ui.lb_Warning.setText('Seleccionar algun shape file')
        return
    path_in = os.path.dirname(os.path.abspath(shape))
    
    key_in = self.ui.cBox_Fields.currentText()
    key_RA = self.ui.cBox_Fields_2.currentText()
    
    booTemp = self.ui.cb_Terra.isChecked()
    booChirps = self.ui.cb_Chirps.isChecked()
    booImerg = self.ui.cb_Imerg.isChecked()
    
    booRA = self.ui.rb_RA_SI.isChecked()
    
    anyo = int(self.ui.lb_Anyo.text())
    
    gpd_locs = gpd.read_file(shape)
    gpd_locs.crs = ('epsg:4326')
    
    if booTemp == booChirps == booImerg == False:
        self.ui.lb_Warning.setText('Seleccionar alguna fuente de datos')
        return

    # Set start and end date
    startTime = datetime(anyo, 1, 2)+ timedelta(days=201)
    endTime = datetime(anyo+1, 1, 2)+ timedelta(days=202)
    start_time = datetime.now()

#    print('\nStart time:', datetime.now())
    

    # Create image collection
    if booTemp == True:
        modisCollection = ee.ImageCollection('MODIS/006/MOD11A1').filterDate(startTime, endTime)
    if booChirps == True:
        chirpsCollection = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate(startTime, endTime)
    if booImerg == True:
        imergCollection = ee.ImageCollection('NASA/GPM_L3/IMERG_V06').filterDate(startTime, endTime)
 
    lst_list = []
    chirps_list = []
    imerg_list = []

    total = gpd_locs.shape[0]
    for index , row in gpd_locs.iterrows():
        point = {'type':'Point', 'coordinates':[row['geometry'].x,row['geometry'].y]}
        
        if booTemp == True:
            _x = _getInfo(modisCollection, point)
            lst_list.append(get_data("LST",_x,point,row,key_in))
#            lst_list.append(get_data("LST","{:.2f}".format(_x),point,row))
#            print(lst_list)

        if booChirps == True:
            _y = _getInfo(chirpsCollection, point)
            chirps_list.append(get_data("CHIRPS",_y,point,row))

        if booImerg == True:
            _z = _getInfo(imergCollection, point)
            imerg_list.append(get_data("IMERG",_z,point,row))

        self.ui.pb_Proceso.setValue(int(index*100/total))

    df = gpd_locs
    
    # para guardar las series de tiempo para uso futuro
    file_to_csv = 'datos'+str(anyo)+'_'
    
    if booTemp == True:
        file_to_csv = file_to_csv+'LST_'
        df_lst = pd.concat(lst_list)
        df = pd.merge(df,df_lst, on = [key_in])

    if booChirps == True:
        file_to_csv = file_to_csv+'Chirps_'
        df_chirps = pd.concat(chirps_list)
        if booTemp == True:
            df = pd.merge(df, df_chirps, on = [key_in,'date', 'x', 'y'])
        else:
            df = pd.merge(df, df_chirps, on = [key_in])

    if booImerg == True:
        file_to_csv = file_to_csv+'IMERG_'
        df_imerg = pd.concat(imerg_list)
        # agregar el df_imerg por día, ya que viene cada media hora
        df_imerg_dayly = df_imerg.groupby([key_in,'date'])['precipitationCal'].sum()
        df_imerg_dayly = df_imerg_dayly.reset_index()
        if booTemp == True or booChirps == True:
            df = pd.merge(df, df_imerg_dayly, on = [key_in, 'date'])
        else:
            df = pd.merge(df, df_imerg_dayly, on = [key_in])

    df = df.reset_index()
    df.to_csv(file_to_csv+'.csv',index=False)

    end_time = datetime.now()
 #   print('\nTotal run time:', end_time - start_time, '\n')

    # Cálculo del Riesgo Ambiental
    if booTemp == True:
        df_ambiente = pd.DataFrame()
        for index , row in gpd_locs.iterrows():
            df_ambiente = df_ambiente.append(get_rambiental(df[df[key_in]==row[key_in]], gpd_locs,key_in))

        df_ambiente.reset_index(drop=True)

        df_merged = pd.merge(df_ambiente,gpd_locs , on = [key_in])
        df_merged['ciclos_norm'] = df_merged['ciclos']/df_merged['ciclos'].max()
#        df_merged['Riesgo_Amb'] = sqrt(df_merged['ciclos_norm']*df_merged['Mapa_pr'])
        df_merged['Riesgo_Amb'] = np.sqrt(df_merged['ciclos_norm']*df_merged[key_RA])

        gdf = gpd.GeoDataFrame(df_merged, geometry = 'geometry')
        #gdf = gdf.drop(columns=['x','y'])
        gdf.crs= "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        gdf.to_file(path_in+'/RA.shp')#, driver='ESRI Shapefile')

 #       df.to_csv(path_in+'/RA.csv',index=False)

        self.ui.pb_Proceso.setValue(100)
    return



    
app = QtWidgets.QApplication([])

application = mywindow()
application.show()

sys.exit(app.exec())

