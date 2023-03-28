import os
import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ContextTypes
from telegram import Update, InputMediaPhoto
from PIL import Image, ImageDraw
import io
from requests import get
import aiohttp
import asyncio

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


ACCESS_KEY = os.environ.get('APIKEY')


async def get_images(url, session: aiohttp.ClientSession):
    headers = {'Authorization': f'Client-ID {ACCESS_KEY}'}
    response = await session.get(url, allow_redirects=True, headers=headers)
    await get_urls(response)
    response.close()


async def get_urls(response: aiohttp.ClientResponse):
    json_response = response.json
    pictures_urls = list(map(InputMediaPhoto, [picture['urls']['regular'] for picture in json_response['results']]))


def image_search(query):
    headers = {'Authorization': f'Client-ID {ACCESS_KEY}'}
    url = f'https://api.unsplash.com/search/photos?page=1&query={query}&per_page=6&lang=ru'  # client_id={ACCESS_KEY}
    json_response = get(url, headers=headers).json()
    return json_response


async def image_sending(update: Update, context: CallbackContext):
    msg = update.message.text  # пока это работает только с латинской раскладкой
    img = Image.new("RGB", (324, 200), (255, 241, 206))
    draw_text = ImageDraw.Draw(img)
    draw_text.text((50, 50), msg, fill=('#1C0606'))
    # decor = Image.open('star.png')  # как добавить картинку на отправляемое изображение
    # img.paste(decor, (100, 100), decor)
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()
    await update.message.reply_photo(imgByteArr, caption='Вот так будет выглядеть карточка')


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = ' '.join(list(context.args))
    except TypeError as err:
        logger.error(err)
        await update.effective_message.reply_text('Параметр должен быть строкой')
        return
    except IndexError as err:
        logger.error(err)
        await update.effective_message.reply_text('Нужно указать параметр')
        return

    data = image_search(query)
    pictures_urls = list(map(InputMediaPhoto, [picture['urls']['regular'] for picture in data['results']]))
    #
    # session = aiohttp.ClientSession()
    # url = f'https://api.unsplash.com/search/photos?page=1&query={query}&per_page=6&lang=ru'
    # task = asyncio.create_task(get_images(url, session))
    #
    # await asyncio.gather(task)
    # await session.close()
    await context.bot.send_media_group(update.effective_message.chat_id, pictures_urls)


async def start(update, context):
    """Отправляет сообщение когда получена команда /start"""
    user = update.effective_user
    await update.message.reply_html(
        rf'''Привет, {user.mention_html()}!Я - тренировочный бот для помощи в работе над проектом.
Напишите мне сообщение, и я пришлю его в виде изображения.''',
    )


async def help_command(update, context):
    """Отправляет сообщение когда получена команда /help"""
    await update.message.reply_text("Я пока не умею помогать....")


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, image_sending)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(text_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
