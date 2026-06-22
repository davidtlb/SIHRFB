import os
import signal
import wave
import pyaudio
from gpiozero import Button

def grabar(pid_bot, btn):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 2
        RATE = 44100
        WAVE_OUTPUT_FILENAME = "voice.wav"

        p = pyaudio.PyAudio()
        #Abro la entrada de objetos para el stream
        stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)
        print ("* grabando")
        frames = []
 
        while btn.value:
            data = stream.read(CHUNK)
            frames.append(data)

        print("* grabacion completa")
        stream.stop_stream()
        stream.close
        p.terminate()
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        os.kill(pid_bot, signal.SIGUSR1)
