from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import numpy as np
import time,datetime
import yfinance as yf
import pandas as pd
from lxml import etree 
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from IPython.display import clear_output



# Definir variables globales
df_bitcoin, precio_actual, tendencia, media_bitcoin,variacion, algoritmo_decision=pd.DataFrame(),None,None,None,None,None

#iniciando driver selenium, deberas tener actualizado el chrome a la ultima versión, y el chromedriver tambien
chrome_options = ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--silent")
chrome_options.add_argument("--log-level=3")
driver = webdriver.Chrome(service=Service('chromedriver.exe'), options=chrome_options)


def importar_base_bitcoin():
    #definir variables globales y symbol para la consulta a yahoo finance
    global df_bitcoin,precio_actual, tendencia, media_bitcoin, algoritmo_decision
    symbol = 'BTC-USD'

    # configurar parametros end_date como fecha de fin (dia actual) y star date los ultimos 7 días
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=7)

    # Descarga el precio histórico del bitcoin en intervalos de 5 minutos con parametro interval
    data = yf.download(symbol, start=start_date, end=end_date, interval='5m')
    #guardar en un dataframe llamado df_bitcoin
    df_bitcoin = pd.DataFrame(data)

    
def extraer_tendencias():
    #definir variables globales
    global df_bitcoin, precio_actual, tendencia, media_bitcoin, algoritmo_decision
    #abrimos en 2do plano la pagina web para scrapear el precio
    driver.get("https://coinmarketcap.com/")
    #buscamos el precio actual y limpiamos la , y el simbolo de $ reemplazandolo por "" , segun su ubicacion por xpath
    seleccionar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[1]/div[4]/table/tbody/tr[1]/td[4]/div/a/span")))
    time.sleep(1)
    precio_actual=seleccionar.text
    precio_actual = float(precio_actual.replace(",", "").replace("$", ""))
 
    # Extraemos la variacion de la ultima hora y le quitamos el % para que nos quede el float
    seleccionar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[1]/div[4]/table/tbody/tr[1]/td[5]/span")))
    variacion = seleccionar.text
    variacion = float(variacion.replace("%", ""))
    
    # Extraemos la clase segun xpath si es icon caret up que indica que la tendencia es alta y el icon caret down, que indica
    # una tendencia baja, luego guaramos en la variable tendencia si es alta o baja

    seleccionar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[1]/div[4]/table/tbody/tr[1]/td[5]/span/span"))) 
    clase_tendencia = seleccionar.get_attribute("class")
    
    if clase_tendencia=="icon-Caret-up":
         tendencia="alta"
    if clase_tendencia=="icon-Caret-down":
         tendencia="baja"
         
    #visualizamos valores en consola     
    print(f"Precio actual: {precio_actual}, Variación: {variacion}, Tendencia: {tendencia}")


def limpieza_datos():
    #definir variables globales
    global df_bitcoin, precio_actual, tendencia, media_bitcoin, algoritmo_decision
    #creamos una copia del dataframe df_bitcoin para poder conservar los datos originales
    df_bitcoin_limpio = df_bitcoin.copy()
    # Identificar valores duplicados en el índice
    valores_duplicados_en_indice = df_bitcoin_limpio.index.duplicated()
    # Eliminar los valores duplicados en el índice
    df_bitcoin_limpio = df_bitcoin_limpio[~df_bitcoin_limpio.index.duplicated(keep='first')]
    # verificar y ver los valores nulos en la columna 
    df_bitcoin_nulos = df_bitcoin_limpio['Close'].isnull().sum()
    print("Valores nulos en Close:", df_bitcoin_nulos)
    # Elimina valores nulos en la columna Close
    df_bitcoin_limpio = df_bitcoin_limpio.dropna(subset=['Close'])
    # Filtra los registros con Volumen mayor a 0
    df_bitcoin_limpio = df_bitcoin_limpio[df_bitcoin_limpio['Volume'] > 0]
    # crea un grafico de caja de la columna close se quedara comentado para fines visuales
    """
    plt.figure(figsize=(8, 6))
    plt.boxplot(df_bitcoin_limpio['Close'], vert=True)
    plt.ylabel('Precio de Cierre (Close)')
    plt.title('Boxplot del Precio de Cierre de Bitcoin')
    plt.show()
    """
    # Calcula los cuartiles Q1 y Q3 
    Q1 = df_bitcoin_limpio['Close'].quantile(0.25)
    Q3 = df_bitcoin_limpio['Close'].quantile(0.75)
    print("cuartil 1 :", Q1)
    print("cuartil 3 :", Q3)
    # Filtra para tener un precio de cierre entre Q1 y Q3
    df_bitcoin_limpio = df_bitcoin_limpio[(df_bitcoin_limpio['Close'] >= Q1) & (df_bitcoin_limpio['Close'] <= Q3)]
    # grafico el df con los valores entre q1 y q3 se quedara comentado para fines visuales
    """
    plt.figure(figsize=(8, 6))
    plt.boxplot(df_bitcoin_limpio['Close'], vert=True)
    plt.ylabel('Precio de Cierre (Close)')
    plt.title('Boxplot del Precio de Cierre de Bitcoin entre Q1 y Q3')
    plt.show()
    """
    # Calcula el precio promedio de la columna close y lo guardamos en la variable media_bitcoin
    media_bitcoin = df_bitcoin_limpio['Close'].mean()
    print("Precio promedio: ", media_bitcoin)
    

