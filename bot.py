import discord
import random
import os
import json
import asyncio  # Новая библиотека для создания пауз (таймеров)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# НОВОЕ: ID канала, куда бот будет писать сам. Замени нули на свой ID!
TARGET_CHANNEL_ID = 1198649196446761002

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

MEMORY_FILE = 'memory.json'
IMAGES_FOLDER = 'images'
MAX_IMAGES = 100

os.makedirs(IMAGES_FOLDER, exist_ok=True)

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("⚠️ Файл памяти был пуст или поврежден. Начинаем с чистой памяти.")
            return {"words": [], "images": []}
    else:
        return {"words": [], "images": []}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

bot_memory = load_memory()
words_database = bot_memory["words"]
images_database = bot_memory["images"]

# Переменная, чтобы таймер не запустился дважды
background_task_started = False

@client.event
async def on_ready():
    global background_task_started
    print(f'Бот {client.user} успешно запущен!')
    print(f'В памяти: слов - {len(words_database)}, картинок - {len(images_database)}.')
    
    # Запускаем наш таймер при старте бота
    if not background_task_started:
        client.loop.create_task(random_message_loop())
        background_task_started = True

# --- НОВАЯ ФУНКЦИЯ: БЕСКОНЕЧНЫЙ ТАЙМЕР ---
async def random_message_loop():
    await client.wait_until_ready()
    # Находим канал по ID, который мы указали в начале файла
    channel = client.get_channel(TARGET_CHANNEL_ID)
    
    if channel is None:
        print("❌ ОШИБКА: Не могу найти канал! Проверь TARGET_CHANNEL_ID.")
        return

    while not client.is_closed():
        # Выбираем случайное время от 1 часа (3600 сек) до 5 часов (18000 сек)
        # Для тестов можешь поменять на (10, 30) - от 10 до 30 секунд
        delay_seconds = random.randint(3600, 18000)
        
        # Переводим секунды в часы для удобного вывода в терминал
        hours_to_wait = delay_seconds / 3600
        print(f"[Таймер] Бот уснул. Следующее сообщение через {hours_to_wait:.2f} часов.")
        
        # Бот "спит" указанное время
        await asyncio.sleep(delay_seconds)
        
        # Бот проснулся - отправляем сообщение!
        print("[Таймер] Бот проснулся! Генерируем сообщение...")
        await send_random_mix(channel)
# ------------------------------------------

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower() == '!тест':
        await send_random_mix(message.channel)
        return

    learned_something_new = False

    if message.content:
        words = message.content.split()
        words_database.extend(words)
        learned_something_new = True
        print(f"[Текст] Выучены новые слова. Всего: {len(words_database)}")

    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image/'):
            file_extension = attachment.filename.split('.')[-1]
            file_path = f"{IMAGES_FOLDER}/{attachment.id}.{file_extension}"
            await attachment.save(file_path)
            images_database.append(file_path)
            learned_something_new = True
            print(f"[Картинка] Скачан новый файл. Всего картинок: {len(images_database)}")

            if len(images_database) > MAX_IMAGES:
                oldest_image_path = images_database.pop(0)
                if os.path.exists(oldest_image_path):
                    os.remove(oldest_image_path)
                print(f"[Очистка] Удалена старая картинка.")

    if learned_something_new:
        save_memory({"words": words_database, "images": images_database})

async def send_random_mix(channel):
    if len(words_database) < 5:
        print("[Инфо] Слишком мало слов в памяти для генерации текста.")
        return 

    number_of_words = random.randint(1, 11)
    random_words = random.sample(words_database, k=number_of_words)
    response_text = " ".join(random_words)

    if images_database and random.choice([True, False]):
        random_image_path = random.choice(images_database)
        if os.path.exists(random_image_path):
            picture = discord.File(random_image_path)
            await channel.send(response_text, file=picture)
            return

    await channel.send(response_text)

client.run(TOKEN)