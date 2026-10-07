import pygame
from google import genai
from google.genai import types 
from elevenlabs import ElevenLabs
from random import Random

from bs4 import BeautifulSoup
import re
import os
from playsound3 import playsound
import sys
import pytchat
import time
import pyaudio
import wave
import threading
import json
import socket
from emoji import demojize
from config import *
import numpy as math
from gtts import gTTS
from mutagen import mp3
import time as time_module
import discord
import aiohttp
pygame.init()
pygame.mixer.init()
pygame.font.init()

# ฟังก์ชันสำหรับวาดปุ่มที่สวยงาม
def draw_gradient_button(surface, rect, color1, color2, text, text_color, font, border_radius=10):
    """วาดปุ่มที่มี gradient และมุมโค้ง"""
    # สร้าง gradient surface
    gradient_surf = pygame.Surface((rect.width, rect.height))
    for y in range(rect.height):
        ratio = y / rect.height
        r = int(color1[0] * (1-ratio) + color2[0] * ratio)
        g = int(color1[1] * (1-ratio) + color2[1] * ratio)
        b = int(color1[2] * (1-ratio) + color2[2] * ratio)
        pygame.draw.line(gradient_surf, (r, g, b), (0, y), (rect.width, y))
    
    # วาดปุ่มกลม
    pygame.draw.rect(surface, color1, rect, border_radius=border_radius)
    surface.blit(gradient_surf, rect.topleft)
    
    # เพิ่มเงา
    shadow_rect = rect.copy()
    shadow_rect.x += 3
    shadow_rect.y += 3
    pygame.draw.rect(surface, (50, 50, 50, 100), shadow_rect, border_radius=border_radius)
    
    # วาดเส้นขอบ
    pygame.draw.rect(surface, (255, 255, 255, 150), rect, width=2, border_radius=border_radius)
    
    # วาดข้อความ
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)

def draw_modern_button(surface, rect, base_color, text, font, is_hovered=False, is_pressed=False):
    """วาดปุ่มสไตล์โมเดิร์น - กลับมามีกรอบปุ่ม"""
    # กำหนดสี
    if is_pressed:
        color = tuple(max(0, c - 30) for c in base_color)
    elif is_hovered:
        color = tuple(min(255, c + 20) for c in base_color)
    else:
        color = base_color
    
    # วาดเงา
    shadow_rect = rect.copy()
    shadow_rect.x += 2
    shadow_rect.y += 2
    pygame.draw.rect(surface, (0, 0, 0, 80), shadow_rect, border_radius=15)
    
    # วาดปุ่ม
    pygame.draw.rect(surface, color, rect, border_radius=15)
    
    # เส้นขอบ gradient
    border_color = tuple(min(255, c + 40) for c in color)
    pygame.draw.rect(surface, border_color, rect, width=3, border_radius=15)
    
    # ข้อความ
    text_color = (255, 255, 255) if sum(base_color) < 400 else (0, 0, 0)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)

v = pygame.Vector2(1920/1.3,1080/1.3)
i= 0
input_t = ""
font = pygame.font.SysFont("FONT/thai/THSarabunNew.ttf",50,False)

pygame.display.set_caption("Fuyuki Eri AI Chattering")
pygame.display.set_icon(pygame.image.load("image/fuyuki_eri_1.png"))
screen = pygame.display.set_mode(v,0,7,0,1)

clock = pygame.time.Clock()
input_dist = pygame.Rect(200,700,150,40)
eri_dist = pygame.Rect(1000,500,1080/2,1920/2)
eri_dist.center = (1800/2,1000/2)
color_input = pygame.Color(255,255,255,255)
t1 = ''
thumb = pygame.image
active_eri = 0
event_1 = ''
event_2 = ''
input_t = ""
txt = ["0"]
live_txt = [""]
live_t = ""
re_event = 0
live = ''
live_ti = ''
live_tr = 0
time_= 0
video_id = ''
AIeri = genai.client.Client(api_key="AIzaSyA8fy9JmTHh2XRPpzRiql2Dvuv8IjCQxLM")
AIeri_prop = ElevenLabs(api_key="sk_6e27122239fa83b00031e78e85ed8d43ab87b8e4789943da")
mp3time = None
conversation = []
# Create a dictionary to hold the message data
history = {"history": conversation}
output_file = ''
CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 48000
WAVE_OUTPUT_FILENAME = "input.wav"
p = pyaudio.PyAudio()

