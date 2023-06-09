import os
import logging
import datetime
import asyncio
import io
import random
from urllib.request import urlopen

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, ConversationHandler, \
    ContextTypes, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, \
    InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont
import aiohttp

from data import db_session
from data.cards import Cards
from data.levels import Levels
from data.users import Users

load_dotenv()

BOT_TOKEN = os.environ.get('TOKEN')
ACCESS_KEY = os.environ.get('APIKEY')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

FIRST_REP_INTERVAlS = [0, 0, 1, 3, 11, 23, 55]
SESSION_NUMBER = 'session_number'
CURRENT_PICTURE = 'current_picture'
FINISHED_PICTURE = 'finished_picture'
CURRENT_SIDE = 'current_side'
FINISHED_SIDE = 'finished_side'
TEXT_STATE = 'text_state'
USER_QUERY = 'image_query'
NUMBERS_REGEX = 'numbers_regex'
CARDS_FOR_TODAY = 'cards_for_today'
LEVELS_FOR_TODAY = 'levels_for_today'
CURRENT_CARD = 'current_card'
goal = ''
level_index = 0
(MAIN_MENU, BACK, NOTIF_SET, FOUR, CARD_ADDING,
 WHICH_SIDE, TEXT_AND_IMAGES, USER_TEXT, PROCESSING, CHANGED_TEXT, SAVING_OR_SIDE_CHANGING,
 USER_CHOICE, USER_FILE, IMAGE_QUERY, NUMBER_OF_PICTURES, WHICH_IMAGE, SENT_PICS, PICTURE_OPTION, FILE_SENDING,
 USER_GOAL, CARD_CHECKING,
 ) = map(chr, range(21))
numbers = ''

my_font = ImageFont.truetype('sfns-display-bold.ttf', size=25)
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

main_menu_markup = ReplyKeyboardMarkup([['В главное меню']], one_time_keyboard=True)


class CardSide:
    def __init__(self, side: str, txt=None, text_pasting_coords=(20, 20), additional_pic=None,
                 img_pasting_coords=(0, 0)):
        self.side = side
        self.card_img = None
        self.decor_img = additional_pic
        self.text = txt
        self.decor_coords = img_pasting_coords
        self.text_coords = text_pasting_coords
        self.image_size = 400, 300
        self.pil_img = Image.new("RGB", self.image_size, (255, 247, 245))

    def get_text(self):
        return self.text

    def get_self_img(self):
        return self.card_img

    def add_text(self, txt: str):
        draw_text = ImageDraw.Draw(self.pil_img)
        self.text = txt
        number_of_lines = (draw_text.textlength(self.text, my_font) // (self.image_size[0] - 20)) + 1
        words = txt.split()
        lines = []
        for i in range(0, int(number_of_lines)):
            text_line = []
            for word in words:
                if (draw_text.textlength(' '.join(text_line), my_font) + draw_text.textlength(word, my_font)) <= (
                        self.image_size[0] - 30):
                    print(draw_text.textlength(' '.join(words), my_font), (self.image_size[0] - 30))
                    if draw_text.textlength(' '.join(words), my_font) < (self.image_size[0] - 30):
                        lines.append(words)
                        break
                    text_line.append(word)
                else:
                    lines.append(text_line)
                    words = words[len(text_line):]
                    break
        for i in range(len(lines)):
            draw_text.text((self.text_coords[0], self.text_coords[1] + i * 30), ' '.join(lines[i]), font=my_font,
                           fill='#1C0606')

    def add_pic(self, url='', filename=''):
        params = f'&h={self.image_size[1]}'
        if url:
            print(url + params)
            self.decor_img = Image.open(urlopen(url + params))  # как добавить картинку на отправляемое изображение
        if filename:
            self.decor_img = Image.open(filename)
            # class 'PIL.JpegImagePlugin.JpegImageFile
        self.image_size = self.decor_img.size
        self.pil_img = self.pil_img.resize(self.decor_img.size)
        self.pil_img.paste(self.decor_img, (0, 0))
        if self.text:
            self.add_text(self.text)

    def make_image(self) -> bytes:
        # my_font2 = ImageFont.truetype('globersemiboldfree.ttf', size=18)
        imgByteArr = io.BytesIO()
        self.pil_img.save(imgByteArr, format='PNG')
        imgByteArr = imgByteArr.getvalue()
        self.card_img = imgByteArr
        return self.card_img


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def group_numbers(number):
    if not number % 3:
        grouped_by_3 = [list(str(n) for n in range(i, i + 3)) for i in range(1, number, 3)]
    else:
        grouped_by_3 = [list(str(n) for n in range(i, i + 3)) for i in range(1, number - (number % 3), 3)] + [list(
            map(str, range(number - (number % 3) + 1, number + 1)))]
    return grouped_by_3


async def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("Начать сессию 📚", callback_data=str(MAIN_MENU)),
            InlineKeyboardButton("Установить цель🎯", callback_data=str(BACK)),
        ],
        [InlineKeyboardButton("Установить время ежедневного напоминания⏳", callback_data=str(NOTIF_SET))],
        [InlineKeyboardButton("О методе интервальных повторений🔍", callback_data=str(FOUR))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '''Вы в главном меню! Чтобы продолжить, нажмите на 1 из кнопок:''', reply_markup=reply_markup)
    return MAIN_MENU


