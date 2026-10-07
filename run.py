

from utils.subtitle import *
from utils.promptMaker import *
from utils.twitch_config import *
from object.obj_db import *
from utils.discord import client,dis_token


# สร้าง lock สำหรับป้องกันการใช้ไฟล์เสียงพร้อมกัน
audio_lock = threading.Lock()
# ป้องกันการประมวลผล AI พร้อมกัน
ai_processing = False

# ตัวแปรสำหรับอุปกรณ์เสียง
selected_input_device = None
selected_output_device = None
audio_devices = {"input": [], "output": []}

# ตัวแปรสำหรับการบันทึกเสียงแบบ Push-to-Talk
is_recording = False
was_e_pressed = False


# ฟังก์ชันรับรายการอุปกรณ์เสียง
def get_audio_devices():
    global audio_devices
    
    p = pyaudio.PyAudio()
    audio_devices = {"input": [], "output": []}
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            audio_devices["input"].append({
                "id": i,
                "name": info['name'],
                "channels": info['maxInputChannels']
            })
        if info['maxOutputChannels'] > 0:
            audio_devices["output"].append({
                "id": i,
                "name": info['name'],
                "channels": info['maxOutputChannels']
            })
    
    p.terminate()
    return audio_devices



def CharMove():  
    global active_eri , time_ , is_Speaking,rando,i,mp3time , output_file
    if active_eri == 0:
        screen.blit(fuyuki_defualt_[0],eri_dist)
    elif active_eri == 2:
           
          
        
        # ตรวจสอบว่าเสียงเล่นจบแล้วหรือยัง
        
        if not pygame.mixer.music.get_busy():
            # fallback: ถ้าเกินเวลาที่กำหนด
            
            pygame.mixer.music.unload()
            
            
            is_Speaking = False
            active_eri = 0
            time_ = 0
        else:
            is_Speaking = True 
            screen.blit(fuyuki_speak_[0],eri_dist)
                
    elif active_eri == 1:
        screen.blit(fuyuki_closedeyes_[0],eri_dist)
        if time_ >= 60*3/clock.get_fps():
            active_eri = 0
            time_= 0

# function to transcribe the user's audio
def transcribe_audio(file):
    global chat_now,chat_prev, is_Speaking, re_event , ai_processing
    
    try:
        ai_processing = True
        audio_file= open(file, "rb")
        transcript = AIeri_prop.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v1",
            language_code="th"
        )
        chat_ = transcript.text
        audio_file.close()
        
        if chat_ and len(chat_.strip()) > 0:
            chat_now = owner_name + " said " + chat_
            conversation.append({'role': 'user', 'content': chat_now})
            chat_prev.append(chat_now)
            print(f"Transcribed: {chat_}")
            
            # เรียก AI เพื่อตอบ
            threading.Thread(target=openai_answer).start()
        else:
            print("No speech detected")
        is_Speaking = False
            
            
    except Exception as e:
        print(f"Error in transcribe_audio: {e}")
        is_Speaking = False
        

# function to get an answer from OpenAI
def openai_answer():
    global total_characters, conversation, chat_now , chat ,chat_prev, ai_processing, is_Speaking, re_event,time_
    
    
    
    ai_processing = True
    
    try:
        prompt = getPrompt()
        total_characters = sum(len(d['content']) for d in conversation)

        while total_characters > 4000:
            try:
                conversation.pop(1)
                total_characters = sum(len(d['content']) for d in conversation)
            except Exception as e:
                break
        
        if event_2 == 'livechat':
            if len(chat) > 0:
                response = AIeri.models.generate_content(
                    model="gemini-3.7-flash",
                    contents=[chat_now,chat, str(prompt),chat_prev]
                )
                message = response.text
                print(f"AI Response: {message}")
                
                with open("conversation.txt", "w", encoding="utf-8") as f:
                    for conv in conversation:
                        f.write(f"{conv['role']}: {conv['content']}\n")
                chat_prev.append(message)
                translate_text(message)
        else:
            if len(chat_now) > 0:
                response = AIeri.models.generate_content(
                    model="gemini-3.7-flash",
                    contents=[chat_now, str(prompt),chat_prev]
                )
                message = response.text
                print(f"AI Response: {message}")
                
                with open("conversation.txt", "w", encoding="utf-8") as f:
                    for conv in conversation:
                        f.write(f"{conv['role']}: {conv['content']}\n")
                chat_prev.append(message)
                translate_text(message)
    except Exception as e:
        print(f"Error in openai_answer: {e}")
    finally:
        ai_processing = False
        is_Speaking = False
        
        
        print("AI processing completed")