def tomar_decisiones():
    #definimos variables globales
    global df_bitcoin, precio_actual, tendencia, media_bitcoin, algoritmo_decision

    #tenemos 3 condiciones,
    # 1 - si el precio actual es mayor o igual a la media y la tendencia es baja y ademas la variacion es diferente
    #     a 0.00, guardamos "Vender" en la variable algoritmo_decision
    # 2 - si el precio actual es menor a la media y la tendencia es alta y ademas la variacion es diferente
    #     a 0.00, guardamos "Comprar" en la variable algoritmo_decision
    # 3 - Si no se cumple ninguna de las 2 condiciones anteriores, se guarda "Esperar" en la variable algoritmo_decision
    
    # a pesar de que en la clase_tendencia podria indicar alta o baja, debemos tambien validar que la variacion no
    # este como 0.00 para no tomar una mala decision, ya que una tendencia alta o baja no servira de indicador
    # cuando la variacion es 0.00 ( en la version anterior nos recomendaba comprar o vender bitcoin cuando la variacion era 0.00)
    
    if precio_actual >= media_bitcoin and tendencia == 'baja' and variacion!=0.00:
        algoritmo_decision = 'Vender'
    elif precio_actual < media_bitcoin and tendencia == 'alta'and variacion!=0.00:
        algoritmo_decision = 'Comprar'
    else:
        algoritmo_decision = 'Esperar'
    print(algoritmo_decision)

def visualizacion():
   #definimos variables globales
   global df_bitcoin, precio_actual, tendencia, media_bitcoin, algoritmo_decision
   #creamos una dataframe llamada df_bitcoin1 para utilizarla en la grafica
   df_bitcoin1=df_bitcoin
   #creamos la columna promedio y llenamos todos los valores con la media del precio
   df_bitcoin1['Promedio'] = media_bitcoin
   #utilizamos plt.clf para borrar la figura actual en el ploteo ( si la hubiera )
   plt.clf()
   # Agregar un título al gráfico y le ponemos un fontsize de 30
   plt.title('Precio del Bitcoin',fontsize=30)
   # Dibujar una línea con los datos del índice como eje X y la columna "Close" como eje Y
   plt.plot(df_bitcoin.index, df_bitcoin['Close'], label='Close')
   # Dibujar otra línea con los datos del índice y la columna "Promedio"
   plt.plot(df_bitcoin.index, df_bitcoin['Promedio'], label='Promedio')
   # Escribimos en el grafico la variable "algoritmo_deciosion" luego configuramos 
   # la ubicacion de la anotacion, que es la ultima variable del index (eje horizontal) y df_bitcoin['Close'].max())
   # que representa el mayor valor de la columna close (eje vertical)
   
   plt.annotate(f'{algoritmo_decision}', (df_bitcoin.index[-1], df_bitcoin['Close'].max()), xytext=(0, -20),
             textcoords='offset points', fontsize=20, color='red', ha='center')
   #mostramos el grafico
   plt.show()
   #pausa 1 segundo para que el programa continúe y se pueda mostrar el gráfico, de lo contrario no se visualizara
   plt.pause(1) 

# Este comando activa el modo interactivo en Matplotlib, ya que
# En el modo interactivo, Matplotlib no bloquea la ejecución del programa cuando se muestra una figura. 
plt.ion()
# utilizamos la inicializacion del plt fuera del while para que se reutilize el grafico y no aparescan multiples
# ventanas
plt.figure(figsize=(16, 5))


#llamamos a todas las funciones con un delay de 300 segundos!!!
while(True):
  try:
   
   #clear_output()
   importar_base_bitcoin()
   extraer_tendencias()
   limpieza_datos()
   tomar_decisiones()
   visualizacion()
   time.sleep(300)
  except:
      print("fallo")
 