async def start_session(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    db_sess = db_session.create_session()
    iters = []
    for i in db_sess.query(Users.user_id):
        iters.append(i[0])
    if (update.effective_message.chat_id not in iters) and (SESSION_NUMBER not in context.user_data.keys()):
        context.user_data[SESSION_NUMBER] = 1
        days_per_list = [2 ** i for i in range(7)]
        for i in range(7):
            level_e = Levels()
            level_e.repetition_date = datetime.date.today() + datetime.timedelta(
                days=FIRST_REP_INTERVAlS[i])
            level_e.days_period = days_per_list[i]
            level_e.user_id = update.effective_message.chat_id
            level_e.level_number = i + 1
            db_sess.add(level_e)
            db_sess.commit()
        user = Users()
        user.user_id = update.effective_message.chat_id
        db_sess.add(user)
        db_sess.commit()

    for_today = []
    cur_user_id = [update.effective_message.chat_id]
    for level in db_sess.query(Levels).filter(
            Levels.repetition_date == datetime.date.today().strftime('%Y-%m-%d 00:00:00.000000'),
            Levels.user_id.in_(cur_user_id)):
        for_today.append(str(level.level_number))
    for_today = sorted(for_today, reverse=True)
    context.user_data[LEVELS_FOR_TODAY] = for_today
    await query.message.reply_text(
        f'''Отлично! Сессия начата. Сегодня на проверке уровни: {', '.join(sorted(for_today, reverse=True))}''')
    for level in db_sess.query(Levels).filter(Levels.level_number.in_(for_today) & Levels.user_id.in_(cur_user_id)):
        repetition_date = level.repetition_date + datetime.timedelta(days=level.days_period)
        level.repetition_date = repetition_date
        db_sess.commit()
    cards = []
    for card in db_sess.query(Cards).filter(Cards.user_id.in_(cur_user_id) & Cards.level.in_(for_today)):
        cards.append(card)
    if not cards:
        await query.message.reply_text(
            f'''У вас пока ещё нет карт для проверки, создайте новые карты''',
            reply_markup=ReplyKeyboardMarkup([['В главное меню'], ['Добавить новую карту']], one_time_keyboard=True))
        return CARD_ADDING
    else:
        context.user_data[CARDS_FOR_TODAY] = cards
        one_level = [card for card in cards if card.level == int(for_today[0])]
        if not one_level:

            await query.message.reply_text(
                f'''На уровне {for_today[0]} ещё нет карточек, идём дальше''',
                reply_markup=ReplyKeyboardMarkup([['Да, хорошо']]))
            context.user_data[LEVELS_FOR_TODAY].pop(0)
        else:
            random.shuffle(one_level)
            print(one_level[0].front_side + '.jpg')
            with open(one_level[0].front_side + '.jpg', mode='rb') as pic:
                data = pic.read()
            await query.message.reply_photo(data, caption=f'Уровень {for_today[0]}',
                                            reply_markup=ReplyKeyboardMarkup([['Помню'], ['Не помню']]))
            context.user_data[CARDS_FOR_TODAY] = [card for card in cards if card.id != one_level[0].id]
            context.user_data[CURRENT_CARD] = one_level[0]
        return CARD_CHECKING


async def set_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        'Напишите, что вы хотите выучить с помощью метода интервальных повторений! Я буду напоминать вам об этом каждый день, чтобы вы не теряли мотивацию💪',
        reply_markup=main_menu_markup)
    return USER_GOAL


