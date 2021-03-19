from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from wialon import Wialon, WialonError

from telegram import States, comands_types, Orders
import logging
import config

bot = Bot(token=config.telegram_token)
dp = Dispatcher(bot)

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


@dp.message_handler(commands="get_orders")
async def cmd_get_orders(message: types.Message):
    orders.get_orders()

    inline_kb_full = types.InlineKeyboardMarkup(row_width=3)
    for keys in orders.data_by_tags.keys():
        inline_kb_full.add(types.InlineKeyboardButton('{}'.format(keys), callback_data='btn_tags{}'.format(keys)))

    print(orders.data_by_tags.keys())
    await message.reply('Выбирите тег', reply_markup=inline_kb_full)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
