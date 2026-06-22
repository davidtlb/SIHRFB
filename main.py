import multiprocessing as mp
import signal
import os
from time import sleep
import subprocess as sp
from record import grabar
from gpiozero import Button

btn = Button(23)
btn2 = Button(27)

def main():
    proc=sp.Popen(["python","/home/david/facial/todo.py", "2>/dev/null"]) #Abro primero el archivo de Telegram asi tengo su PID.
    grabando = False
    sleep(10) #Espero 10 segundos asi se carga el archivo de telegram y guarda el PID.
    f = open("pid.txt","r")
    pid1 = f.read()
    f.close()
    print(pid1)

    while True:
        #---------------------Boton para grabar audio--------------------------
        if btn.value:
            grabacion = mp.Process(target= grabar, args=(int(pid1), btn))
            grabacion.start()
            grabando = True
        if grabando:
            grabacion.join()
            grabando = False
        #--------------------Boton del timbre-----------------------
        if btn2.is_pressed:
            os.kill(proc.pid, signal.SIGUSR2)
            sleep(2)

if __name__ == '__main__':
    main()
