import os
import logging

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
from telegram import ReplyKeyboardMarkup, Update

load_dotenv()

BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

logger = logging.getLogger(__name__)


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Вы нажали на кнопку Старт! Клавиатура пока не готова, выберите 1 из предложенных комманд: /start_session /set_notification /set_goal /help',
        reply_markup=ReplyKeyboardMarkup(
            [['/start_session', '/set_notification'], ['/set_goal', '/help']]))


async def help(update: Update, context: CallbackContext):
    await update.message.reply_text('Здесь будет показана справочная информация по боту.')


async def start_session(update: Update, context: CallbackContext):
    await update.message.reply_text('Сессия запущена')


async def set_notification(update: Update, context: CallbackContext):
    await update.message.reply_text('Установите время ежедневного напоминания')


async def set_goal(update: Update, context: CallbackContext):
    await update.message.reply_text('Установите цель повторений')


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('start_session', start_session))
    application.add_handler(CommandHandler('set_notification', set_notification))
    application.add_handler(CommandHandler('set_goal', set_goal))
    application.add_handler(CommandHandler('help', help))
    application.run_polling()


if __name__ == '__main__':
    main()
