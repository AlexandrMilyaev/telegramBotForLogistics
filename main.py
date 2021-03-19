from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from wialon import Wialon, WialonError

from telegram import States, comands_types, Orders

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext

import logging
import config


def loyaut_keyboard_tags():
    inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)
    for keys in orders.data_by_tags.keys():
        inline_kb_full.add(types.KeyboardButton('{}'.format(keys), callback_data='btn_tags{}'.format(keys)))
    return inline_kb_full


bot = Bot(token=config.telegram_token)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())



wialon_api = Wialon()
result = wialon_api.token_login(token=config.logistics_token)
wialon_api.sid = result['eid']
orders = Orders(wialon_object=wialon_api, token=config.logistics_token)
logging.basicConfig(level=logging.INFO)



@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    await message.reply("Привет!\nЯ создан для того,\nчто бы ты в суботу мог работать!")


@dp.message_handler(commands="help")
async def cmd_help(message: types.Message):
    msg = "Я на стадии разработки,\nно вот что я умею уже сейчас:\n"
    for cmd, text in comands_types.items():
        msg += cmd + ' - ' + text + '\n'
    await message.answer(msg)


@dp.message_handler(state='*', commands="get_orders")
async def cmd_get_orders(message: types.Message, state: FSMContext):
    orders.get_orders()
    keyboard = loyaut_keyboard_tags()
    await state.update_data(tags=orders.data_by_tags.keys())
    await States.STATE_GET_TAG.set()
    await message.reply('Выбирите тег', reply_markup=keyboard)


@dp.message_handler(state=States.STATE_GET_TAG, content_types=types.ContentTypes.TEXT)
async def get_tag(message: types.Message, state: FSMContext):
    if message.text in orders.data_by_tags.keys():
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        for order in orders.data_by_tags[message.text]:
            keyboard.add(types.KeyboardButton(f'{order}'))
        keyboard.add(types.KeyboardButton('Назад <-'))
        await message.reply('Выбирите нужные заявки. Для выбора другого тега нажмите "Назад"',
                            reply_markup=keyboard)
        await States.STATE_GET_ORDERS.set()
    else:
        await message.reply('Нет такого тега')


@dp.message_handler(state=States.STATE_GET_ORDERS, content_types=types.ContentTypes.TEXT)
async def get_order(message: types.Message, state: FSMContext):
    if message.text == 'Назад <-':
        keyboard = loyaut_keyboard_tags()
        # await state.update_data(tags=orders.data_by_tags.keys())
        await States.STATE_GET_TAG.set()
        await message.reply('Выбирите тег', reply_markup=keyboard)



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
