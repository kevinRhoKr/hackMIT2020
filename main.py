
import requests #for POST/api
import json #for .json files
import signal
import subprocess
import time
import threading
import os
import socket

#display
from board import SCL, SDA
from PIL import Image, ImageDraw, ImageFont
import busio
import adafruit_ssd1306

import RPi.GPIO as GPIO
# LED and button of GPIO for recording

# Create the I2C interface for display
i2c = busio.I2C(SCL, SDA)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c) #adafruit OLED I2C display
display.fill(0) #clear display
display.show()
font = ImageFont.load_default()

subscription_key = 'PRIVATE INFORMATION'
fetch_token_url = 'PRIVATE INFORMATION'

recording_time = 10 #in seconds, max

sound_filename = '/mnt/ramdisk/sound.wav' #.wav file directory
arecord_cmd = '/mnt/ramdisk/arecord -D plughw:1,0 -f S16_LE -r 16000 -d {} /mnt/ramdisk/sound.wav'.format(recording_time) #raspberry pi built-in recording program
usb_reset_cmd = '/mnt/ramdisk/uhubctl -a 2 -p 1 -d 0.3' #usb reset every run to allow for re-recording

arecord_process = ''

GPIO.setmode(GPIO.BCM) # set Broadcom SOC Channel
GPIO.setwarnings(False) #disable warnings
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Button to GPIO23
GPIO.setup(24, GPIO.OUT)  # LED to GPIO24

def get_button_status(pin=23): #pressed or not
    return GPIO.input(pin)

def set_recording_led(status, pin=24): #LED on or not
    GPIO.output(pin, status)

def usb_reset(): #usb reset (after every loop)
    t = subprocess.Popen(usb_reset_cmd.split(), stdout=subprocess.PIPE, shell=False)
    t.communicate()

def recording(): #recording using arecord (built-in audio recording)
    global arecord_process

    arecord_process = subprocess.Popen(arecord_cmd.split(), stdout=subprocess.PIPE, shell=False)
    arecord_process.communicate()

def speech2txt():
    msg = voice_service() #function 2 voice_service()
    text_page_display(msg)
    print(msg)

def voice_service():
    try:
        with open(sound_filename, 'rb') as f: #open the sound.wav and read as a binary
            data = f.read()
            headers = {
                'Ocp-Apim-Subscription-Key': subscription_key, #in dict
                'Accept': 'applicatiotexn/json;t/xml',
                'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
            }
            response = requests.post(fetch_token_url, headers=headers, data=data) #POST api
            if response.status_code <= 200:
                r = response.json() #  .json
                print(json.dumps(r, indent=2))
                try:
                    return r['NBest'][0]['Display'] #get the message 'Display:'
                except:
                    return "I can't hear you. try again." #error message 1
            else:
                if response.status_code == 400:
                    return 'error: Bad request' #erroe message 2
                elif response.status_code <= 401:
                    return 'error: Unauthorized' #error message 3
                elif response.status_code <= 403:
                    return 'error: Forbidden' #error message 4

                return 'unknown error' #error message 5
    except Exception as e:
        return str(e)

def get_ip_address(): #documentarion from online (raspberrypi.org forums)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def draw_text(x, y, display, draw, image, text): #'drawing' the text
    line = ''
    for i in range(0, len(text), 4):
        line += text[i:i+4]

        draw.text((x, y), line, font=font, fill=255)

        #info about the parameters above:
            #(x,y) <-- coordinate for the display i.e. (0,0) means top left corner
            #line <-- the text that we want to print (but by 4 at a time to create dynamic movements)
            #fill <-- RGB color (255 is white)

        display.image(image)
        display.show()
        time.sleep(0.2)

def text_page_display(text, d=0): #took reference/help from the adafruit website
    width = display.width
    height = display.height

    image = Image.new("1", (width, height)) 
    #the first parameter is for the 'mode'. Where mode '1' means 1 pixel per byte.
    #the tuple (width, height) is for the size


    #draw.rectangle is for the background initializing. Basically, to a black background screen.

    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    padding = -2
    top = padding
    bottom = height - padding

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    chunk_size = 20

    text = text.replace('\n', ' {NL} ')

    message_list = []
    line = ''


    for m in text.split(): #adding line by line (each line as an element in the list)
        if m == '{NL}': #new line --> append and then initialize the line to an empty string
            message_list.append(line)
            line = ''
        elif len(line) + len(m) + 1 > chunk_size: #if the word we are adding exceeds the limit size or the 'chunk_size'
            message_list.append(line) #append...
            line = m #...and put the word on the next line
        else:
            if len(line) > 0: #line is already created
                line += ' ' + m #add the word with space in front
            else:
                line += m #add the word (beginning)

    if len(line) > 0:
        message_list.append(line) #last remaining line/words

    i = 1
    font_height = 12
    for m in message_list:
        # draw.text((0, top), m, font=font, fill=255)
        #top <-- padding
        #display <-- OLED display..
        draw_text(0, top, display, draw, image, m) #function call to draw_text (prints to the screen)

        if m == message_list[-1]: #if this is the last message on the list,
            break

        if i % 3 == 0: #if this is the third row on the display
            top = padding #the first padding
            time.sleep(4) #wait/sleep for 4 sec
            draw.rectangle((0, 0, width, height), outline=0, fill=0) #then start again from row 1/top row
        else:
            top += font_height #change padding to increase the row/line on the display

        i += 1


if __name__ == '__main__':
    usb_reset()
    time.sleep(1)

    print('start...')
    text_page_display('Ready\n\n' + get_ip_address())# display ip address on the screen
    print(get_ip_address())
    print('ready!')

    while True:
        while get_button_status() == False:
            time.sleep(0.1)

        print('start recording.')
        set_recording_led(True)

        t = threading.Thread(target=recording) #start recording, run in background
        t.setDaemon(True) # allow the main from exiting
        t.start()

        while get_button_status() == True: #recording while you pressed down the button
            time.sleep(0.2)
            continue

        set_recording_led(False)
        arecord_process.terminate() #stop recording

        print('stop recording')

        print('convert sound.wav file to text string.')
        t = threading.Thread(target=speech2txt) # API process and printing the message onto the OLED Display
        t.setDaemon(True)
        t.start()

        print('usb reset')
        usb_reset() #reset to start again






