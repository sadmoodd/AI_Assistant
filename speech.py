import speech_recognition as sr
from gtts import gTTS
import re
import requests
import threading
import pygame
import time

from pydub import AudioSegment

def speed_change(sound, speed=1.5):
    # speed >1 быстрее, <1 медленнее
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
         "frame_rate": int(sound.frame_rate * speed)
      })
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)


API_URL = "https://router.huggingface.co/v1/chat/completions"

#TODO delete for production
HF_API_TOKEN = "YOUR_HF_KEY"


headers = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json"
}

def clean_text(text):
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\*', '', text)
    text = re.sub(r'[`_>#+\-]', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def query_huggingface_chat(user_text):
    payload = {
        "messages": [ {"role": "user", "content": user_text} ],
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita"
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    else:
        print("Ошибка Hugging Face API:", response.status_code, response.text)
        return None

recognizer = sr.Recognizer()

# Глобальный флаг для остановки воспроизведения
stop_flag = False

def play_audio(file_path):
    global stop_flag
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()

    # Ждем либо окончания воспроизведения, либо пока stop_flag не станет True
    while pygame.mixer.music.get_busy():
        if stop_flag:
            pygame.mixer.music.stop()
            break
        time.sleep(0.1)

def listen_for_stop():
    global stop_flag
    r = sr.Recognizer()
    with sr.Microphone() as source:
        while pygame.mixer.music.get_busy():
            try:
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=5)
                keyword = recognizer.recognize_google(audio, language='ru-RU').lower()
                print(f"Сказано: {keyword}")
                text = r.recognize_google(audio, language='ru-RU').lower()
                print(f"Команда во время воспроизведения: {keyword}")
                if 'стоп' in text:
                    stop_flag = True
                    break
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Ошибка распознавания: {e}")

print("Голосовой ассистент запущен. Скажите 'привет' чтобы начать.")

def main():
    while True:
        try:
            with sr.Microphone() as source:
                print("Ожидание ключевого слова 'привет, братишка'...")
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=100)
                keyword = recognizer.recognize_google(audio, language='ru-RU').lower()
                print(f"Сказано: {keyword}")

                if "привет" in keyword:
                    recognizer.adjust_for_ambient_noise(source)
                    print("Ключевое слово услышано! Говорите ваш запрос.")
                    audio = recognizer.listen(source, timeout=15, phrase_time_limit=100)
                    input_text = recognizer.recognize_google(audio, language='ru-RU')
                    print(f"Вы сказали: {input_text}")
                    print("Запрос получен, думаю...")

                    hf_response = query_huggingface_chat(input_text)
                    if hf_response:
                        hf_response = clean_text(hf_response)
                        print("Ответ Hugging Face:", hf_response)
                        tts = gTTS(hf_response, lang='ru', slow=False)
                        tts.save("voice.mp3")
                        
                        sound = AudioSegment.from_file("voice.mp3")
                        faster_sound = speed_change(sound, speed=1.35)  # ускорить в 1.5 раза
                        faster_sound.export("voice.mp3", format="mp3")
                        
                        stop_flag = False
                        # Запускаем воспроизведение и слушаем команду стоп параллельно
                        thread_play = threading.Thread(target=play_audio, args=("voice.mp3",))
                        thread_listen = threading.Thread(target=listen_for_stop)

                        thread_play.start()
                        thread_listen.start()

                        thread_play.join()
                        thread_listen.join()

                        print("Готов к новому запросу.")
                    else:
                        print("Не удалось получить ответ от Hugging Face")
                else:
                    print("Ключевое слово не распознано, ожидаю дальше...")
                    
                if 'стоп' in keyword:
                    raise KeyboardInterrupt

        except sr.UnknownValueError:
            print("Не удалось распознать речь, повторите.")
        except sr.RequestError as e:
            print(f"Ошибка подключения к сервису распознавания речи: {e}")
        except Exception as e:
            print(f"Ошибка: {e}")
            
if __name__ == "__main__":
    main()
