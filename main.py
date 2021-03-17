from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from wialon import Wialon, WialonError

from telegram import States, comands_types, Orders
import logging
import token

bot = Bot(token=token.telegram_token)
dp = Dispatcher(bot)

wialon_api = Wialon()
result = wialon_api.token_login(token=token.logistics_token)
wialon_api.sid = result['eid']
orders = Orders(wialon_object=wialon_api, token=token.logistics_token)
logging.basicConfig(level=logging.INFO)


@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    await message.reply("Привет!\nЯ создан для того,\nчто бы ты в суботу мог работать!")


@dp.message_handler(commands="help")
async def cmd_help(message: types.Message):
    msg = "Я на стадии разработки,\nно вот что я умею уже сейчас:\n"
    for cmd, text in comands_types.items():
        msg += cmd + ' - ' + text + '\n'
    print(msg)
    await message.answer(msg)


@dp.message_handler(commands="get_orders")
async def cmd_get_orders(message: types.Message):
    global orders
    try:
        spec = {
            "itemsType": "avl_resource",
            "propType": "propitemname",
            "propName": "orders",
            "propValueMask": "*",
            "sortType": "orders"
        }
        params = {
            "spec": spec,
            "force": 1,
            "flags": 524288,
            "from": 0,
            "to": 0
        }
        orders = wialon_api.call('core_search_items', params)
        orders = orders['items']
    except WialonError as e:
        print(e.args)
        res = wialon_api.token_login(
            token='d1dcbcc6fcac65add3de13b53aa92137B0B8283A39C934274F591684CA9222B97461A356')
        wialon_api.sid = res['eid']
        spec = {
            "itemsType": "avl_resource",
            "propType": "propitemname",
            "propName": "orders",
            "propValueMask": "*",
            "sortType": "orders"
        }
        params = {
            "spec": spec,
            "force": 1,
            "flags": 524288,
            "from": 0,
            "to": 0
        }
        orders = wialon_api.call('core_search_items', params)
        orders = orders['items']
    finally:
        tags_value = list()
        tags_key = dict(No_tags='')
        for el in orders:
            orders = el['orders']
            for name in orders.values():
                if name['f'] == 32:
                    if name['p']['tags'] == [] or type(name['p']['tags']) == str:
                        tags_value = tags_key.get('No_tags')
                        tags_value = list(tags_value)
                        tags_value.append(name['n'])
                        tags_key['No_tags'] = tags_value
                    else:
                        for tags in name['p']['tags']:
                            if tags_key.get(tags) is None:
                                tags_value = list(tags_value)
                                tags_key.update({tags: tags_value})
                            else:
                                tags_value = tags_key.get(tags)
                                tags_value = list(tags_value)
                                tags_value.append(name['n'])
                                tags_key[tags] = tags_value
        inline_kb_full = types.InlineKeyboardMarkup(row_width=3)
        for keys in tags_key.keys():
            inline_kb_full.add(types.InlineKeyboardButton('{}'.format(keys), callback_data='btn_tags{}'.format(keys)))

        print(tags_key.keys())
        await message.reply('Выбирите тег', reply_markup=inline_kb_full)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
