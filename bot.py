import discord
import random
import os
from dotenv import load_dotenv

# Загружаем секреты из файла .env
load_dotenv()
# Достаем наш токен из загруженных секретов
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

words_database = []
images_database = []

@client.event
async def on_ready():
    print(f'Бот {client.user} успешно запущен и готов слушать!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content:
        words = message.content.split()
        words_database.extend(words)

    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image/'):
            images_database.append(attachment.url)

    if random.randint(1, 20) == 1:
        await send_random_mix(message.channel)

async def send_random_mix(channel):
    if len(words_database) < 5:
        return 

    number_of_words = random.randint(3, 7)
    random_words = random.sample(words_database, k=number_of_words)
    
    response_text = " ".join(random_words)

    if images_database and random.choice([True, False]):
        random_image = random.choice(images_database)
        response_text += f"\n{random_image}"

    await channel.send(response_text)

# Запускаем бота, используя токен, который мы достали из .env
client.run(TOKEN)