async def goal_saving(update: Update, context: CallbackContext):
    global goal
    user_goal = update.message.text
    goal = user_goal.lower()
    print(goal)
    await update.message.reply_text(
        "Хорошо, я запомнил, для чего вы это делаете😏",
        reply_markup=main_menu_markup)
    return BACK


async def set_notification(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Во сколько вам напоминать о сессии? Выберите час или введите своё время в формате hh:mm",
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
    text = f'Замечательно! Ежедневное напоминание установлено на {time.strftime("%H:%M")} '
    if job_removed:
        text += 'и старое время удалено.'
    await update.message.reply_text(text, reply_markup=main_menu_markup)
    return BACK


async def notification(context: CallbackContext):
    global goal
    job = context.job
    if goal:
        await context.bot.send_message(job.chat_id,
                                       text=f'Привет! Пора повторить важную информацию для того, чтобы {goal}☺ ',
                                       reply_markup=ReplyKeyboardRemove())
    else:
        await context.bot.send_message(job.chat_id,
                                       text=f'Привет! Пора повторить важную информацию, чтобы не забыть её ☺ ',
                                       reply_markup=ReplyKeyboardRemove())


async def card_showing(update: Update, context: CallbackContext):
    global level_index
    msg = update.message.text
    db_sess = db_session.create_session()
    if msg != 'Да, хорошо':
        with open(context.user_data[CURRENT_CARD].back_side + '.jpg', mode='rb') as pic:
            data = pic.read()
    if msg == 'Помню':
        card = db_sess.query(Cards).filter(Cards.id == context.user_data[CURRENT_CARD].id).first()
        if card.level == 7:
            db_sess.delete(card)
            db_sess.commit()
            os.remove(f'back_sides/{card.id}.jpg')
            os.remove(f'front_sides/{card.id}.jpg')
            await update.message.reply_text(f'Поздравляю, эта карта ушла из игры!')
        else:
            card.level += 1
            db_sess.commit()
        await update.message.reply_photo(data, caption=f'Отлично, карта переходит на следующий уровень! Теперь дальше',
                                         reply_markup=ReplyKeyboardRemove())
    elif msg == 'Не помню':
        card = db_sess.query(Cards).filter(Cards.id == context.user_data[CURRENT_CARD].id).first()
        card.level = 1
        db_sess.commit()
        await update.message.reply_photo(data, caption=f'Упс, карта возвращается на 1 уровень! Теперь дальше',
                                         reply_markup=ReplyKeyboardRemove())
    cards = context.user_data[CARDS_FOR_TODAY]
    if not cards:
        await update.message.reply_text(
            'Замечательно, вы повторили все карты на сегодня! Теперь можете добавить новые или закончить сессию',
            reply_markup=ReplyKeyboardMarkup([['Закончить сессию'], ['Добавить новую карту']]))
        return CARD_ADDING
    for_today = context.user_data[LEVELS_FOR_TODAY]
    one_level = [card for card in cards if card.level == int(for_today[level_index])]
    if not one_level:
        level_index += 1
        one_level = [card for card in cards if card.level == int(for_today[level_index])]
    # print(one_level.front_side + '.jpg')
    with open(one_level[0].front_side + '.jpg', mode='rb') as pic:
        data = pic.read()
    await update.message.reply_photo(data, caption=f'Уровень {for_today[level_index]}',
                                     reply_markup=ReplyKeyboardMarkup([['Помню'], ['Не помню']]))
    context.user_data[CARDS_FOR_TODAY] = [card for card in cards if card.id != one_level[0].id]
    context.user_data[CURRENT_CARD] = one_level[0]
    return CARD_CHECKING


async def card_adding(update: Update, context: CallbackContext):
    await update.message.reply_text(
        '''Хорошо, с какой стороны начнём оформление?''',
        reply_markup=ReplyKeyboardMarkup([['Лицевая сторона'], ['Обратная сторона']]))
    return WHICH_SIDE


async def add_inf(update: Update, context: CallbackContext):
    side = update.message.text
    if side[:-8] == 'Лицевая':
        context.user_data[CURRENT_SIDE] = 'front'
    if side[:-8] == 'Обратная':
        context.user_data[CURRENT_SIDE] = 'back'
    await update.message.reply_text(
        '''Добавьте нужную вам информацию. Помните, что лучше создать много карточек с отдельными фактами, чем одну большую 😉''',
        reply_markup=ReplyKeyboardMarkup([['Добавить текст'], ['Добавить изображение'], ['Назад']]))
    return TEXT_AND_IMAGES


async def text(update: Update, context: CallbackContext):
    if CURRENT_PICTURE in context.user_data.keys():
        if context.user_data[CURRENT_PICTURE].text:
            await update.message.reply_text('Что вы хотите сделать с существующим текстом?',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Изменить'], ['Дополнить'], ['Сохранить']]))
            return PROCESSING
    await update.message.reply_text('Напишите текст, который хотите видеть на этой стороне',
                                    reply_markup=ReplyKeyboardMarkup([['Назад']]))
    return USER_TEXT


async def text_adding(update: Update, context: CallbackContext):
    msg = update.message.text + ' '
    if CURRENT_PICTURE not in context.user_data.keys():
        context.user_data[CURRENT_PICTURE] = \
            CardSide(context.user_data[CURRENT_SIDE])
    context.user_data[CURRENT_PICTURE].add_text(msg)
    await update.message.reply_photo(context.user_data[CURRENT_PICTURE].make_image(),
                                     caption='Вот так будет выглядеть эта сторона',
                                     reply_markup=ReplyKeyboardMarkup([['Изменить'], ['Дополнить'], ['Сохранить'], ]))
    return PROCESSING


async def change_text(update: Update, context: CallbackContext):
    context.user_data[TEXT_STATE] = update.message.text
    await update.message.reply_text('Напишите текст, который хотите добавить или на который заменить',
                                    reply_markup=ReplyKeyboardMarkup([['Сохранить']]))

    return CHANGED_TEXT


async def change_card(update: Update, context: CallbackContext):
    old_text = context.user_data[CURRENT_PICTURE].text
    new_text = ''
    if context.user_data[TEXT_STATE] == 'Изменить':
        new_text = update.message.text
    if context.user_data[TEXT_STATE] == 'Дополнить':
        new_text = old_text + update.message.text
    # card_img = context.user_data[CURRENT_PICTURE].get_self_img()
    old_image = ''
    if context.user_data[CURRENT_PICTURE].decor_img:
        old_image = context.user_data[CURRENT_PICTURE].decor_img
    context.user_data[CURRENT_PICTURE] = CardSide(context.user_data[CURRENT_SIDE], new_text)
    context.user_data[CURRENT_PICTURE].add_text(new_text)
    if old_image:
        context.user_data[CURRENT_PICTURE].add_pic(old_image)
    await update.message.reply_photo(context.user_data[CURRENT_PICTURE].make_image(),
                                     caption='Вот так будет выглядеть эта сторона',
                                     reply_markup=ReplyKeyboardMarkup([['Изменить'], ['Дополнить'], ['Сохранить']]))
    return PROCESSING


async def saving(update: Update, context: CallbackContext):
    if FINISHED_SIDE in context.user_data.keys():
        save_button = 'Сохранить карту'
    else:
        save_button = 'Сохранить и перейти на другую сторону'
    await update.message.reply_text('Хорошо, эта часть сохранена', reply_markup=ReplyKeyboardMarkup([['Добавить текст',
                                                                                                      'Добавить изображение'],
                                                                                                     [save_button]]))
    return SAVING_OR_SIDE_CHANGING


async def side_changing(update: Update, context: CallbackContext):
    context.user_data[FINISHED_SIDE] = context.user_data[CURRENT_SIDE]
    context.user_data[FINISHED_PICTURE] = context.user_data[CURRENT_PICTURE]
    if context.user_data[FINISHED_SIDE] == 'front':
        context.user_data[CURRENT_SIDE] = 'back'
    else:
        context.user_data[CURRENT_SIDE] = 'front'
    context.user_data.pop(CURRENT_PICTURE)
    await update.message.reply_text('Отлично, вы оформили одну сторону карточки, теперь давайте оформим вторую!',
                                    reply_markup=ReplyKeyboardMarkup([['Добавить текст'],
                                                                      ['Добавить изображение']]))
    return TEXT_AND_IMAGES


async def card_saving(update: Update, context: CallbackContext):
    db_sess = db_session.create_session()
    card_ids = [card.id for card in db_sess.query(Cards)]
    next_number = card_ids[-1] + 1
    sides = (context.user_data[FINISHED_SIDE], context.user_data[CURRENT_SIDE])
    pictures = (context.user_data[FINISHED_PICTURE], context.user_data[CURRENT_PICTURE])
    for i in range(2):
        with open(f'{sides[i]}_sides/{next_number}.jpg', 'wb') as side:
            side.write(pictures[i].get_self_img())
    new_card = Cards(front_side=os.path.join('front_sides', str(next_number)),
                     back_side=os.path.join('back_sides', str(next_number)), level=1,
                     user_id=update.effective_message.chat_id)
    db_sess.add(new_card)
    db_sess.commit()
    await update.message.reply_text('Замечательно, новая карта сохранена!',
                                    reply_markup=ReplyKeyboardMarkup([['В главное меню'], ['Добавить новую карту']]))
    return CARD_ADDING


async def image(update: Update, context: CallbackContext):
    await update.message.reply_text('Какое изображение вы хотите добавить?',
                                    reply_markup=ReplyKeyboardMarkup([['Добавить свой файл'], ['Поиск картинки']]))
    return USER_CHOICE


async def file_adding(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Отправьте файл изображения, которое хотите видеть на карточке в формате jpg или png',
        reply_markup=ReplyKeyboardRemove())
    return FILE_SENDING


async def get_images(url, session: aiohttp.ClientSession):
    headers = {'Authorization': f'Client-ID {ACCESS_KEY}'}
    async with session.get(url, allow_redirects=True, headers=headers) as resp:
        json_response = await resp.json()
        return json_response


async def image_query(update: Update, context: CallbackContext):
    await update.message.reply_text('Введите запрос для поиска нужного Вам изображения',
                                    reply_markup=ReplyKeyboardMarkup([['Назад']]))
    return IMAGE_QUERY


async def number_of_pictures(update: Update, context: CallbackContext):
    context.user_data[USER_QUERY] = update.message.text
    await update.message.reply_text('Сколько изображений вы хотите увидеть? Отправьте число от 1 до 10',
                                    reply_markup=ReplyKeyboardRemove())
    return NUMBER_OF_PICTURES


async def image_search(update: Update, context: CallbackContext):
    try:
        number = int(update.message.text)
    except ValueError as err:
        logger.error(err)
        await update.effective_message.reply_text('Извините, количество страниц должно быть числом')
        return
    # print(numbers)
    url = f'https://api.unsplash.com/search/photos?page=1&query={context.user_data[USER_QUERY]}&per_page={number}&lang=ru'
    async with aiohttp.ClientSession() as session:
        task = [get_images(url, session)]
        for future in asyncio.as_completed(task):
            data = await future
    pictures_urls = list(map(InputMediaPhoto, [picture['urls']['regular'] for picture in data['results']]))
    context.user_data[SENT_PICS] = pictures_urls
    # print(pictures_urls)
    grouped_by_3 = group_numbers(number)

    await context.bot.send_media_group(update.effective_message.chat_id, pictures_urls)
    await update.message.reply_text('Какое изображение добавить на карту?',
                                    reply_markup=ReplyKeyboardMarkup(grouped_by_3))

    return WHICH_IMAGE


async def image_adding(update: Update, context: CallbackContext):
    try:
        image_number = int(update.message.text)
    except ValueError as err:
        logger.error(err)
        await update.message.reply_text(
            'Я пока не умею отвечать на такие сообщения, введите, пожалуйста, номер')
        return
    if int(image_number) > len(context.user_data[SENT_PICS]):
        await update.message.reply_text(f'Изображений только {len(context.user_data[SENT_PICS])}')
        return
    image_url = context.user_data[SENT_PICS][int(image_number) - 1].media
    # print(image_url)
    if CURRENT_PICTURE not in context.user_data.keys():
        context.user_data[CURRENT_PICTURE] = \
            CardSide(context.user_data[CURRENT_SIDE])
    msg = context.user_data[CURRENT_PICTURE].text
    context.user_data[CURRENT_PICTURE] = CardSide(context.user_data[CURRENT_SIDE], msg)
    context.user_data[CURRENT_PICTURE].add_pic(url=image_url)
    await update.message.reply_photo(context.user_data[CURRENT_PICTURE].make_image(),
                                     caption='Вот так будет выглядеть эта сторона',
                                     reply_markup=ReplyKeyboardMarkup(
                                         [['Изменить'], ['Удалить'], ['Сохранить'], ]))
    return PICTURE_OPTION


async def change_picture(update: Update, context: CallbackContext):
    await update.message.reply_text('На какое изображение заменить?',
                                    reply_markup=ReplyKeyboardMarkup([['Добавить свой файл', 'Поиск картинки'],
                                                                      ['Выбрать другое изображение из запроса']]))
    return USER_CHOICE


async def other_pic(update: Update, context: CallbackContext):
    grouped_by_3 = group_numbers(len(context.user_data[SENT_PICS]))

    await context.bot.send_media_group(update.effective_message.chat_id, context.user_data[SENT_PICS])
    await update.message.reply_text('Какое изображение добавить на карту?',
                                    reply_markup=ReplyKeyboardMarkup(grouped_by_3))

    return WHICH_IMAGE


async def delete_picture(update: Update, context: CallbackContext):
    msg = context.user_data[CURRENT_PICTURE].text
    context.user_data[CURRENT_PICTURE] = CardSide(context.user_data[CURRENT_SIDE], msg)
    await update.message.reply_photo(context.user_data[CURRENT_PICTURE].make_image(),
                                     caption='Дополнительное изображение удалено',
                                     reply_markup=ReplyKeyboardMarkup([['Добавить текст'],
                                                                       ['Добавить изображение']]))
    return TEXT_AND_IMAGES


async def get_photo(update: Update, context: CallbackContext):
    photo = update.message.effective_attachment
    if photo:
        user_file = await context.bot.get_file(photo[-1].file_id)
        if not os.path.exists('user_images') or not os.path.isdir('user_images'):
            os.mkdir('user_images')
        photo_path = os.path.join('user_images', f'{photo[-1].file_unique_id}.jpg')
        await user_file.download_to_drive(photo_path)
        if CURRENT_PICTURE not in context.user_data.keys():
            context.user_data[CURRENT_PICTURE] = \
                CardSide(context.user_data[CURRENT_SIDE])
        msg = context.user_data[CURRENT_PICTURE].text
        context.user_data[CURRENT_PICTURE] = CardSide(context.user_data[CURRENT_SIDE], msg)
        context.user_data[CURRENT_PICTURE].add_pic(filename=photo_path)
        await update.message.reply_photo(context.user_data[CURRENT_PICTURE].make_image(),
                                         caption='Вот так будет выглядеть эта сторона',
                                         reply_markup=ReplyKeyboardMarkup(
                                             [['Изменить'], ['Удалить'], ['Сохранить'], ]))
        return PICTURE_OPTION
    else:
        await update.message.reply_text("Вы сказали, что отправите свой файл")


async def help(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    with open('help_text1.txt', mode='r', encoding='utf-8') as help_text:
        text1 = help_text.readlines()
        text1 = ' '.join(text1)
    with open('help_text2.txt', mode='r', encoding='utf-8') as help_text:
        text2 = help_text.readlines()
        text2 = ' '.join(text2)
    with open('help_text3.txt', mode='r', encoding='utf-8') as help_text:
        text3 = help_text.readlines()
        text3 = ' '.join(text3)
    with open('help_text4.txt', mode='r', encoding='utf-8') as help_text:
        text4 = help_text.readlines()
        text4 = ' '.join(text4)

    await query.message.reply_text(text=text1, reply_markup=main_menu_markup)
    await query.message.reply_text(text=text2, reply_markup=main_menu_markup)
    await query.message.reply_text(text=text3, reply_markup=main_menu_markup)
    await query.message.reply_text(text=text4, reply_markup=main_menu_markup)
    return BACK


async def stop(update: Update, context: CallbackContext):
    await update.message.reply_text("Всего доброго!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    global numbers
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
                        MessageHandler(filters.TEXT & ~filters.COMMAND, notif_setting)],
            CARD_ADDING: [MessageHandler(
                filters.Regex("^(В главное меню)$") & ~filters.COMMAND, start),
                MessageHandler(filters.Regex("^(Закончить сессию)$") & ~filters.COMMAND, start),
                MessageHandler(filters.Regex("^(Добавить новую карту)$") & ~filters.COMMAND, card_adding)],
            WHICH_SIDE: [MessageHandler(filters.Regex("^(Лицевая сторона)$") & ~filters.COMMAND, add_inf),
                         MessageHandler(filters.Regex("^(Обратная сторона)$") & ~filters.COMMAND, add_inf)],
            TEXT_AND_IMAGES: [MessageHandler(filters.Regex("^(Добавить текст)$") & ~filters.COMMAND, text),
                              MessageHandler(filters.Regex("^(Добавить изображение)$") & ~filters.COMMAND, image),
                              MessageHandler(filters.Regex("^(Назад)$") & ~filters.COMMAND, card_adding)],
            USER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(Назад)$"), text_adding),
                        MessageHandler(filters.Regex("^(Назад)$") & ~filters.COMMAND, add_inf)],
            PROCESSING: [MessageHandler(filters.Regex("^(Изменить)$") & ~filters.COMMAND, change_text),
                         MessageHandler(filters.Regex("^(Дополнить)$") & ~filters.COMMAND, change_text),
                         MessageHandler(filters.Regex("^(Сохранить)$") & ~filters.COMMAND, saving)],
            CHANGED_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND &
                                          ~filters.Regex("^(Сохранить)$"), change_card),
                           MessageHandler(filters.Regex("^(Сохранить)$") & ~filters.COMMAND, saving)],
            SAVING_OR_SIDE_CHANGING: [MessageHandler(filters.Regex("^(Добавить текст)$") & ~filters.COMMAND, text),
                                      MessageHandler(
                                          filters.Regex("^(Сохранить и перейти на другую сторону)$") & ~filters.COMMAND,
                                          side_changing),
                                      MessageHandler(filters.Regex("^(Добавить изображение)$") & ~filters.COMMAND,
                                                     image),
                                      MessageHandler(filters.Regex("^(Сохранить карту)$") & ~filters.COMMAND,
                                                     card_saving)],
            USER_CHOICE: [MessageHandler(filters.Regex("^(Добавить свой файл)$") & ~filters.COMMAND, file_adding),
                          MessageHandler(filters.Regex("^(Поиск картинки)$") & ~filters.COMMAND, image_query),
                          MessageHandler(
                              filters.Regex("^(Выбрать другое изображение из запроса)$") & ~filters.COMMAND,
                              other_pic)
                          ],
            IMAGE_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND &
                                         ~filters.Regex("^(Назад)$"), number_of_pictures),
                          MessageHandler(filters.Regex("^(Назад)$") & ~filters.COMMAND, add_inf)],
            NUMBER_OF_PICTURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, image_search)],
            WHICH_IMAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, image_adding)],
            PICTURE_OPTION: [MessageHandler(filters.Regex("^(Изменить)$") & ~filters.COMMAND, change_picture),
                             MessageHandler(filters.Regex("^(Удалить)$") & ~filters.COMMAND, delete_picture),
                             MessageHandler(filters.Regex("^(Сохранить)$") & ~filters.COMMAND, saving)],
            FILE_SENDING: [MessageHandler(filters.PHOTO, get_photo)],
            USER_GOAL: [MessageHandler(filters.Regex("^(В главное меню)$") & ~filters.COMMAND, start),
                        MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(В главное меню)$"),
                                       goal_saving)],
            CARD_CHECKING: [MessageHandler(filters.Regex("^(Помню)$") & ~filters.COMMAND, card_showing),
                            MessageHandler(filters.Regex("^(Не помню)$") & ~filters.COMMAND, card_showing),
                            MessageHandler(filters.Regex("^(Да, хорошо)$") & ~filters.COMMAND, card_showing)],
            # END_ROUTES: [
            #     CallbackQueryHandler(start_over, pattern="^" + str(ONE) + "$"),
            #     CallbackQueryHandler(end, pattern="^" + str(TWO) + "$"),
            # ],
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    db_session.global_init("db/cards.db")
    main()
