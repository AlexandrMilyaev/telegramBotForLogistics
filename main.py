import states as states
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from wialon import Wialon, WialonError

from telegram import States, comands_types, Orders

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext

import sqlite3 as sql

import logging
import config

import pandas as pd


def loyaut_keyboard_tags():
    inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)
    for keys in orders.data_by_tags.keys():
        inline_kb_full.add(types.KeyboardButton('{}'.format(keys), callback_data='btn_tags{}'.format(keys)))
    return inline_kb_full


con = sql.connect('user.db')
cur = con.cursor()
'''
with con:
    con.execute("""
        CREATE TABLE USER (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT
        );
    """)
'''

bot = Bot(token=config.telegram_token)
storege = MemoryStorage()
dp = Dispatcher(bot, storage=storege)
dp.middleware.setup(LoggingMiddleware())

wialon_api = Wialon()
result = wialon_api.token_login(token=config.logistics_token)
wialon_api.sid = result['eid']
orders = Orders(wialon_object=wialon_api, token=config.logistics_token, itemId=22403020)
logging.basicConfig(level=logging.INFO)
orders_list = list()
# print(user)

df = pd.DataFrame({
    'phone_number',
    'first_name',
    'last_name',
    'user_id'
})

with open('import/contacts.txt', 'r', encoding='utf-8') as g:
    pass


@dp.message_handler(commands="start")
async def cmd_test(message: types.Message):
    inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)
    inline_kb_full.add(types.KeyboardButton('Отправить свой контакт ☎️', request_contact=True))
    await States.STATE_GET_NUMBER.set()
    await message.answer("Отправьте свой номер телефона для идентификации",
                         reply_markup=inline_kb_full)


