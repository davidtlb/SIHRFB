import os
import signal
import threading
import cv2
import imutils
import gpiozero
import numpy as np
import multiprocessing as mp
import subprocess as sp
import netifaces as ni
from correo import correos
from time import sleep
from picamera import PiCamera
from gpiozero import MotionSensor
from subprocess import call
from telegram.ext import Updater, CommandHandler, MessageHandler,CallbackQueryHandler,ConversationHandler, Filters, Dispatcher
from telegram import InlineKeyboardMarkup, InlineKeyboardButton,ReplyKeyboardRemove, ChatAction

bot_token="TOKEN DEL BOT" #TOKEN del BOT.
INPUT_TEXT, INPUT_TEXT2, INPUT_TEXT3, INPUT_TEXT4 = range(4)
RING_SFX_PATH = '/home/david/facial/Doorbell.wav'
RELAY_PIN = 18
LUZ_PIN = 15
estado = 0
#-----------------------------------------Funcion /start del BOT, lo primero que se ejecuta al inicar el bot---------------------------------------------
def start(update, context):
    global chat_id
    chat_id = update.message.chat_id
    #archivo = open ("chatid.csv", "a")
    #archivo.write(chat_id)
    #archivo.write("\n")
    #archivo.close
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    msg = f'Hola *{first_name} {last_name}*, bienvenido a nuestro bot. '

    context.bot.sendMessage(chat_id=chat_id, text=msg, parse_mode = "Markdown")
    context.bot.sendMessage(chat_id, 'En la parte inferior izquierda tendras un menu de ayuda o podes poner /info.')

#-----------------------------------------Funcion /info del BOT, informacion extra y para saber que hace cada comando---------------------------------------------
def info(update, context):
    chat_id = update.message.chat_id
    msg = "/start: Sirve para inicializar el BOT (una vez o cada vez que se reinicie el sistema).\n\n"
    msg+= "/foto: Saca una foto en tiempo real desde la camara y lo sube al BOT.\n\n"
    msg+= "/video: Graba un video de 5 segundos en tiempo real y lo sube al BOT.\n\n"
    msg+= "/puerta: Abrir puerta, 5 segundos de activacion.\n\n"
    msg+= "/prenderluz: Activa el rele para prender la luz.\n\n"
    msg+= "/pir: Activa el rele para prender la luz.\n\n"
    msg+= "/Ip: Ver direccion IP de la Raspberry PI.\n\n"
    msg+= "/listarCaras: Listar caras registradas para el Reconocimiento Facial.\n\n"
    msg+= "/RFacial: Activar Camara para el ingreso por Registro Facial.\n\n" 
    msg+= "/AgregarCorreo: Agregar correo.\n\n" 
    msg+= "/AgregarContrasena: Agregar contraseña de correo.\n\n"
    msg+= "/verCorreo: ver correo y contraseña guardada.\n\n" 
    msg+= "/reiniciar: Reinicia el sistema, enviar nuevamente /start despues de que se reinicie.\n\n"
    msg+= "Cargar cara para Registro Facial:\n<i>1)</i> Grabe un video de por lo menos 10 segundos y espere que se guarde.\n\n"
    msg+= "<i>2)</i> Al abrir la botonera ingresar el Nombre a registrar o puede cancelar la operacion.\n\n"
    msg+= "<i>3)</i> Una vez registrado el nombre, espere mientras SIHRFB registra la cara, le debe llegar un mensaje de 'Proceso Terminado'.\n"
    
    context.bot.sendMessage(chat_id=chat_id, text=msg, parse_mode="html")
 
#-----------------------------------------Funcion para la captura y suba de una foto desde la camara Pi---------------------------------------------
def foto(update, context):
    chat_id = update.message.chat_id
    camera = PiCamera()
    camera.rotation = 180
    camera.resolution = (1280, 720)
    context.bot.sendMessage(chat_id, 'Sacando Foto')
    context.bot.sendChatAction(chat_id, 'upload_photo')
    #Tiempo de calentamiento de la cámara
    sleep(2)
    #Capturando la foto
    camera.capture('foto.png', format='png', use_video_port=False)
    camera.close()
    #Abriendo archivo creado y enviandolo
    photofile = open('foto.png', 'rb')
    context.bot.sendPhoto(chat_id, photo=photofile)