# สร้าง stream เริ่มต้น (จะถูกสร้างใหม่เมื่อเลือกอุปกรณ์)
try:
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
except:
    stream = None
    
frames = []

# ฟังก์ชันสร้าง audio stream ใหม่
def create_audio_stream(input_device_id=None):
    global stream, p
    try:
        if stream:
            stream.stop_stream()
            stream.close()
    
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=input_device_id,
                        frames_per_buffer=CHUNK)
        return True
    except Exception as e:
        print(f"Error creating audio stream: {e}")
        return False

mode = 0
total_characters = 0
chat = ""

chat_now = ""
chat_prev = [""]
is_Speaking = False
owner_name = "Hachifuma"
blacklist = ["Nightbot", "streamelements"]
time_t = 0
rando = Random().randrange(1,4,1)
rando_1 = Random().randrange(15,25,1)
db_level = 0
# ตัวแปรสำหรับอุปกรณ์เสียง
current_input_device_index = 0
current_output_device_index = 0
audio_device_names = {"input": [], "output": []}

fuyuki_defualt = thumb.load_extended("image/fuyuki_eri_1.png")
fuyuki_r_defualt = fuyuki_defualt.get_rect()
fuyuki_r_defualt.center = (500/2,1000 / 2)
fuyuki_defualt_ = [fuyuki_defualt,fuyuki_r_defualt]

fuyuki_speak = thumb.load_extended("image/fuyuki_eri_2.png")
fuyuki_r_speak = fuyuki_defualt.get_rect()
fuyuki_r_speak.center = fuyuki_r_defualt.center 
fuyuki_speak_ = [fuyuki_speak,fuyuki_r_speak]

fuyuki_closedeyes = thumb.load_extended("image/fuyuki_eri_3.png")
fuyuki_r_closedeyes = fuyuki_closedeyes.get_rect()
fuyuki_r_closedeyes.center = fuyuki_r_defualt.center 
fuyuki_closedeyes_ = [fuyuki_closedeyes,fuyuki_r_closedeyes]

fuyuki_closedeyes_speak = thumb.load_extended("image/fuyuki_eri_4.png")
fuyuki_r_closedeyes_speak = fuyuki_closedeyes.get_rect()
fuyuki_r_closedeyes_speak.center = fuyuki_r_defualt.center 
fuyuki_closedeyes_speak_ = [fuyuki_closedeyes_speak,fuyuki_r_closedeyes_speak]







text_start = font.render("*\\welcome to Fuyuki Eri's AI Chat/*",True,(255,255,255))
text_r_start = text_start.get_rect()  
text_r_start .center = (1000/2,40/2)
text_start_ = [text_start,text_r_start]



text_button = font.render("(Hold E to Record)",True,(255,255,255))
text_r_button = text_button.get_rect()  
text_r_button.center = (1500/2,40/2)
text_button_ = [text_button,text_r_button]

text_button_1 = font.render("(Release E to Stop & Process)",True,(255,255,255))
text_r_button_1 = text_button_1.get_rect()  
text_r_button_1.center = (1500/2,100/2)   
text_button_1_ = [text_button_1,text_r_button_1] 

text_rec = font.render("Recording...",True,(255,255,255))
text_r_rec = text_rec.get_rect()  
text_r_rec.center = (1000/2,40/2)
text_rec_ = [text_rec, text_r_rec]

