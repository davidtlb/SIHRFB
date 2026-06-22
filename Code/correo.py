from cgitb import html
from multiprocessing import context
import time
from time import sleep
from time import gmtime, strftime
import datetime
import smtplib, ssl
from email.mime.image import MIMEImage
from email.mime.text import MIMEText #mime signifca mensajes multimedias, importamos texto
from email.mime.multipart import MIMEMultipart #importamos multiparte, en donde se puede encontrar el ASUNTO, formato, etc.

#----------------------------------------Ingresar los datos de tu gmail.--------------------------------------
#email_address = ''
#email_password = '' #contraseña que te genero en 'contraseña de aplicaciones'
#email_receiver = '' #Destinatario

def correos():
    p = open('correo.txt','r')
    email_address = str(p.readline())

    p = open('correo2.txt','r')
    email_password = str(p.readline())
#-----------------------------------------Crear el mensaje-----------------------------------------------------
    mensaje = MIMEMultipart("alternative") #Estandar
    mensaje["Subject"] = "TIMBRE CASA"
    mensaje["From"] = email_address
    mensaje["To"] = email_address
    d = time.strftime("%H:%M %p del %d-%m-%Y")
#Ponemos el formato en html
    html = f""" 
    <html>
    <body>
        Hola,<br> 
        Alguien está tocando el timbre a las %s, te adjunto foto.<br>
        ¡Qué tengas un lindo día!
    </body>
    </html>
    """ %(d) #Lo que hago aca es pasar dia y hora que se tomo la foto
# las tres comillas me dejan escribir un string largo, <br> es salto de linea y poner entre <b> </b> se pone en negrita
# el contenido del mensaje como HTML
    parte_html = MIMEText(html, "html")

#--------------------------------------Abro la imagen y la cargo---------------------------------------------------
    f = open("foto.png", "rb")
    image = f.read()
    f.close()
    parte_imagen = MIMEImage(image)

#-------------------------------------agregar los contenidos al mensaje-----------------------------------------------------
    mensaje.attach(parte_html)
    mensaje.attach(parte_imagen)
#-------------------------------Crear la conexion y enviar el mensaje---------------------------------------------------------------
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(email_address,email_password) #Inicio de sension
        print("Inicio de sesion")
        server.sendmail(email_address, email_address, mensaje.as_string()) #Enviar email, mensaje.as_string() envia el mensaje como string
        print("Mensaje enviado")