#-----------------------------------------Funcion para la grabacion y suba de video desde la camara Pi---------------------------------------------
def video(update, context):
    camera = PiCamera()
    camera.rotation = 180
    camera.resolution = (1280, 720)
    chat_id = update.message.chat_id
    context.bot.sendMessage(chat_id, 'Espere unos Segundos mientras se sube el Video')
    context.bot.sendChatAction(chat_id, 'record_video') #Le dice al usuario que algo está sucediendo del lado del bot
    #Creo el archivo y empiezo la grabacion
    filename = "./video_22"
    camera.start_recording(filename + ".h264")
    camera.wait_recording(5)
    camera.stop_recording()
    camera.close() #método para liberar los recursos de la cámara
    #Transformo el formato .h264 a .mp4 llamando por consola
    command = "MP4Box -add " + filename + '.h264' + " " + filename + '.mp4'
    call([command], shell=True)
    #Envio el video
    context.bot.sendChatAction(chat_id, 'upload_video')
    context.bot.sendVideo(chat_id, video = open(filename + '.mp4', 'rb'))
    context.bot.sendMessage(chat_id, 'video enviado')
    #Elimino los archvios creados asi no tengo problemas de espacio
    command = "rm " + filename + '.h264'
    call([command], shell=True)
    command = "rm " + filename + '.mp4'
    call([command], shell=True)

#-----------------------------------------Funcion para reproducir una nota de voz recibida desde el BOT---------------------------------------------
def reciboaudio(update, context):
    file = context.bot.getFile(update.message.voice.file_id) #Al recibir una nota de voz, la descargo y la guardo.
    file.download('voice.m4a')
    os.system('/usr/bin/cvlc --play-and-exit /home/david/facial/voice.m4a 2>/dev/null') #Ejecuto VLC y reproduzco el archivo enviado en la raspberry.

#-----------------------------------------Funcion para enviar una nota de voz al BOT---------------------------------------------
def enviarAudio(nro, framw):
    global chat_id
    dispatcher.bot.sendChatAction(chat_id, 'record_audio') #al usar el dispatcher, no es necesario usar context. Avisa que esta grabando un Audio.
    command = 'sox voice.wav voice.ogg' #Comando para transformar de wav a ogg, usando sox.
    call([command], shell=True)
    dispatcher.bot.sendVoice(chat_id, voice = open('voice.ogg', 'rb'))

#-----------------------------------------Funcion listar caras registradas--------------------------------------------
def lista_cara(update,context):
    dataPath = '/home/david/facial/Data'
    personaList = os.listdir(dataPath)
    chat_id = update.message.chat_id
    if os.listdir(dataPath):
        context.bot.sendMessage(chat_id, text=f'Listando personas: \n {personaList}')
        button1 = InlineKeyboardButton(text='Si',callback_data='eliminarNombre') 
        button2 = InlineKeyboardButton(text='No',callback_data='cancelar')

        update.message.reply_text(text='¿Quiere eliminar alguna persona?', reply_markup=InlineKeyboardMarkup([
            [button1, button2]])
        )
    else:
        context.bot.sendMessage(chat_id, text="No se encuentran personas registradas por el momento.")

