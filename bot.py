import discord
import random
import os
import asyncio
import requests # Библиотека для запросов к ImgBB
from pymongo import MongoClient # Библиотека для работы с MongoDB
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

# Достаем все настройки из файла .env
TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID', 0))
MONGO_URI = os.getenv('MONGO_URI')
IMGBB_KEY = os.getenv('IMGBB_KEY')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

MAX_IMAGES = 100
background_task_started = False

# --- ПОДКЛЮЧЕНИЕ К ОБЛАЧНОЙ БАЗЕ ДАННЫХ MONGODB ---
db_client = MongoClient(MONGO_URI)
db = db_client["discord_bot_db"]
collection = db["memory"]

# Если бот запускается впервые, создаем для него пустую ячейку памяти
if collection.count_documents({"_id": "memory_data"}) == 0:
    collection.insert_one({"_id": "memory_data", "words": [], "images": []})

# Загружаем память из облака при старте
db_data = collection.find_one({"_id": "memory_data"})
words_database = db_data.get("words", [])
images_database = db_data.get("images", [])
# --------------------------------------------------

def upload_to_imgbb(image_url):
    """Отправляет временную ссылку Discord в ImgBB и получает вечную ссылку"""
    try:
        payload = {"key": IMGBB_KEY, "image": image_url}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if res.status_code == 200:
            return res.json()['data']['url']
    except Exception as e:
        print(f"Ошибка загрузки картинки: {e}")
    return None

@client.event
async def on_ready():
    global background_task_started
    # Добавляем flush=True в каждый принт
    print(f'Бот {client.user} успешно подключен к облаку!', flush=True)
    print(f'В облаке: слов - {len(words_database)}, картинок - {len(images_database)}.', flush=True)
    
    if not background_task_started and TARGET_CHANNEL_ID != 0:
        client.loop.create_task(random_message_loop())
        background_task_started = True

async def random_message_loop():
    await client.wait_until_ready()
    try:
        channel = client.get_channel(TARGET_CHANNEL_ID) or await client.fetch_channel(TARGET_CHANNEL_ID)
    except Exception as e:
        print(f"❌ ОШИБКА ДОСТУПА к каналу: {e}")
        return

    if channel is None:
        print("❌ ОШИБКА: Не могу найти канал! Проверь TARGET_CHANNEL_ID в .env")
        return

    while not client.is_closed():
        delay_seconds = random.randint(1800, 2700)
        print(f"[Таймер] Бот уснул. Следующее сообщение через {delay_seconds} сек.")
        await asyncio.sleep(delay_seconds)
        print("[Таймер] Бот проснулся! Отправляем сообщение...")
        await send_random_mix(channel)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower() == '!тест':
        await send_random_mix(message.channel)
        return
    if message.content.lower().startswith('!забудь '):
        # Вырезаем само слово из команды
        word_to_forget = message.content[8:].strip()
        
        # Запоминаем, сколько слов было
        old_length = len(words_database)
        
        # Перезаписываем память, выкидывая нужное слово (независимо от регистра букв)
        words_database[:] = [w for w in words_database if w.lower() != word_to_forget.lower()]
        
        if len(words_database) < old_length:
            # Если слово нашлось и удалилось, обновляем MongoDB
            collection.update_one(
                {"_id": "memory_data"},
                {"$set": {"words": words_database}}
            )
            deleted_count = old_length - len(words_database)
            await message.channel.send(f"🧹 Удалил слово '{word_to_forget}' из памяти (стерто {deleted_count} шт).")
        else:
            await message.channel.send(f"🤷 Я не помню, чтобы когда-то знал слово '{word_to_forget}'.")
        return

    words_updated = False
    images_updated = False

    # 1. СЛОВА -> В ПАМЯТЬ
    if message.content:
        # Разбиваем сообщение на отдельные слова
        all_words = message.content.split()
        
        # МАГИЯ ЗДЕСЬ: Оставляем только те слова, которые НЕ начинаются с '!'
        clean_words = [word for word in all_words if not word.startswith('!')]
        
        # Если после фильтрации остались нормальные слова, сохраняем их
        if clean_words:
            words_database.extend(clean_words)
            words_updated = True
            print(f"[Текст] Выучены слова (без команд). В облаке будет: {len(words_database)}")
            

    # 2. КАРТИНКИ -> В IMGBB
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image/'):
            # Загружаем картинку в облако и получаем вечную ссылку
            permanent_url = upload_to_imgbb(attachment.url)
            if permanent_url:
                images_database.append(permanent_url)
                images_updated = True
                print(f"[Картинка] Загружена в ImgBB! Всего: {len(images_database)}")

                # Соблюдаем лимит в 100 ссылок
                if len(images_database) > MAX_IMAGES:
                    images_database.pop(0)

    # 3. СОХРАНЯЕМ ВСЁ В MONGODB ОДНИМ РАЗОМ
    if words_updated or images_updated:
        collection.update_one(
            {"_id": "memory_data"},
            {"$set": {"words": words_database, "images": images_database}}
        )

async def send_random_mix(channel):
    if len(words_database) < 5:
        return 

    number_of_words = random.randint(1, 7)
    random_words = random.sample(words_database, k=number_of_words)
    response_text = " ".join(random_words)

    if images_database and random.choice([True, False]):
        random_image_url = random.choice(images_database)
        response_text += f"\n{random_image_url}"

    await channel.send(response_text)

keep_alive()
client.run(TOKEN, log_handler=discord.utils.setup_logging())