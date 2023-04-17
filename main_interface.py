import os
import logging
import datetime
import asyncio
import io
from urllib.request import urlopen

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ConversationHandler, \
    ContextTypes, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Bot
from PIL import Image, ImageDraw, ImageFont
import aiohttp

from data import db_session
from data.cards import Cards
from data.levels import Levels

load_dotenv()

BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

FIRST_REP_INTERVAlS = [0, 0, 1, 3, 11, 23, 55]
SESSION_NUMBER = 'session_number'
(MAIN_MENU, BACK, NOTIF_SET, FOUR, CARD_ADDING,
 WHICH_SIDE, TEXT_AND_IMAGES, USER_TEXT) = map(chr, range(8))

time_keyboard = [['Назад'],
                  ['8:00', '9:00', '10:00', '11:00'],
                  ['12:00', '13:00', '14:00', '15:00'],
                  ['16:00', '17:00', '18:00', '19:00'],
                  ['20:00', '21:00', '22:00', '23:00'],
                  ['0:00', '1:00', '2:00', '3:00'],
                  ['4:00', '5:00', '6:00', '7:00']]
time_markup = ReplyKeyboardMarkup(time_keyboard, one_time_keyboard=True)
regex = ''
for line in time_keyboard[1:]:
    regex += '|'.join(line) + '|'
regex = regex[:-1]

reply_markup = ReplyKeyboardMarkup([['В главное меню']])


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("Начать сессию", callback_data=str(MAIN_MENU)),
            InlineKeyboardButton("Установить цель", callback_data=str(BACK)),
        ],
        [InlineKeyboardButton("Установить время ежедневного напоминания", callback_data=str(NOTIF_SET))],
         [InlineKeyboardButton("О методе интервальных повторений", callback_data=str(FOUR))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '''Вы в главном меню! Чтобы продолжить, нажмите на 1 из кнопок:''', reply_markup=reply_markup)
    return MAIN_MENU


