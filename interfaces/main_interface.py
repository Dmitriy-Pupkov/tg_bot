import os
import logging

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ConversationHandler, \
    ContextTypes, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Bot

load_dotenv()

BOT_TOKEN = os.environ.get('TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

MAIN_MENU = ["/start_session", "/set_goal", "/set_notification", "/help"]
ONE, TWO, THREE, FOUR = range(4)


reply_markup = ReplyKeyboardMarkup([['back']])


async def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("start_session", callback_data=str(ONE)),
            InlineKeyboardButton("set_goal", callback_data=str(TWO)),
        ],
        [InlineKeyboardButton("set_notification", callback_data=str(THREE))],
        [InlineKeyboardButton("help", callback_data=str(FOUR))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Приветствую!', reply_markup=reply_markup)
    return ONE


async def start_session(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text('hbjkbjhk.', reply_markup=reply_markup)
    await query.edit_message_text('Сессия начата.')
    # await context.bot.edit_message_text('fbsnjgfbj')
    # return await state(update, context)
    return TWO


async def set_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Установите цель повторений")
    # return await state(update, context)
    return TWO


async def set_notification(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Установите время ежедневного напоминания")
    # await update.message.reply_text("Установите время ежедневного напоминания")
    # return await state(update, context)
    return TWO


async def help(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('Здесь будет показана справочная информация по боту.')
    # return await state(update, context)
    return TWO


async def state(update: Update, context: CallbackContext):
    await update.message.reply_text(reply_markup=ReplyKeyboardMarkup([['back']]))
    return TWO


async def stop(update: Update, context: CallbackContext):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ONE: [
                CallbackQueryHandler(start_session, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(set_goal, pattern="^" + str(TWO) + "$"),
                CallbackQueryHandler(set_notification, pattern="^" + str(THREE) + "$"),
                CallbackQueryHandler(help, pattern="^" + str(FOUR) + "$"),

            ],
            TWO: [CommandHandler('back', start)]
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
    main()