#------------------------------------------------Funciones para eliminar caras registradas--------------------------------------
def eliminar_persona(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Escriba el nombre de la persona a eliminar:")
    return INPUT_TEXT2

def input_text2(update, context):
    nombre = update.message.text
    dataPath = '/home/david/facial/Data'
    personaPath = dataPath + '/' + nombre
    if os.path.exists(personaPath):
        dispatcher.bot.sendMessage(chat_id, text=f'Carpeta con el Nombre {nombre} econtrado y eliminado.\u2705')
        command = "rm -r " + personaPath
        call([command], shell=True)
    else:
        dispatcher.bot.sendMessage(chat_id, text=f'No se encuentra el nombre de: <ins>{nombre}</ins>.\u203C\uFE0F', parse_mode="HTML")

    return ConversationHandler.END

#-----------------------------------------Funcion para recibir un Video desde el BOT y utilizarlo para el reconocimiento facial---------------------------------------------
def reciboVideo(update, context):
    #Con esta funcion en caso de recibir video de telegram lo guardo
    file = context.bot.getFile(update.message.video.file_id)
    file.download('video.mp4')
    button1 = InlineKeyboardButton(text='Agregar Nombre',callback_data='nombre') #Al apretar aca hago un call con el dato "nombre" y me llama al manejador CallbackQueryHandler
    button2 = InlineKeyboardButton(text='Cancelar',callback_data='cancelar')

    update.message.reply_text(text='Agregue el Nombre o cancele la operación.', reply_markup=InlineKeyboardMarkup([
        [button1, button2]
         ])
    )

#-----------------------------------------Funcion para cancelar lo de agregar nombre--------------------------------------------
def cancelar(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="\u274C Operacion Cancelada. \u274C")
    #La funcion scandir() actúa como un iterador en lugar de devolver una lista.
    #Devuelve objetos de tipo DirEntry que, además del nombre, contienen otros atributos que indican si el objeto es un fichero, un directorio, su número inode o su ruta completa.
    '''
    with os.scandir(dir) as ficheros: 
        for fichero in ficheros:
            if fichero.name == 'video.mp4':
                command = "rm " + 'video.mp4'
                call([command], shell=True)
    '''
    return ConversationHandler.END

#-----------------------------------------Funciones para registrar el nombre y crear la carpeta-------------------------------------------
def registro_cara(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Escriba el nombre a guardar por favor: ")
    return INPUT_TEXT

def input_text(update, context):
    nombre = update.message.text
    dataPath = '/home/david/facial/Data'
    personaPath = dataPath + '/' + nombre

    if os.path.exists(personaPath):
        dispatcher.bot.sendMessage(chat_id, '\u203C\uFE0F Ya existe esta carpeta con este nombre, volver a grabar y registrar otro Nombre.')
        command = "rm " + 'video.mp4'
        call([command], shell=True)
        return
    else:
        dispatcher.bot.sendMessage(chat_id, text=f'\u2705 Carpeta creada con el nombre de: {nombre}.')
        os.makedirs(personaPath)

    ReconocerCara(nombre)
    return ConversationHandler.END

#-----------------------------------------Funciones  para registrar la cara y entrenarla-------------------------------------------
def ReconocerCara(nombre):
    global chat_id
    dataPath = '/home/david/facial/Data'
    personaPath = dataPath + '/' + nombre
    dispatcher.bot.sendMessage(chat_id, '\u26A0\uFE0F Espere mientras se registra la Cara \u231A.')
    cap = cv2.VideoCapture('video.mp4') #Lee el video recibido desde telegram.
    faceClassif = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    count = 0
    while True:
        ret, frame = cap.read() #lee los fotogramas de una cámara y ret comprueba el retorno en cada fotograma.
        if ret == False:
            break

        frame = imutils.resize(frame, width=640) #Se redimensiona la imagen, esto lo hago para redimensionar el tamaño de los fotogramas del video de entrada.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #función cvtColor() para escalar en gris la imagen. Frame se convierte en gris.
        auxFrame = frame.copy()
        faces = faceClassif.detectMultiScale(gray,1.3,5)

        for(x,y,w,h) in faces:
            #cv2.rectangle(frame, (x,y),(x+w,y+h), (0,255,0),2) #dibuja una forma rectangular en la imagen, para despues poder extraer esa parte de la imagen.
            rostro = auxFrame[y:y+h, x:x+w]
            rostro = cv2.resize(rostro, (150,150), interpolation=cv2.INTER_CUBIC) #Se redimensionan las imagenes para que todas posean el mismo tamaño.INTER_CUBIC se usa para hacer zoom.
            cv2.imwrite(personaPath + '/rostro_{}.jpg'.format(count), rostro) #cv2.imwrite() para guardar una imagen. El primer argumento es el nombre del archivo, el segundo argumento es la imagen que desea guardar.
            count = count + 1 #contador creciente para que muestre el número de fotogramas creados

        k = cv2.waitKey(1)
        if k == 27 or count >= 30:
            break
    dispatcher.bot.sendMessage(chat_id, '\u2705 Proceso de registro de cara terminado!')
    command = "rm " + 'video.mp4'
    call([command], shell=True)
    cap.release() #libera recurso de software y hardware de la camara, porque si no salta un error en donde dice: Dispositivo o recurso ocupado.
    entrenamiento(dataPath)
    cv2.destroyAllWindows()

def entrenamiento(dataPath):
    global chat_id
    dispatcher.bot.sendMessage(chat_id, '\u26A0\uFE0F Espere mientras se Entrenan las caras.')
    personaList = os.listdir(dataPath) #Lista directorios
    #Creamos dos Array, esto es porque  la computadora debe saber a quien corresponde cada cara
    #por lo que le asignamos etiquetas, asi se puede diferenciar de una persona de otra.
    labels = []
    facesData = []
    label = 0
    
    for nameDir in personaList: #Con este for especificamos la ruta en donde se van a leer las imagenes.
        personaPath = dataPath + '/' + nameDir
        dispatcher.bot.sendMessage(chat_id, text=f'Leyendo las imagenes de: {nameDir}')

        for fileName in os.listdir(personaPath): # #En este for lo que hacemos es leer cada uno de los rostros.
            labels.append(label) #Ahora almacenamos los rostros con sus respectivas etiquetas.#En labels añadiremos lo que seria la etiqueta.
            facesData.append(cv2.imread(personaPath + '/' + fileName,0)) #en facesData añadiremos a cada una de las imagenes a escala de grises. 
            #cv2.imread() El primer argumento es el nombre de la imagen, El segundo argumento es una bandera que especifica la forma en que se debe leer la imagen.
            #El segundo argumento en 0 (cero) especifica que la imagen se leerá en modo de escala de grises.

        label = label + 1 #Ahora incrementamos el valor label para que asigne valores, 0 a la primera carpeta, 1 a la segunda y asi sucesivamente.

    face_recognizer = cv2.face.LBPHFaceRecognizer_create() #Método para entrenar el reconocedor
    dispatcher.bot.sendMessage(chat_id, 'Entrenando\u203C\uFE0F')
    face_recognizer.train(facesData, np.array(labels)) #Entrenando el reconocedor de rostros
    face_recognizer.write('modeloLBPHFace.xml') #Almacenando el modelo obtenido
    dispatcher.bot.sendMessage(chat_id, text=f"\U0001f601 Modelo almacenado! Listo para poder ingresar por Registro Facial las siguientes personas:\n {personaList}")

#-----------------------------------------Funcion para correr un Hilo y ejectuar el reconocimiento facial-------------------------------------------
def Registro_Facial(update, context):
    global chat_id
    dataPath = '/home/david/facial/Data' #Carpeta donde se almacenan los rostros, que seria en Data
    imagePaths = os.listdir(dataPath)
    face_recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_recognizer.read('modeloLBPHFace.xml')
    cap = cv2.VideoCapture(0)
    count = 0
    faceClassif = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    dispatcher.bot.sendMessage(chat_id, 'Sistema de Reconocimiento Facial listo. Acerquese a la camara')
    while True:
        ret,frame = cap.read()
        frame = cv2.rotate(frame, cv2.ROTATE_180) 
        if ret == False: break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        auxFrame = gray.copy()

        faces = faceClassif.detectMultiScale(gray,1.3,5)

        for (x,y,w,h) in faces:
            rostro = auxFrame[y:y+h,x:x+w]
            rostro = cv2.resize(rostro,(150,150),interpolation= cv2.INTER_CUBIC)
            result = face_recognizer.predict(rostro)

            if result[1] < 80:
                nombre = '{}'.format(imagePaths[result[0]])
                dispatcher.bot.sendMessage(chat_id, f'Persona Reconococida: {nombre}')
                relay = gpiozero.OutputDevice(RELAY_PIN, active_high=False, initial_value=False)
                relay.on() # Activa el RELE una vez detectada la cara
                dispatcher.bot.sendMessage(chat_id, "Rele de puerta en estado: Encendido")
                sleep(5) # Espera de 5 segundos
                relay.off() # Apaga el RELE
                dispatcher.bot.sendMessage(chat_id, "Rele de puerta en estado: Apagado")
                cap.release()
                cv2.destroyAllWindows()
            else:
                dispatcher.bot.sendMessage(chat_id, 'No se reconoce la cara, intentelo de nuevo!')
                count = count + 1
                if count == 15:
                    dispatcher.bot.sendMessage(chat_id, 'Se acabaron los intentos sistema apagado.')
                    cap.release()
                    cv2.destroyAllWindows()
    #dispatcher.bot.sendMessage(chat_id, 'APAGADO')
    cap.release()
    cv2.destroyAllWindows()
  
#--------------------------------------------Avisa cuando alguien toca el timbre, reproduce el sonido de timbre y envia una foto -----------------
def timbre(update, context):
    global chat_id
    camera = PiCamera()
    camera.rotation = 180
    camera.resolution = (1280, 720)
    dispatcher.bot.sendMessage(chat_id, '\U0001f6ce\uFE0F Alguien esta tocando el timbre!\nSacando Foto.')
    os.system('/usr/bin/cvlc --play-and-exit /home/david/facial/Doorbell.wav 2>/dev/null') #Ejecuta el audio grabado
    dispatcher.bot.sendChatAction(chat_id, 'upload_photo')
    sleep(2) #Tiempo de calentamiento de la cámara
    camera.capture('foto.png', format='png', use_video_port=False) #Capturando la foto
    camera.close()
    photofile = open('foto.png', 'rb') #Abriendo archivo creado y enviandolo
    dispatcher.bot.sendPhoto(chat_id, photo=photofile)

    enviarcorreo = mp.Process(target= correos) #Creo un subproceso para enviar el correo al email.
    enviarcorreo.start()
    enviarcorreo.join()

#--------------------------------------------Funciona para guardar email ------------------------------------------------------------
def AgregarCorreo(update, context):
    button1 = InlineKeyboardButton(text='Agregar Correo',callback_data='ncorreo') # Llama a la funcion correo1
    button2 = InlineKeyboardButton(text='Cancelar',callback_data='cancelar')    #Llama a la funcion cancelar (linea 161)

    update.message.reply_text(text='Eliga una Opcion:', reply_markup=InlineKeyboardMarkup([
        [button1, button2]
         ]))

def correo1(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Escriba el correo (gmail) a agregar: ")
    return INPUT_TEXT3

def input_text3(update, context):
    global chat_id
    correo = update.message.text
    dispatcher.bot.sendMessage(chat_id, text=f'Correo: {correo} Guardado.')
    archivo = open ("/home/david/facial/correo.txt", "w") #Creo y abro el archivo como solo escritura.
    archivo.write(correo) #Escribo el gmail.
    archivo.close
    return ConversationHandler.END
 
#--------------------------------------------Funciona para guardar contraseña -------------------
def AgregarContrasena(update, context):
    button1 = InlineKeyboardButton(text='Agregar Contraseña',callback_data='acontra')
    button2 = InlineKeyboardButton(text='Cancelar',callback_data='cancelar')

    update.message.reply_text(text='Eliga una Opcion:', reply_markup=InlineKeyboardMarkup([
        [button1, button2]
         ]))

def correo2(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Escriba la contraseña que te genero en 'contraseña de aplicaciones': ")
    return INPUT_TEXT4

def input_text4(update, context):
    global chat_id
    correo2 = update.message.text
    dispatcher.bot.sendMessage(chat_id, text=f'Contraseña: {correo2} Guardada.')
    archivo = open ("correo2.txt", "w")
    archivo.write(correo2)
    archivo.close
    return ConversationHandler.END

#---------------------------------------- Funcion para abrir la puerta con el rele --------------------------------------------------------
def puerta(update, context):
    global chat_id
    relay = gpiozero.OutputDevice(RELAY_PIN, active_high=True, initial_value=False)
    relay.on() # Rele on
    dispatcher.bot.sendMessage(chat_id, "Rele de puerta en estado: Encendido")
    sleep(5)
    relay.off() # rele off
    dispatcher.bot.sendMessage(chat_id, "Rele de puerta en estado: Apagado")

#---------------------------------------- Funcion para encender o apagar el sensor PIR--------------------------------------------------------
def pir(update, context):
    button1 = InlineKeyboardButton(text='Encender',callback_data='encender') #Al apretar aca hago un call con el dato "nombre" y me llama al manejador CallbackQueryHandler
    button2 = InlineKeyboardButton(text='Apagar',callback_data='apagar')

    update.message.reply_text(text='¿Encender o Apagar sensor de movimiento?.', reply_markup=InlineKeyboardMarkup([
        [button1, button2]
         ])
    )

def encender(update, context):
    query = update.callback_query
    global estado
    if estado == 1:
        query.edit_message_text(text="El sensor PIR ya esta encendido!")
        return ConversationHandler.END
    elif estado == 0:
        estado = 1
        pir_start(estado)
        query.edit_message_text(text="Sensor de movimiento encendido")
        return ConversationHandler.END

def apagar(update, context):
    query = update.callback_query
    global estado
    if estado == 0:
        query.edit_message_text(text="El sensor PIR ya esta apagado")
        return ConversationHandler.END
    elif estado == 1:
        estado = 0
        pir_start(estado)
        query.edit_message_text(text="Sensor de movimiento apagado")
        return ConversationHandler.END

def pir_start(valor): #Arranco para empezar a usar el PIR
    valor=int(valor)
    global t
    if valor == 1:
        t = threading.Thread(target=pir_running)
        t.start()
    elif valor == 0:
        t.do_run = False
        #print("se apago") era para verificar si llegaba a este punto

def pir_running(): #Funcion para correr el PIR, al usar hilos no me traba los demas programas
    global chat_id
    global t
    pir = MotionSensor(4)
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        pir.wait_for_motion()
        dispatcher.bot.sendMessage(chat_id, "Se detecta presencia en puerta de entrada!")
        pir.wait_for_no_motion()
#---------------------------------------- VISUALIZADOR DE ARCHIVOS -----------------------------------------------------------------------------
def vercorreo(update, context):
    global chat_id
    archivo=open("/home/david/facial/correo.txt")
    dispatcher.bot.sendMessage(chat_id, text=f'Correo guardado: {archivo.read()}')
    archivo1=open("/home/david/facial/correo2.txt")
    dispatcher.bot.sendMessage(chat_id, text=f'Contraseña guardada: {archivo1.read()}')
    archivo.close
    archivo1.close
#---------------------------------------- Prender LUZ CORREGIR -----------------------------------------------------------------------------
def prenderluz(update, context):
   global chat_id
   luz = gpiozero.OutputDevice(LUZ_PIN, active_high=True, initial_value=False)
   luz.on() # Rele on
   dispatcher.bot.sendMessage(chat_id, "Luz encendida")
   sleep(5)
   luz.off() # rele off
   dispatcher.bot.sendMessage(chat_id, "Luz apagada")

#---------------------------------------- Saber direccion IP de la Raspberry -----------------------------------------------------------------------------
def IP(update, context):
   global chat_id
   ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
   dispatcher.bot.sendMessage(chat_id, text=f'La direccion IP de la Raspberry PI es: {ip}')

#---------------------------------------- Funcion para reiniciar el sistema-----------------------------------------------------------------------------
def reinicar(update, context):
    global chat_id
    button1 = InlineKeyboardButton(text='SI',callback_data='si') #Al apretar aca hago un call con el dato "si" y me llama al manejador CallbackQueryHandler
    button2 = InlineKeyboardButton(text='NO',callback_data='cancelar')

    update.message.reply_text(text='¿ESTA SEGURO QUE QUIERE REINICIAR EL SISTEMA?.', reply_markup=InlineKeyboardMarkup([
        [button1, button2]
         ])
    )
    
def si(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_tex(text="Reiniciando Sistema, espere unos minutos y mande nuevamente el comando /start")
    sleep(3)
    command = "sudo reboot now"
    call([command], shell=True)


#---------------------------------------- MAIN -----------------------------------------------------------------------------
if __name__== '__main__':

    #Creo el PID para relacionar los procesos de grabar audio y el toque de timbre y asi cuando lo grabo, lo puedo enviar.
    f = open('pid.txt','w') #Creo un archivo texto, donde almaceno el pid del padre.
    f.write(str(os.getpid())) #Escribo el PID.
    f.close()

    #--------Recepcion de señales--------------
    signal.signal(signal.SIGUSR1, enviarAudio)
    signal.signal(signal.SIGUSR2, timbre)
    
    updater = Updater(token=bot_token, use_context=True) #updater es para saber la peticiones que va recibiendo el bot, el use_context es una variable obligatoria a pasar.
    dispatcher = updater.dispatcher #El dispatcher es el que se encarga de enviar las acciones recibidas. Despachador que maneja las actualizaciones y las despacha a los manejadores.

#-----------------------------------------Creacion de los Manejadores---------------------------------------------
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('info', info))
    dispatcher.add_handler(CommandHandler('foto', foto))
    dispatcher.add_handler(CommandHandler('video',video))
    dispatcher.add_handler(CommandHandler('puerta',puerta))
    dispatcher.add_handler(CommandHandler('prenderluz',prenderluz))
    dispatcher.add_handler(CommandHandler('AgregarCorreo',AgregarCorreo))
    dispatcher.add_handler(CommandHandler('vercorreo',vercorreo))
    dispatcher.add_handler(CommandHandler('AgregarContrasena', AgregarContrasena))
    dispatcher.add_handler(CommandHandler('pir',pir))
    dispatcher.add_handler(CommandHandler('listarCaras',lista_cara))
    dispatcher.add_handler(CommandHandler('RFacial',Registro_Facial))
    dispatcher.add_handler(CommandHandler('Ip',IP))
    dispatcher.add_handler(CommandHandler('reiniciar',reinicar))
    dispatcher.add_handler(MessageHandler(Filters.voice,reciboaudio))
    dispatcher.add_handler(MessageHandler(Filters.video,reciboVideo))

#----------------------------------------------Creacion de Conversaciones -----------------------------------------------------------
    dispatcher.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(pattern='nombre', callback=registro_cara), 
                    CallbackQueryHandler(pattern='cancelar', callback=cancelar),
                    CallbackQueryHandler(pattern='eliminarNombre', callback=eliminar_persona),
                    CallbackQueryHandler(pattern='ncorreo', callback=correo1),
                    CallbackQueryHandler(pattern='acontra', callback=correo2),
                    CallbackQueryHandler(pattern='encender', callback=encender),
                    CallbackQueryHandler(pattern='apagar', callback=apagar),
                    CallbackQueryHandler(pattern='SI', callback=si)],
        states={INPUT_TEXT: [MessageHandler(Filters.text, input_text)],
               INPUT_TEXT2: [MessageHandler(Filters.text, input_text2)],
               INPUT_TEXT3: [MessageHandler(Filters.text, input_text3)],
               INPUT_TEXT4: [MessageHandler(Filters.text, input_text4)]},
        fallbacks=[]
    ))

    #Ejecute el bot hasta que la usuario presione Ctrl-C
    updater.start_polling()
    #updater.idle()