def chatupdate():
    global chat, live , blacklist , is_Speaking
    
    while live.is_alive():
        for c in live.get().sync_items():
            if is_Speaking == True:
                continue
            else:
                if c.author.name in blacklist:
                    continue
                chat = str(c.author.name + ' said ' + c.message)

def yt_livechat():
    global live_txt,live,t1,chat_prev,chat,is_Speaking
    try:    
        if len(live_txt[-1]) > 0:
            if live == '':
                live = pytchat.create(video_id=t1)
                threading.Thread(target=chatupdate, daemon=True).start()
            if is_Speaking == True:
                chat_prev.append(chat) 
    except KeyboardInterrupt:
        print("Stopping pytchat...")       

def twitch_livechat():
    global chat
    sock = socket.socket()

    sock.connect((server, port))
    sock.send(f"PASS {token}\n".encode('utf-8'))
    sock.send(f"NICK {nickname}\n".encode('utf-8'))
    sock.send(f"JOIN {channel}\n".encode('utf-8'))

    regex = r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)"

    while True:
        try:
            resp = sock.recv(2048).decode('utf-8')

            if resp.startswith('PING'):
                sock.send("PONG\n".encode('utf-8'))
            elif not user in resp:
                resp = demojize(resp)
                match = re.match(regex, resp)
                username = match.group(1)
                message = match.group(2)

                if username in blacklist:
                    continue
                
                chat = username + ' said ' + message
                print(chat)

        except Exception as e:
            print("Error receiving chat: {0}".format(e))

# translating is optional
def translate_text(text_p):
    global is_Speaking , active_eri , mp3time , time_ ,output_file
    
    # ใช้ lock เพื่อป้องกันการใช้ไฟล์เสียงพร้อมกัน
    
        # สร้างชื่อไฟล์ที่ไม่ซ้ำกัน
    timestamp = str(int(time_module.time() * 1000))
    output_file = f"output_{timestamp}.mp3"
    
    
        
    
    
    # สร้างไฟล์เสียงใหม่
    eri = gTTS(text=text_p, lang='th', slow=False)
    eri.save(output_file)
    
    # เล่นไฟล์เสียงด้วยชื่อใหม่
    pygame.mixer.music.load(output_file)
    mp3time = mp3.MP3(output_file).info.length
    pygame.mixer.music.play()
    
    active_eri = 2
    os.remove(output_file)    
            
            
            
        
    
    # Clear the text files after the assistant has finished speaking
    with open ("output.txt", "w") as f:
        f.truncate(0)
    with open ("chat.txt", "w") as f:
        f.truncate(0)

def preparation():
    global conversation, chat_now, chat, chat_prev
    while True:
        chat_now = chat
        if is_Speaking == False and chat_now != chat_prev:
            conversation.append({'role': 'user', 'content': chat_now})
            chat_prev = chat_now
            openai_answer()
        time.sleep(1)

    
    
    
