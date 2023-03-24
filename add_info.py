import os
import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
from telegram import Update
from PIL import Image, ImageDraw
import io

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


async def image_sending(update: Update, context: CallbackContext):
    msg = update.message.text
    img = Image.new("RGB", (324, 200), (255, 241, 206))
    draw_text = ImageDraw.Draw(img)
    draw_text.text((50, 50), msg, fill=('#1C0606'))
    # decor = Image.open('star.png')
    # img.paste(decor, (100, 100), decor)
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()

    await update.message.reply_photo(imgByteArr, caption='Вот так будет выглядеть карточка')


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
    text_handler = MessageHandler(filters.TEXT, image_sending)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(text_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