@dp.message_handler(state=States.STATE_GET_NUMBER, content_types=types.ContentTypes.CONTACT)
async def get_number(message: types.Message, state: FSMContext):
    df = pd.read_csv('user.csv', delimiter=',')
    phone = df['phone_number'].tolist()
    try:
        print(phone.index(int(dict(message.contact)['phone_number'])))
        await message.answer('Ваш номер уже присутствует в списке авторизированиых номеров.\n'
                             'Отправьте команду /help для получения информации'
                             ' по доступным командам.'
                             , reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        driver = orders.get_driver(dict(message.contact)['phone_number'])
        if driver is None:
            await message.answer('Извените, вы отсутствуете в списке разрешонных пользователей',
                                 reply_markup=types.ReplyKeyboardRemove())
        else:
            list_pandas = [dict(message.contact)]
            df = df.append(list_pandas)
            df.to_csv('user.csv', index=False)
            if driver == 0:
                await message.answer('Авторизация прошла успешно,'
                                     ' но за вами не закреплен автомобиль.\n'
                                     ' Обратитесь к диспетчеру для назначения на автомобиль.'
                                     , reply_markup=types.ReplyKeyboardRemove())
            else:
                await message.answer('Авторизация прошла успешно.\n'
                                     'Отпраьте команду /help для получения информации'
                                     ' по доступным командам.'
                                     , reply_markup=types.ReplyKeyboardRemove())

    finally:
        phone.clear()
        await state.finish()


@dp.message_handler(commands="help")
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    df = pd.read_csv('user.csv', delimiter=',')
    df_user_id = df['user_id'].tolist()
    if user_id in df_user_id:
        msg = "Я на стадии разработки,\nно вот что я умею уже сейчас:\n"
        for cmd, text in comands_types.items():
            msg += cmd + ' - ' + text + '\n'
        await message.answer(msg)
    else:
        await message.answer('Мы не знакомы.\n'
                             'Пройдите авторизацию, отправив команду /start')


@dp.message_handler(commands="test")
async def cmd_test(message: types.Message):
    user_id = message.from_user.id
    df = pd.read_csv('user.csv', delimiter=',')
    df_user_id = df['user_id'].tolist()
    if user_id in df_user_id:
        data = orders.get_orders()
        data = data[0]['orders']
        for key, _ in data.items():
            flag = _['f'] & 8
            if flag:
                print(_)
        await message.answer("Эта команда вам не нужна!\n"
                             "Она нужна разработчику для отладки некотрых функций.")
    else:
        await message.answer('Мы не знакомы.\n'
                             'Пройдите авторизацию, отправив команду /start')


@dp.message_handler(commands="start_route")
async def cmd_start_route(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    df = pd.read_csv('user.csv', delimiter=',')
    df_user_id = df['user_id'].tolist()
    if user_id in df_user_id:
        orders.get_orders()
        keyboard = loyaut_keyboard_tags()
        await state.update_data(tags=orders.data_by_tags.keys())
        await States.STATE_GET_TAG.set()
        await message.answer('Выбирите тег', reply_markup=keyboard)
        print(message.from_user.id)
    else:
        await message.answer('Мы не знакомы.\n'
                             'Пройдите авторизацию, отправив команду /start')


@dp.message_handler(state=States.STATE_GET_TAG, content_types=types.ContentTypes.TEXT)
async def get_tag(message: types.Message, state: FSMContext):
    if message.text in orders.data_by_tags.keys():
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        keyboard.add(types.KeyboardButton('Далее ->'))
        for tag, order in orders.data_by_tags[message.text].items():
            keyboard.add(types.KeyboardButton(f'{tag}: {order}'))

        keyboard.add(types.KeyboardButton('Назад <-'))
        await state.update_data(tag_selected=message.text.casefold())
        await message.answer('Выбирите нужные заявки.\n'
                             'Для выбора другого тега нажмите "Назад <-".\n'
                             'Для создания маршрута нажмите "Далее ->"',
                             reply_markup=keyboard)
        await States.STATE_GET_ORDERS.set()
    else:
        await message.answer('Нет такого тега')


@dp.message_handler(state=States.STATE_GET_ORDERS, content_types=types.ContentTypes.TEXT)
async def get_order(message: types.Message, state: FSMContext):
    if message.text == 'Назад <-':
        keyboard = loyaut_keyboard_tags()
        # await state.update_data(tags=orders.data_by_tags.keys())
        await States.STATE_GET_TAG.set()
        await message.answer('Выбирите тег', reply_markup=keyboard)

    elif message.text[message.text.find(':') + 2:] in orders.orders_list.values():
        try:
            orders.orders_for_route.update({int(message.text[:message.text.find(':')]):
                                                message.text[message.text.find(':') + 2:]})
            orders_list.append(message.text)
            print(orders_list)
            await message.answer(f'Заявка "{message.text}" добавлена в список для состовления маршрута')
        except Exception as e:
            await message.answer('Некоректная заявка')

    elif message.text == 'Далее ->':
        await States.STATE_CREATE_ROUTS.set()
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        keyboard.add(types.KeyboardButton('Да'))
        keyboard.add(types.KeyboardButton('Нет'))
        data = ''
        for _ in orders_list:
            data += _ + '\n'
        await message.answer(f'Создать маршрут согласно следуещего списка заявок?:\n{data}', reply_markup=keyboard)


@dp.message_handler(state=States.STATE_CREATE_ROUTS, content_types=types.ContentTypes.TEXT)
async def create_route(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        df = pd.read_csv('user.csv', delimiter=',')
        user_id = df['user_id'].tolist()
        phone = df['phone_number'].tolist()
        pointer_user_id = user_id.index(message.from_user.id)
        phone = phone[pointer_user_id]
        driver = orders.get_driver(str(phone))
        orders.craete_route(list(orders.orders_for_route.keys()), driver)
        orders.orders_for_route.clear()
        orders_list.clear()
        await message.answer('Маршрут создан', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    elif message.text == 'Нет':
        orders.orders_for_route.clear()
        orders_list.clear()
        await message.answer('Отмена создания маршрута!', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()


@dp.message_handler(commands="add_orders")
async def cmd_start_route(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    df = pd.read_csv('user.csv', delimiter=',')
    df_user_id = df['user_id'].tolist()
    if user_id in df_user_id:
        await message.answer('Эта команда пока не работает. С помощью ее вы сможете в будущем '
                             'добавлять заявки в уже существующий маршрут')
    else:
        await message.answer('Мы не знакомы.\n'
                             'Пройдите авторизацию, отправив команду /start')


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def text_answer(message: types.Message):
    user_id = message.from_user.id
    df = pd.read_csv('user.csv', delimiter=',')
    df_user_id = df['user_id'].tolist()
    if user_id in df_user_id:
        await message.answer('Я вас не понимаю.\n'
                             'Отправьте команду /help для ознакомления со списком доступных команд')
    else:
        await message.answer('Мы не знакомы.\n'
                             'Пройдите авторизацию, отправив команду /start')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