def event_dis():
    global event_1 ,active_eri, time_,  live_txt, event_2, re_event,chat,is_Speaking,i,t1,chat_now, is_recording, was_e_pressed,ai_processing
    
    while True:
        keys = pygame.key.get_pressed() 
        if event_1 == 'talking':
            
            # Push-to-Talk: กด E ค้างเพื่อบันทึก
            if keys[pygame.K_e]:
                if not is_recording:
                    # เริ่มบันทึกใหม่
                    is_recording = True
                    frames.clear()  # ล้างข้อมูลเก่า
                    time_ = 0
                    print("Started recording...")
                
                # บันทึกเสียงต่อเนื่อง
                if stream and is_recording:
                    try:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        frames.append(data)
                        print("Recording...")
                    except Exception as e:
                        print(f"Error reading audio: {e}")
                
                was_e_pressed = True
                
            else:
                # ปล่อยปุ่ม E = หยุดบันทึกและประมวลผล
                if was_e_pressed and is_recording and not ai_processing:
                    is_recording = False
                    was_e_pressed = False
                    
                    # บันทึกไฟล์เสียง
                    if len(frames) > 0:
                        try:
                            print("Stopped recording, processing...")
                            wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(p.get_sample_size(FORMAT))
                            wf.setframerate(RATE)
                            wf.writeframes(b''.join(frames))
                            wf.close()
                            
                            # ประมวลผลข้อความ
                            threading.Thread(target=transcribe_audio, args=(WAVE_OUTPUT_FILENAME,)).start()
                        except Exception as e:
                            print(f"Error saving audio: {e}")
                    else:
                        print("No audio data recorded")
                elif was_e_pressed and is_recording and ai_processing:
                    ai_processing = False
                        
            if time_ >= 60*10/clock.get_fps(): 
                if is_Speaking == False:
                    if keys[pygame.K_e]:    
                        continue
                    else:
                        chat_now=f"{owner_name}:: [เงียบ]"
                        is_Speaking = True
                        threading.Thread(target=openai_answer).start()
        
            
                 
        elif event_1 == 'livechat':
            if event_2 == 'livechat':
                if keys[pygame.K_e]:
                    if not is_recording:
                        is_recording = True
                        frames.clear()
                        time_ = 0
                    if stream and is_recording:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        frames.append(data)

                    
                    was_e_pressed = True
                else:
                    if was_e_pressed and not ai_processing:
                        is_recording = False
                        was_e_pressed = False
                        if len(frames) > 0:
                            try:
                                print("Stopped recording, processing...")
                                wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
                                wf.setnchannels(CHANNELS)
                                wf.setsampwidth(p.get_sample_size(FORMAT))
                                wf.setframerate(RATE)
                                wf.writeframes(b''.join(frames))
                                wf.close()
                                
                                # ประมวลผลข้อความ
                                threading.Thread(target=transcribe_audio, args=(WAVE_OUTPUT_FILENAME,)).start()
                            except Exception as e:
                                print(f"Error saving audio: {e}")

                if t1 == '':
                    t1 = "https://www.youtube.com/watch?v="+live_txt[-1]
                    
                if time_ >= 60*10/clock.get_fps():
                    if is_Speaking == False:
                        if keys[pygame.K_e]:    
                            continue
                        else:
                            
                            is_Speaking = True
                            threading.Thread(target=openai_answer).start()
        if event_1 == "bot_discord":
            if event_2 == "bot_active":
                client.run(token=dis_token)
                event_2 = ''

                    

def timer(framerate):
    global time_
    
    clock.tick(framerate)
    if clock.get_fps() == 0:
        pass
    else:    
        time_ += 1 / clock.get_fps() 

