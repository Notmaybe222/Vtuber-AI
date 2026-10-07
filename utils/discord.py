import os
import re
import traceback
import wave
import time
import asyncio
import threading
import array
import discord
import aiohttp
from bs4 import BeautifulSoup
from gtts import gTTS

# โมดูล Discord Voice Receive Extension


# โมดูลภายนอกของโปรเจกต์คุณ
from utils.promptMaker import getPrompt, saveIdentity
from object.obj_db import AIeri, chat_prev, chat_now, types, AIeri_prop, eri_speak

URL_PATTERN = re.compile(r'https?://[^\s]+')
connections = {}
 
 
class DiscordBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # เก็บ guild ที่กำลังบันทึกเสียงอยู่ เพื่อกันการสั่ง eristart ซ้ำ
        # และให้ eristop รู้ว่ามีการบันทึกค้างอยู่ไหม
        self.recording_guilds: set[int] = set()
 
    async def speak(self, vc, text: str):
        """แปลงข้อความ เป็น เสียง แล้วเล่นใน Voice Channel"""
        if not vc or not vc.is_connected():
            return
 
        filename = "response.mp3"
        try:
            tts = gTTS(text=text, lang='th')
            tts.save(filename)
 
            if vc.is_playing():
                vc.stop()
 
            def after_playing(error):
                if error:
                    print(f"⚠️ Playback error: {error}")
                else:
                    print("Finished speaking.")
                if os.path.exists(filename):
                    os.remove(filename)
 
            vc.play(discord.FFmpegPCMAudio(filename), after=after_playing)
        except Exception as e:
            print(f"Error in speak: {e}")
 
    async def fetch_web_content(self, url: str) -> str:
        """ดึงข้อความจากเว็บ URL"""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return f"[ไม่สามารถเข้าถึงหน้าเว็บได้: Error {response.status}]"
 
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
 
                    for script in soup(["script", "style"]):
                        script.decompose()
 
                    text = soup.get_text(separator=' ')
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase for line in lines for phrase in line.split("  "))
                    cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
 
                    return cleaned_text[:3000]
        except Exception as e:
            return f"[เกิดข้อผิดพลาดในการอ่านเว็บ: {e}]"
 
    async def answer_audio(self, channel, author_id, author_name):
        """แปลง STT -> ส่ง Gemini -> พูดตอบกลับ (คาดว่า {author_id}.wav ถูกเขียนไว้แล้ว)"""
        global chat_prev, chat_now
        file_path = f"{author_id}.wav"
 
        if not os.path.exists(file_path):
            await channel.send("ไม่พบเสียงที่บันทึกไว้เลยค่ะ ลองพูดดังขึ้นอีกนิดนะคะ")
            return
 
        try:
            with open(file_path, "rb") as audio_file:
                transcript = AIeri_prop.speech_to_text.convert(
                    file=audio_file,
                    model_id="scribe_v1",
                    language_code="th"
                )
 
            chat_ = transcript.text
            if chat_ and len(chat_.strip()) > 0:
                chat_now = f"{author_name} said {chat_}"
                chat_prev.append(chat_now)
                print(f"Transcribed: {chat_}")
 
                bot_response = AIeri.models.generate_content(
                    model="gemini-3.7-flash",
                    contents=[chat_now, getPrompt()]
                )
 
                vc = channel.guild.voice_client
                if vc:
                    await self.speak(vc, text=bot_response.text)
 
                chat_prev.append(f"fuyuki eri said -> [{bot_response.text}]")
                saveIdentity("characterConfig/Pina/chatdata.txt", str(chat_prev))
            else:
                await channel.send("ไม่ได้ยินเสียงพูดที่ชัดเจนค่ะ ลองพูดใหม่อีกครั้งนะคะ")
        except Exception as e:
            print(f"Error in answer_audio: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
 
    async def recording_finished(self, sink: discord.sinks.Sink, channel, author_id: int, author_name: str):
        """
        Callback ที่ py-cord เรียกอัตโนมัติหลัง vc.stop_recording()
        sink.audio_data คือ dict: user_id -> discord.sinks.AudioData (มี .file เป็น BytesIO ของไฟล์ .wav)
        """
        self.recording_guilds.discard(channel.guild.id)
 
        audio_data = sink.audio_data.get(author_id)
        
 
        wav_path = f"{author_id}.wav"
        with open(wav_path, "wb") as f:
            f.write(audio_data.file.read())
 
        await channel.send("หยุดบันทึกแล้ว กำลังประมวลผลเสียง... ⏳")
        await self.answer_audio(channel, author_id, author_name)
 
    async def start_listen(self, message):
        """eristart: เชื่อมต่อห้องเสียง (ถ้ายัง) แล้วเริ่มบันทึกเสียงต่อเนื่อง
        ใช้ VoiceClient.start_recording() ของ py-cord ตรงๆ (ไม่ต้องเขียน sink เอง)"""
        voice = message.author.voice
 
        if not voice:
            await message.channel.send("You aren't in a voice channel!")
            return
 
        # ใช้ voice client เดิมถ้ามีอยู่แล้ว ไม่งั้นค่อยต่อใหม่
        vc = message.guild.voice_client or await voice.channel.connect()
        connections.update({message.guild.id: vc})
 
        sink = discord.sinks.WaveSink()  # ต้องสร้าง instance (มี ()) ไม่ใช่ pass class เฉยๆ
 
        vc.start_recording(
            sink,
            self.recording_finished,  # ส่ง callback function ไปเฉยๆ ห้าม await/เรียกมันตรงนี้
            message.channel,
            message.author.id,
            message.author.name
        )
        self.recording_guilds.add(message.guild.id)
 
        await message.channel.send("เริ่มบันทึกเสียงแล้วค่ะ พูดได้เลย พิมพ์ eristop เมื่อพูดจบนะคะ 🎙️")
 
    async def stop_listen(self, message):
        """eristop: หยุดบันทึก — ผลลัพธ์จะไปโผล่ที่ recording_finished() แบบ async ต่อเอง"""
        vc = message.guild.voice_client
 
        if message.guild.id not in self.recording_guilds or not vc or not vc.is_recording:
            await message.channel.send("ยังไม่ได้เริ่มบันทึกเสียงค่ะ พิมพ์ eristart ก่อนนะคะ")
            return
 
        vc.stop_recording()  # เรียก recording_finished callback ให้อัตโนมัติ
 
    async def on_ready(self):
        print(f"Logged in successfully as {self.user}")
        print(f"discord.opus loaded: {discord.opus.is_loaded()}")
 
    async def on_message(self, message):
        global chat_prev, chat_now, at_part
        if message.author == self.user:
            return
 
        command = None
        user_message = message.content.strip()
 
        words = user_message.split()
        if not words:
            return
 
        first_word = words[0].lower()
 
        if first_word in ['erijoin', 'eridisconnect', 'eristop', 'eristart', 'เอริ', 'eri']:
            command = first_word
            user_message = message.content[len(command):].strip()
 
        at_part = ""
        if len(message.attachments) > 0:
            attachment = message.attachments[0]
            at = await attachment.read()
            at_part = types.Part.from_bytes(
                data=at, mime_type=attachment.content_type
            )
 
        urls = URL_PATTERN.findall(user_message)
        web_text = await self.fetch_web_content(urls[0]) if urls else ""
 
        if command == 'erijoin':
            if message.author.voice:
                if not message.guild.voice_client:
                    await message.author.voice.channel.connect()
                    await message.channel.send("เชื่อมต่อเข้าห้องเสียงเรียบร้อยแล้วค่ะ!")
                else:
                    await message.channel.send("บอทอยู่ในห้องเสียงอยู่แล้วค่ะ!")
            else:
                await message.channel.send("คุณไม่ได้อยู่ในห้องเสียง!")
            return
 
        if command == 'eridisconnect':
            if message.guild.voice_client:
                self.recording_guilds.discard(message.guild.id)
                await message.guild.voice_client.disconnect()
                await message.channel.send("ตัดการเชื่อมต่อจากห้องเสียงเรียบร้อยค่ะ")
            return
 
        if command == 'eristop':
            await self.stop_listen(message)
            return
 
        if command == 'eristart':
            await self.start_listen(message)
            return
 
        if command in ['เอริ', 'eri']:
            prompt = getPrompt()
            chat_prev.append(f"{message.author} said: {message.content}")
 
            bot_response = AIeri.models.generate_content(
                model="gemini-3.7-flash",
                contents=[user_message, at_part, f"\n\n[เนื้อหาจากลิงก์ที่ผู้ใช้แนบมา]:\n{web_text}", prompt]
            )
 
            chat_prev.append(f"fuyuki eri said -> [{bot_response.text}]")
            saveIdentity("characterConfig/Pina/chatdata.txt", str(chat_prev))
            await message.channel.send(bot_response.text)

intents = discord.Intents.default()
intents.message_content = True
client = DiscordBot(intents=intents)



# แนะนำให้ดึง Token จาก Environment Variables เพื่อความปลอดภัย
# client.run(os.getenv("DISCORD_TOKEN"))
dis_token = ""