async def start_session(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    db_sess = db_session.create_session()
    if SESSION_NUMBER not in context.user_data.keys():
        context.user_data[SESSION_NUMBER] = 1
        for level in db_sess.query(Levels):
            level.repetition_date = datetime.date.today() + datetime.timedelta(days=FIRST_REP_INTERVAlS[level.id - 1])
            print(level.repetition_date, datetime.date.today())
            db_sess.commit()
    for_today = []
    for level in db_sess.query(Levels).filter(Levels.repetition_date == datetime.date.today().strftime('%Y-%m-%d 00:00:00.000000')):
        for_today.append(str(level.id))

    await query.message.reply_text(
        f'''Отлично! Сессия начата. Сегодня на проверке уровни {', '.join(sorted(for_today, reverse=True))}''',
        reply_markup=ReplyKeyboardMarkup([['В главное меню'], ['Добавить новую карту']]))
    for level in db_sess.query(Levels).filter(Levels.id.in_(for_today)):
        repetition_date = level.repetition_date + datetime.timedelta(days=level.days_period)
        print(repetition_date)
    return CARD_ADDING


async def set_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text('Установите цель повторений', reply_markup=reply_markup)
    return BACK


async def set_notification(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text("Во сколько вам напоминать о сессии? Выберите час или введите своё время в формате hh:mm",
                                   reply_markup=time_markup)
    return NOTIF_SET


async def notif_setting(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_time = update.message.text
    try:
        time = datetime.time(*(map(int, user_time.split(':'))), tzinfo=datetime.timezone(datetime.timedelta(hours=5)))
    except ValueError as err:
        logger.error(err)
        await update.effective_message.reply_text('Ой, это неправильное время, введите время в нужном формате')
        return
    job_removed = remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_daily(notification, time, name=str(chat_id), chat_id=chat_id)
    text = f'Замечательно! Ежедневное напоминание установлено на {time} '
    if job_removed:
        text += 'и старое время удалено.'
    await update.message.reply_text(text, reply_markup=reply_markup)
    return BACK


async def notification(context: CallbackContext):
    job = context.job
    await context.bot.send_message(job.chat_id,
                                   text='Привет! Пора повторить важную информацию для достижения твоей цели!')


async def card_adding(update: Update, context: CallbackContext):
    await update.message.reply_text(
        '''Хорошо, с какой стороны начнём оформление?''',
        reply_markup=ReplyKeyboardMarkup([['Лицевая сторона'], ['Обратная сторона']]))
    return WHICH_SIDE


async def add_inf(update: Update, context: CallbackContext):
    await update.message.reply_text(
        '''Добавьте нужную вам информацию. Помните, что лучше создать много карточек с отдельными фактами, чем одну большую 😉''',
        reply_markup=ReplyKeyboardMarkup([['Добавить текст'], ['Добавить изображение']]))
    return TEXT_AND_IMAGES


async def text(update: Update, context: CallbackContext):
    await update.message.reply_text('Напишите текст, который хотите видеть на этой стороне',
                                    reply_markup=ReplyKeyboardRemove())
    return USER_TEXT
    # await update.message.reply_text(
    #     '''Добавьте нужную вам информацию. Помните, что лучше создать много карточек с отдельными фактами, чем одну большую 😉''',
    #     reply_markup=ReplyKeyboardMarkup([['добавить текст'], ['Добавить изображение']]))
    # return WHICH_SIDE


async def image(update: Update, context: CallbackContext):
    await update.message.reply_text('Тут можно будет добавить картинку')


async def text_adding(update: Update, context: CallbackContext):
    msg = update.message.text
    img = Image.new("RGB", (485, 300), (255, 241, 206))
    my_font = ImageFont.truetype('sfns-display-bold.ttf', size=20)
    # my_font2 = ImageFont.truetype('globersemiboldfree.ttf', size=18)
    # decor = Image.open(urlopen('https://images.unsplash.com/photo-1579362816626-1ea1d0b7fa8a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=Mnw0MjgxMTh8MHwxfHNlYXJjaHwyfHwlRDAlQjQlRDAlQjUlRDAlQkIlRDElOEMlRDElODQlRDAlQjglRDAlQkQlRDElOEJ8cnV8MHx8fHwxNjgwODkwMzk5&ixlib=rb-4.0.3&q=80&w=162&h=100')) # как добавить картинку на отправляемое изображение
    # img.paste(decor, (100, 100))
    draw_text = ImageDraw.Draw(img)
    draw_text.text((50, 50), msg, font=my_font, fill=('#1C0606'))
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()
    # with open('front_sides/1.jpg', mode='rb') as pic:
    #     data = pic.read()
    await update.message.reply_photo(imgByteArr, caption='Вот так будет выглядеть эта сторона',
                                     reply_markup=ReplyKeyboardMarkup([['Изменить'], ['Дополнить'], ['Сохранить'],]))


async def help(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text('Здесь будет показана справочная информация по боту.', reply_markup=reply_markup)
    return BACK


async def stop(update: Update, context: CallbackContext):
    await update.message.reply_text("Всего доброго!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(start_session, pattern="^" + str(MAIN_MENU) + "$"),
                CallbackQueryHandler(set_goal, pattern="^" + str(BACK) + "$"),
                CallbackQueryHandler(set_notification, pattern="^" + str(NOTIF_SET) + "$"),
                CallbackQueryHandler(help, pattern="^" + str(FOUR) + "$"),

            ],
            BACK: [MessageHandler(filters.Regex("^(В главное меню)$") & ~filters.COMMAND, start)],
            NOTIF_SET: [MessageHandler(filters.Regex("^(Назад)$") & ~filters.COMMAND, start),

                        MessageHandler(
                            filters.Regex(f"^({regex})$") & ~filters.COMMAND, notif_setting
                        ),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, notif_setting)],
            CARD_ADDING: [MessageHandler(filters.Regex("^(В главное меню)$") & ~filters.COMMAND, start),
                          MessageHandler(filters.Regex("^(Добавить новую карту)$") & ~filters.COMMAND, card_adding)],
            WHICH_SIDE: [MessageHandler(filters.Regex("^(Лицевая сторона)$") & ~filters.COMMAND, add_inf),
                          MessageHandler(filters.Regex("^(Обратная сторона)$") & ~filters.COMMAND, add_inf)],
            TEXT_AND_IMAGES: [MessageHandler(filters.Regex("^(Добавить текст)$") & ~filters.COMMAND, text),
                          MessageHandler(filters.Regex("^(Добавить изображение)$") & ~filters.COMMAND, image)],
            USER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_adding)],
            # END_ROUTES: [
            #     CallbackQueryHandler(start_over, pattern="^" + str(ONE) + "$"),
            #     CallbackQueryHandler(end, pattern="^" + str(TWO) + "$"),
            # ],
        },

        # states={
        #     1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_session)],
        #     2: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_goal)],
        #     3: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_notification)],
        #     4: [MessageHandler(filters.TEXT & ~filters.COMMAND, help)]
        # },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    db_session.global_init("db/cards.db")
    main()
