import os
import logging
import datetime
import asyncio

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ConversationHandler, \
    ContextTypes, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Bot

from data import db_session
from data.cards import Cards
from data.levels import Levels

load_dotenv()

BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

FIRST_REP_INTERVAlS = [0, 0, 1, 3, 11, 23, 55]
SESSION_NUMBER = 'session_number'
MAIN_MENU, BACK, NOTIF_SET, FOUR = range(4)
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
            InlineKeyboardButton("начать сессию", callback_data=str(MAIN_MENU)),
            InlineKeyboardButton("установить цель", callback_data=str(BACK)),
        ],
        [InlineKeyboardButton("Установить время ежедневного напоминания", callback_data=str(NOTIF_SET))],
         [InlineKeyboardButton("о методе интервальных повторений", callback_data=str(FOUR))]
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
            print(level.repetition_date == datetime.date.today())
            db_sess.commit()
    for_today = []
    for level in db_sess.query(Levels).filter(Levels.repetition_date == datetime.date.today()): # filter не работает,
        # результат получается пустой
        # если его убрать, id  выводятся
        print(level.id)
        for_today.append(str(level.id))
    print(for_today)
    await query.message.reply_text(
        f'''Отлично! Сессия начата. Сегодня на проверке уровни {', '.join(for_today)}''',
        reply_markup=reply_markup)  # ReplyKeyboardMarkup([['Закончить сессию']])
    for level in db_sess.query(Levels).filter(Levels.id.in_(for_today)):
        repetition_date = level.repetition_date + datetime.timedelta(days=level.days_period)
        print(repetition_date)
    return BACK


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
                        MessageHandler(filters.TEXT & ~filters.COMMAND, notif_setting)]
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
