import os
import logging

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ConversationHandler, \
    ContextTypes, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove

load_dotenv()

BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

logger = logging.getLogger(__name__)

MAIN_MENU = ["/start_session", "/set_goal", "/set_notification", "/help"]


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return int(query.data)  # проблема


async def start(update: Update, context: CallbackContext):
    query = update.callback_query
    keyboard = [
        [
            InlineKeyboardButton("/start_session", callback_data=1),
            InlineKeyboardButton("/set_goal", callback_data=2),
        ],
        [InlineKeyboardButton("/set_notification", callback_data=3)],
        [InlineKeyboardButton("/help", callback_data=4)]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Приветствую!', reply_markup=reply_markup)

    # await query.answer()
    # return int(query.data)


async def start_session(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Сессия начата.')
    return


async def set_goal(update: Update, context: CallbackContext):
    await update.message.reply_text("Установите цель повторений")


async def set_notification(update: Update, context: CallbackContext):
    await update.message.reply_text("Установите время ежедневного напоминания")


async def help(update: Update, context: CallbackContext):
    await update.message.reply_text('Здесь будет показана справочная информация по боту.')


async def stop(update: Update, context: CallbackContext):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_session)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_goal)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_notification)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, help)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()


if __name__ == '__main__':
    main()
