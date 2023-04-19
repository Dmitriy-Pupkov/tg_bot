import os
import logging
import io
import asyncio
from urllib.request import urlopen
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ContextTypes
from telegram import Update, InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont
import aiohttp
from dotenv import load_dotenv

from data import db_session
from data.cards import Cards
from data.levels import Levels


load_dotenv()
BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


ACCESS_KEY = os.environ.get('APIKEY')
test_tasks = [1, 1, 1, 2, 2, 3, 3, 4, 5, 6, 7]
SESSION_NUMBER = 'session_number'


async def get_images(url, session: aiohttp.ClientSession):
    headers = {'Authorization': f'Client-ID {ACCESS_KEY}'}
    async with session.get(url, allow_redirects=True, headers=headers) as resp:
        json_response = await resp.json()
        return json_response


async def image_sending(update: Update, context: CallbackContext):
    msg = update.message.text
    img = Image.new("RGB", (485, 300), (255, 241, 206))
    my_font = ImageFont.truetype('sfns-display-bold.ttf', size=20)
    # my_font2 = ImageFont.truetype('globersemiboldfree.ttf', size=18)
    # decor = Image.open(urlopen('https://images.unsplash.com/photo-1579362816626-1ea1d0b7fa8a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=Mnw0MjgxMTh8MHwxfHNlYXJjaHwyfHwlRDAlQjQlRDAlQjUlRDAlQkIlRDElOEMlRDElODQlRDAlQjglRDAlQkQlRDElOEJ8cnV8MHx8fHwxNjgwODkwMzk5&ixlib=rb-4.0.3&q=80&w=162&h=100')) # как добавить картинку на отправляемое изображение
    # img.paste(decor, (100, 100))
    draw_text = ImageDraw.Draw(img)
    draw_text.text((50, 50), msg, font=my_font, fill=('#1C0606'))
    print(draw_text.textsize(msg, my_font))
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()
    # with open('front_sides/1.jpg', mode='rb') as pic:
    #     data = pic.read()
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

    url = f'https://api.unsplash.com/search/photos?page=1&query={query}&per_page=6&lang=ru'
    async with aiohttp.ClientSession() as session:
        task = [get_images(url, session)]
        for future in asyncio.as_completed(task):
            data = await future
    pictures_urls = list(map(InputMediaPhoto, [picture['urls']['small'] for picture in data['results']]))
    print(pictures_urls)
    await context.bot.send_media_group(update.effective_message.chat_id, pictures_urls)


async def start(update, context):
    user = update.effective_user
    await update.message.reply_html(
        rf'''Привет, {user.mention_html()}!Я - тренировочный бот для помощи в работе над проектом.
Напишите мне сообщение, и я пришлю его в виде изображения.''',
    )


async def help_command(update, context):
    await update.message.reply_text("Я пока не умею помогать....")


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавляет задание в очередь."""
    chat_id = update.effective_message.chat_id

    # context.job_queue.run_repeating(alarm, due, chat_id=chat_id, name=str(chat_id), data=due)

    text = "Timer successfully set!"
    await update.effective_message.reply_text(text)


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"Beep! {job.data} секунд закончились!")


async def show_tasks(update: Update, context: CallbackContext):

    await update.message.reply_text('Сегодня такие уровни на проверке:')


async def show_levels(update: Update, context: CallbackContext):
    if context.user_data[SESSION_NUMBER]:
        pass
    else:
        context.user_data[SESSION_NUMBER] = 1
    db_sess = db_session.create_session()
    for level in db_sess.query(Levels):
        pass
    # user.name = "Измененное имя пользователя"
    # user.created_date = datetime.datetime.now()
    db_sess.commit()
    await update.message.reply_text(
        '''Во сколько вам напоминать о сессии? Выберите час или введите своё время в 23-часовом формате hh:mm''')


def main():

    application = Application.builder().token(BOT_TOKEN).build()
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, image_sending)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(text_handler)
    application.add_handler(CommandHandler("show_levels", show_levels))

    application.run_polling()


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    db_session.global_init("db/cards.db")
    # db_sess = db_session.create_session()
    # i = 1
    # while i != 128:
    #     level = Levels(days_period=i)
    #     db_sess.add(level)
    #     db_sess.commit()
    #     i *= 2
    # period = db_sess.query(Levels).filter(Levels.id == 1)
    # first_card = Cards(front_side=os.path.join('front_sides', '1'), back_side=os.path.join('back_sides', '1'), level=1)
    # db_sess = db_session.create_session()
    # db_sess.add(first_card)
    # db_sess.commit()
    main()