text_stoprec = font.render("Stop Recording...",True,(255,255,255))
text_r_stoprec = text_stoprec.get_rect()  
text_r_stoprec.center = (1000/2,40/2)
text_stoprec_ = [text_stoprec,text_r_stoprec]




text_sel_id = font.render("Livestream ID: ",True,(255,255,255))
text_r_sel_id = text_sel_id.get_rect()  
text_r_sel_id.center = (1000/2,40/2)
text_sel_id_ = [text_sel_id,text_r_sel_id]

text_dis_live = font.render("(Press Enter to keep token and press F2 to start)",True,(255,255,255))
text_r_dis_live = text_dis_live.get_rect()  
text_r_dis_live.center = (1800/2,300/2)
text_dis_live_ = [text_dis_live,text_r_dis_live]
#for ui button - ออกแบบใหม่
# คำนวณตำแหน่งจากกลางหน้าจอ
center_x = v.x // 2
center_y = v.y // 2

# ปุ่มหลัก - จัดให้อยู่กึ่งกลางและสวยงาม
button_width = 300
button_height = 70
button_spacing = 90

r_button_voicechat = pygame.Rect(center_x - button_width//2, center_y - button_spacing, button_width, button_height)
voice_chat_color = (74, 144, 226)  # สีฟ้า

r_button_livechat = pygame.Rect(center_x - button_width//2, center_y, button_width, button_height)
live_chat_color = (231, 76, 60)  # สีแดง

r_button_audio_settings = pygame.Rect(center_x - button_width//2, center_y + button_spacing, button_width, button_height)
audio_settings_color = (155, 89, 182)  # สีม่วง

# ปุ่ม Back - มุมซ้ายบน
r_button_back = pygame.Rect(30, 30, 120, 50)
back_color = (149, 165, 166)  # สีเทา

r_button_discord = pygame.Rect(center_x - button_width//2, center_y + 200, button_width, button_height)
discord_color = (231, 76, 60) 
# UI สำหรับหน้าตั้งค่าเสียง - ปรับปรุงให้สวยงาม
device_button_width = 500
device_button_height = 50

r_button_input_device = pygame.Rect(center_x - device_button_width//2, 200, device_button_width, device_button_height)
input_device_color = (52, 152, 219)  # สีฟ้าเข้ม

r_button_output_device = pygame.Rect(center_x - device_button_width//2, 300, device_button_width, device_button_height)
output_device_color = (46, 204, 113)  # สีเขียว

# ปุ่ม Apply และ Refresh
action_button_width = 150
action_button_height = 60

r_button_apply_audio = pygame.Rect(center_x - action_button_width - 20, 400, action_button_width, action_button_height)
apply_color = (39, 174, 96)  # สีเขียวเข้ม

r_button_refresh_audio = pygame.Rect(center_x + 20, 400, action_button_width, action_button_height)
refresh_color = (230, 126, 34)  # สีส้ม

# กำหนดฟอนต์ที่สวยงาม
try:
    title_font = pygame.font.Font("FONT/thai/THSarabunNew Bold.ttf", 36)
    button_font = pygame.font.Font("FONT/thai/THSarabunNew Bold.ttf", 24)
    small_font = pygame.font.Font("FONT/thai/THSarabunNew.ttf", 18)
except:
    title_font = pygame.font.SysFont("Arial", 36, bold=True)
    button_font = pygame.font.SysFont("Arial", 24, bold=True)
    small_font = pygame.font.SysFont("Arial", 18)

# สร้างข้อความสำหรับปุ่มต่างๆ
text_back = small_font.render("◀ Back", True, (255, 255, 255))
text_input_device_label = button_font.render(" Input Device:", True, (255, 255, 255))
text_output_device_label = button_font.render(" Output Device:", True, (255, 255, 255))
text_apply_audio = button_font.render("✓ Apply", True, (255, 255, 255))
text_refresh_audio = button_font.render(" Refresh", True, (255, 255, 255))

at_part = ""
eri_speak = False