if __name__ == "__main__":
    
    # เริ่มต้นระบบเสียง
    get_audio_devices()
    
    t = threading.Thread(target=event_dis ,daemon=True) 
    t.start()
     
    while True:
        keys = pygame.key.get_pressed() 

        screen.fill((155,155,255))

        # Process player inputs.
        for event  in pygame.event.get():
            
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN:
                if eri_dist.collidepoint(event.pos):
                    active_eri = 1
                    time_ = 0

                if event_1 == 'start':
                    if r_button_voicechat.collidepoint(event.pos):
                        txt.append("1")
                        event_1 = 'talking'
                        time_ = 0
                    if r_button_livechat.collidepoint(event.pos):
                        txt.append("2")
                        event_1 = 'livechat'
                        time_ = 0
                    if r_button_audio_settings.collidepoint(event.pos):
                        txt.append("3")
                        event_1 = 'audio_settings'
                        time_ = 0
                        # รับรายการอุปกรณ์เสียง
                        get_audio_devices()
                    if r_button_discord.collidepoint(event.pos):
                        txt.append("4")
                        event_1 = 'bot_discord'
                   
                if event_1 == 'livechat':
                    if r_button_back.collidepoint(event.pos):
                        txt.append("0")
                        event_1 = 'start'
                        time_=0
                if event_1 == 'talking':
                    if r_button_back.collidepoint(event.pos):
                        txt.append("0")
                        event_1 = 'start'
                        time_=0
                    

                if event_1 == 'audio_settings':
                    if r_button_back.collidepoint(event.pos):
                        txt.append("0")
                        event_1 = 'start'
                        time_=0
                    if r_button_input_device.collidepoint(event.pos):
                        # สลับอุปกรณ์ input
                        current_input_device_index = (current_input_device_index + 1) % len(audio_devices["input"])
                    if r_button_output_device.collidepoint(event.pos):
                        # สลับอุปกรณ์ output  
                        current_output_device_index = (current_output_device_index + 1) % len(audio_devices["output"])
                    if r_button_refresh_audio.collidepoint(event.pos):
                        # รีเฟรชรายการอุปกรณ์
                        get_audio_devices()
                    if r_button_apply_audio.collidepoint(event.pos):
                        # ใช้การตั้งค่าใหม่
                        if len(audio_devices["input"]) > 0:
                            selected_input_device = audio_devices["input"][current_input_device_index]["id"]
                            # สร้าง audio stream ใหม่ด้วยอุปกรณ์ที่เลือก
                            success = create_audio_stream(selected_input_device)
                            if success:
                                print(f"Applied input device: {audio_devices['input'][current_input_device_index]['name']}")
                            else:
                                print("Failed to apply input device")
                        if len(audio_devices["output"]) > 0:
                            selected_output_device = audio_devices["output"][current_output_device_index]["id"]
                            print(f"Applied output device: {audio_devices['output'][current_output_device_index]['name']}")
                if event_1 == 'bot_discord':
                    event_2 = 'bot_active'
                    if r_button_back.collidepoint(event.pos):
                        txt.append("0")
                        event_1 = 'start'
                        time_=0

            if len(live_t) >= 20:
                if len(live_t) >= len(live_ti[:-len(live_t)] ):
                    live_ti += live_t
                    live_tr += 82
                    
            if event.type == pygame.KEYDOWN:
                
                if event.key == pygame.K_BACKSPACE:
                    if event_1 == 'livechat':
                        live_t = live_t[:-1]
                    if event_1 == 'talking':
                        input_t = input_t[:-1]
                    if event_1 == 'start':
                        input_t = input_t[:-1]
                    
                else:
                    if event_1 == 'livechat':
                        if event_2 == 'livechat':
                            live_t = live_t  
                        else:    
                            live_t +=  str(event.unicode)
                            
                    if event_1 == 'talking':
                        input_t +=  str(event.unicode)
                    if event_1 == 'start':
                        input_t +=  str(event.unicode)
                    if event.key == pygame.K_KP_ENTER:

                        if event_1 == 'livechat':
                            if len(live_t[len(live_t):-1]) == len(live_t) - 1:
                                continue
                            else:
                                live_txt.append(live_t)
                            live_t = ''
                        if event_1 == 'talking':
                            if len(input_t[len(input_t):-1]) == len(input_t) - 1:
                                continue
                            else:
                                txt.append(input_t[:-1])
                            input_t = ''
                        if event_1 == 'start':
                            if len(input_t[len(input_t):-1]) == len(input_t) - 1:
                                continue
                            else:
                                txt.append(input_t[:-1])
                            input_t = ''

        if txt[-1] == "0": 
            pygame.display.set_caption("Fuyuki Eri AI Chattering - Main Menu")
            event_1 = 'start'
            
            # พื้นหลัง gradient
            for y in range(int(v.y)):
                ratio = y / v.y
                r = int(30 * (1-ratio) + 60 * ratio)
                g = int(30 * (1-ratio) + 80 * ratio)  
                b = int(60 * (1-ratio) + 120 * ratio)
                pygame.draw.line(screen, (r, g, b), (0, y), (v.x, y))
            
            # หัวข้อหลัก
            title_text = title_font.render("Fuyuki Eri AI VTuber", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(v.x//2, 100))
            screen.blit(title_text, title_rect)
            
            # เส้นใต้หัวข้อ
            pygame.draw.line(screen, (255, 255, 255), 
                           (title_rect.left, title_rect.bottom + 10), 
                           (title_rect.right, title_rect.bottom + 10), 3)
            
            # วาดปุ่มต่างๆ ด้วยสไตล์ใหม่
            draw_modern_button(screen, r_button_voicechat, voice_chat_color, "Voice Chat", button_font)
            draw_modern_button(screen, r_button_livechat, live_chat_color, "Live Chat", button_font)  
            draw_modern_button(screen, r_button_audio_settings, audio_settings_color, "Audio Settings", button_font)
            draw_modern_button(screen, r_button_discord,discord_color,"discord Mode",button_font)
            
            # ตัวละครด้านขวา
            eri_dist.center = (v.x - 200, v.y//2)
            screen.blit(fuyuki_defualt_[0], eri_dist)

            if keys[pygame.K_ESCAPE]:
                pygame.quit()
                raise SystemExit

        if txt[-1] == "1":
            for y in range(int(v.y)):
                ratio = y / v.y
                r = int(40 * (1-ratio) + 70 * ratio)
                g = int(50 * (1-ratio) + 90 * ratio)  
                b = int(80 * (1-ratio) + 150 * ratio)
                pygame.draw.line(screen, (r, g, b), (0, y), (v.x, y))
            
            eri_dist.center = (200, v.y//2)

            threading.Thread(target=CharMove).start()
            if is_Speaking == True:
                time_ = 0 

            
            
            event_1 = 'talking'
            pygame.display.set_caption("Fuyuki Eri AI Chattering - Voice Chat")
            
            # พื้นหลัง gradient
            
            
            # หัวข้อ
            title_text = title_font.render("Voice Chat Mode", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(v.x//2, 60))
            screen.blit(title_text, title_rect)
            
            # คำแนะนำการใช้งาน
            instruction1 = button_font.render("Hold E to Record", True, (255, 255, 255))
            instruction2 = small_font.render("Release E to Stop & Process", True, (200, 200, 200))
            
            inst1_rect = instruction1.get_rect(center=(v.x//2, 120))
            inst2_rect = instruction2.get_rect(center=(v.x//2, 150))
            
            screen.blit(instruction1, inst1_rect)
            screen.blit(instruction2, inst2_rect)
            
            # ตัวละครด้านซ้าย
            
                    
            # แสดงสถานะการบันทึกเสียง
            if is_recording:
                # วาดวงกลมสีแดงกะพริบ
                if int(time_ * 3) % 2:  # กะพริบเร็วขึ้น
                    pygame.draw.circle(screen, (255, 50, 50), (v.x//2, v.y//2), 100)
                    pygame.draw.circle(screen, (255, 100, 100), (v.x//2, v.y//2), 80)
                    
                    # ข้อความบันทึก
                    rec_text = title_font.render("RECORDING", True, (255, 255, 255))
                    rec_rect = rec_text.get_rect(center=(v.x//2, v.y//2))
                    screen.blit(rec_text, rec_rect)
            
            # ปุ่ม Back สไตล์ใหม่
                
            draw_modern_button(screen, r_button_back, back_color, "back" , small_font)     
            if keys[pygame.K_F1]:
                txt.append("0")
                event_1 = 'start'
            
        elif txt[-1] == "2":
            
            if event_2 == 'livechat':
                pygame.display.set_caption("Fuyuki Eri AI Chattering - Live Chat")
                
                # พื้นหลัง gradient สีเขียว
                for y in range(int(v.y)):
                    ratio = y / v.y
                    r = int(20 * (1-ratio) + 50 * ratio)
                    g = int(80 * (1-ratio) + 120 * ratio)  
                    b = int(40 * (1-ratio) + 80 * ratio)
                    pygame.draw.line(screen, (r, g, b), (0, y), (v.x, y))
                
                # หัวข้อ
                title_text = title_font.render("Live Chat Active", True, (255, 255, 255))
                title_rect = title_text.get_rect(center=(v.x//2, 60))
                screen.blit(title_text, title_rect)
                
                # เส้นใต้หัวข้อ
                pygame.draw.line(screen, (255, 255, 255), 
                               (title_rect.left, title_rect.bottom + 10), 
                               (title_rect.right, title_rect.bottom + 10), 2)
                if is_recording:
                # วาดวงกลมสีแดงกะพริบ
                    if int(time_ * 3) % 2:  # กะพริบเร็วขึ้น
                        pygame.draw.circle(screen, (255, 50, 50), (v.x//2, v.y//2), 100)
                        pygame.draw.circle(screen, (255, 100, 100), (v.x//2, v.y//2), 80)
                        
                        # ข้อความบันทึก
                        rec_text = title_font.render("RECORDING", True, (255, 255, 255))
                        rec_rect = rec_text.get_rect(center=(v.x//2, v.y//2))
                        screen.blit(rec_text, rec_rect)
                if is_Speaking == True:
                    processing_text = font.render("Processing chat...", True, (255,255,0))
                    processing_rect = processing_text.get_rect()
                    processing_rect.center = (v.x/2, 150)
                    screen.blit(processing_text, processing_rect)
                    time_ = 0
                 
                yt_livechat()  
                
                # แสดงข้อความ chat ล่าสุด
                if 'chat' in globals():
                    chat_surface = font.render(chat, True, (255, 255, 255))
                    chat_rect = chat_surface.get_rect(center=(v.x//2, 200))
                    screen.blit(chat_surface, chat_rect)
                
                # ตัวละครด้านซ้าย
                eri_dist.center = (200, v.y//2)
                threading.Thread(target=CharMove).start() 
                    
                # ปุ่ม Back สไตล์ใหม่
                draw_modern_button(screen, r_button_back, back_color, "Back", small_font)
                
                if keys[pygame.K_F1]:
                    txt.append("0")
                    live_txt.append("")
                    event_1 = 'start'
                
            else:
                pygame.display.set_caption("Fuyuki Eri AI Chattering - Live Chat Setup")
                
                # พื้นหลัง gradient สีส้ม
                for y in range(int(v.y)):
                    ratio = y / v.y
                    r = int(80 * (1-ratio) + 120 * ratio)
                    g = int(50 * (1-ratio) + 90 * ratio)  
                    b = int(20 * (1-ratio) + 60 * ratio)
                    pygame.draw.line(screen, (r, g, b), (0, y), (v.x, y))
                
                # หัวข้อ
                title_text = title_font.render("Live Chat Setup", True, (255, 255, 255))
                title_rect = title_text.get_rect(center=(v.x//2, 80))
                screen.blit(title_text, title_rect)
                
                # เส้นใต้หัวข้อ
                pygame.draw.line(screen, (255, 255, 255), 
                               (title_rect.left, title_rect.bottom + 10), 
                               (title_rect.right, title_rect.bottom + 10), 2)
                
                # คำแนะนำ
                instruction_text = button_font.render("Enter YouTube Video ID:", True, (255, 255, 255))
                instruction_rect = instruction_text.get_rect(center=(v.x//2, 150))
                screen.blit(instruction_text, instruction_rect)
                
                # กรอบข้อความ input สวยๆ
                input_rect = pygame.Rect(v.x//2 - 200, 200, 400, 50)
                pygame.draw.rect(screen, (255, 255, 255), input_rect)
                pygame.draw.rect(screen, (100, 100, 100), input_rect, 3)
                
                # ข้อความที่พิมพ์
                if 'live_t' in globals():
                    text_live = font.render(live_t, True, (0, 0, 0))
                    text_rect = text_live.get_rect()
                    text_rect.centery = input_rect.centery
                    text_rect.left = input_rect.left + 10
                    screen.blit(text_live, text_rect)
                
                # คำแนะนำเพิ่มเติม
                help_text = small_font.render("Press F2 to start monitoring live chat", True, (255, 255, 255))
                help_rect = help_text.get_rect(center=(v.x//2, 280))
                screen.blit(help_text, help_rect)
                
                # ตัวละครด้านขวา
                eri_dist.center = (v.x - 200, v.y//2)
                threading.Thread(target=CharMove).start()
                
                # ปุ่ม Back สไตล์ใหม่
                draw_modern_button(screen, r_button_back, back_color, "Back", small_font)
                
                event_1 = 'livechat'
                    
                if keys[pygame.K_F2]:
                    event_2 = 'livechat'
                    time_ = 0

                if keys[pygame.K_F1]:
                    txt.append("0")
                    live_txt.append("")
                    event_1 = 'start'

        elif txt[-1] == "3":
            # หน้าจอ Audio Settings
            event_1 = 'audio_settings'
            pygame.display.set_caption("Fuyuki Eri AI Chattering - Audio Settings")
            
            # พื้นหลัง gradient สีม่วง
            for y in range(int(v.y)):
                ratio = y / v.y
                r = int(60 * (1-ratio) + 100 * ratio)
                g = int(40 * (1-ratio) + 70 * ratio)  
                b = int(120 * (1-ratio) + 180 * ratio)
                pygame.draw.line(screen, (r, g, b), (0, y), (v.x, y))
            
            # หัวข้อหลัก
            title_text = title_font.render("Audio Device Settings", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(v.x//2, 80))
            screen.blit(title_text, title_rect)
            
            # เส้นใต้หัวข้อ
            pygame.draw.line(screen, (255, 255, 255), 
                           (title_rect.left, title_rect.bottom + 10), 
                           (title_rect.right, title_rect.bottom + 10), 2)
            
            # แสดงอุปกรณ์ Input
            input_label_rect = text_input_device_label.get_rect()
            input_label_rect.center = (v.x//2, 170)
            screen.blit(text_input_device_label, input_label_rect)
            
            input_device_name = "No device selected"
            if len(audio_devices["input"]) > 0:
                device_info = audio_devices["input"][current_input_device_index]
                input_device_name = f"{device_info['name']}"
                if len(input_device_name) > 50:
                    input_device_name = input_device_name[:50] + "..."
            
            # วาดปุ่มอุปกรณ์ Input
            draw_modern_button(screen, r_button_input_device, input_device_color, 
                             input_device_name, small_font)
            
            # แสดงอุปกรณ์ Output  
            output_label_rect = text_output_device_label.get_rect()
            output_label_rect.center = (v.x//2, 270)
            screen.blit(text_output_device_label, output_label_rect)
            
            output_device_name = "No device selected"
            if len(audio_devices["output"]) > 0:
                device_info = audio_devices["output"][current_output_device_index]
                output_device_name = f"{device_info['name']}"
                if len(output_device_name) > 50:
                    output_device_name = output_device_name[:50] + "..."
            
            # วาดปุ่มอุปกรณ์ Output
            draw_modern_button(screen, r_button_output_device, output_device_color, 
                             output_device_name, small_font)
            
            # ปุ่ม Apply และ Refresh
            draw_modern_button(screen, r_button_apply_audio, apply_color, "Apply", button_font)
            draw_modern_button(screen, r_button_refresh_audio, refresh_color, "Refresh", button_font)
            
            # ปุ่ม Back
            draw_modern_button(screen, r_button_back, back_color, "Back", small_font)
            
            # แสดงตัวละคร
            threading.Thread(target=CharMove).start()
            eri_dist.center = (v.x - 150, v.y//2)
            
            # คำแนะนำ
            help_text = small_font.render("Click device buttons to cycle through available options", 
                                        True, (255, 255, 255))
            help_rect = help_text.get_rect(center=(v.x//2, v.y - 80))
            screen.blit(help_text, help_rect)
            
            if keys[pygame.K_F1]:
                txt.append("0")
                event_1 = 'start'
        if txt[-1] == "4":
            for y in range(int(v.y)):
                ratio = y / v.y
                r = int(60 * (1-ratio) + 100 * ratio)
                g = int(40 * (1-ratio) + 70 * ratio)  
                b = int(120 * (1-ratio) + 180 * ratio)
                pygame.draw.line(screen, (r, g, b), (0, y), (v.x, y))
            title_text = title_font.render("::Discord Mode::", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(v.x//2, 80))
            screen.blit(title_text, title_rect)
            event_1 = 'bot_discord'
           
            draw_modern_button(screen,r_button_back,back_color,"back",button_font)
            
            CharMove()
            if keys[pygame.K_F1]:
                txt.append("0")
                
                
        fps = font.render(f"FPS:{int(clock.get_fps())}",True,(255,255,255))
        fps_r = fps.get_rect()
        fps_r.center = (1900/1.35,40/1.35)
        screen.blit(fps,fps_r)

        pygame.display.flip()
        
      
        timer(sys.maxsize)
