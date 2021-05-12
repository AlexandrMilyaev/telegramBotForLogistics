from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from wialon import Wialon, WialonError

try:
    from telegram import States, comands_types, Orders
except:
    import os
    import sys
    dir_path = os.path.dirname(os.path.realpath('import/telegram.py'))
    sys.path.insert(0, dir_path)
    from telegram import States, comands_types, Orders

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
import time
import logging
import config
import pandas as pd

def loyaut_keyboard_tags():
    inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)

    for keys in orders.data_by_tags.keys():
        inline_kb_full.add(types.KeyboardButton('{}'.format(keys), callback_data='btn_tags{}'.format(keys)))
    return inline_kb_full


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
    if orders.user_id is not None:
        inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)
        inline_kb_full.add(types.KeyboardButton('Отправить свой контакт ☎️', request_contact=True))
        await States.STATE_GET_NUMBER.set()
        await message.answer("Отправьте свой номер телефона для идентификации",
                             reply_markup=inline_kb_full)
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')

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
            flag = _['f'] & 4
            if flag:
                print(_)
        await message.answer("Эта команда вам не нужна!\n"
                             "Она нужна разработчику для отладки некотрых функций.")
    else:
        await message.answer('Мы не знакомы.\n'
                             'Пройдите авторизацию, отправив команду /start')


@dp.message_handler(commands="start_route")
async def cmd_start_route(message: types.Message, state: FSMContext):
    if orders.user_id is None:
        user_id = message.from_user.id
        df = pd.read_csv('user.csv', delimiter=',')
        df_user_id = df['user_id'].tolist()
        if user_id in df_user_id:
            # заносим имя менеджера и его id в обьект
            pointer_user_id = df_user_id.index(user_id)
            df_first_name = df['first_name'].tolist()
            df_last_name = df['last_name'].tolist()
            if df_last_name[pointer_user_id] == 'nan':
                orders.user_name = f'{df_first_name[pointer_user_id]} '
            else:
                orders.user_name = f'{df_first_name[pointer_user_id]} ' \
                                   f'{df_last_name[pointer_user_id]}'
            orders.user_id = message.from_user.id

            orders.get_orders()
            keyboard = loyaut_keyboard_tags()
            await state.update_data(tags=orders.data_by_tags.keys())
            await States.STATE_GET_TAG.set()
            await message.answer('Выбирите тег', reply_markup=keyboard)
            print(message.from_user.id)
        else:
            await message.answer('Мы не знакомы.\n'
                                 'Пройдите авторизацию, отправив команду /start')
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')

@dp.message_handler(state=States.STATE_GET_TAG, content_types=types.ContentTypes.TEXT)
async def get_tag(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text in orders.data_by_tags.keys():
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            keyboard.add(types.KeyboardButton('Далее ->'))
            for tag, order in orders.data_by_tags[message.text].items():
                data = order['n']
                keyboard.add(types.KeyboardButton(f'{tag}: {data}'))

            keyboard.add(types.KeyboardButton('Назад <-'))
            await state.update_data(tag_selected=message.text.casefold())
            await message.answer('Выбирите нужные заявки.\n'
                                 'Для выбора другого тега нажмите "Назад <-".\n'
                                 'Для создания маршрута нажмите "Далее ->"',
                                 reply_markup=keyboard)
            await States.STATE_GET_ORDERS.set()
        else:
            await message.answer('Нет такого тега')
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_GET_ORDERS, content_types=types.ContentTypes.TEXT)
async def get_order(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        data = []
        for _ in orders.orders_list.values():
            data.append(_['n'])
        if message.text == 'Назад <-':
            keyboard = loyaut_keyboard_tags()
            await States.STATE_GET_TAG.set()
            await message.answer('Выбирите тег', reply_markup=keyboard)

        elif message.text[message.text.find(':') + 2:] in data:
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.orders_list[id_orders]
                data_orders['f'] = 1
                time_1 = int(time.time())
                time_1 = time_1 - (time_1 % 86400) + time.altzone
                data_orders['tf'] = time_1 + data_orders['tf']
                data_orders['tt'] = time_1 + data_orders['tt']
                orders.orders_for_route.update({id_orders: data_orders})
                orders_list.append(message.text)
                await message.answer(f'Заявка "{message.text}" добавлена в список для состовления маршрута')
            except Exception as e:
                await message.answer('Некоректная заявка')

        elif message.text == 'Далее ->':
            await States.STATE_INITIAL_WAREHOUSE.set()
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            keyboard.add(types.KeyboardButton('Без склада'))
            for key, warehouse in orders.warehouse.items():
                house = warehouse['n']
                keyboard.add(types.KeyboardButton(f'{key}: {house}'))
            await message.answer(f'Выберете начальный склад', reply_markup=keyboard)
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_INITIAL_WAREHOUSE, content_types=types.ContentTypes.TEXT)
async def initial_warehouse(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text != 'Без склада':
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.warehouse[id_orders]
                data_orders['f'] = 260
                time_1 = int(time.time())
                time_1 = time_1 - (time_1 % 86400) + time.altzone
                data_orders['tf'] = time_1 + data_orders['tf']
                data_orders['tt'] = time_1 + data_orders['tt']
                orders.warehouses_for_route.update({id_orders: data_orders})
                orders_list.insert(0, message.text)
                await message.answer(f'Начальный склад "{message.text}" добавлен в список для состовления маршрута')
                await States.STATE_FINAL_WAREHOUSE.set()
                keyboard = types.ReplyKeyboardMarkup(row_width=2)
                keyboard.add(types.KeyboardButton('Без склада'))
                for key, warehouse in orders.warehouse.items():
                    house = warehouse['n']
                    keyboard.add(types.KeyboardButton(f'{key}: {house}'))
                await message.answer(f'Выберете конечный склад', reply_markup=keyboard)
            except Exception as e:
                await message.answer('Некоректный склад')
        else:
            await States.STATE_FINAL_WAREHOUSE.set()
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            keyboard.add(types.KeyboardButton('Без склада'))
            for key, warehouse in orders.warehouse.items():
                house = warehouse['n']
                keyboard.add(types.KeyboardButton(f'{key}: {house}'))
            await message.answer(f'Выберете конечный склад', reply_markup=keyboard)
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_FINAL_WAREHOUSE, content_types=types.ContentTypes.TEXT)
async def final_warehouse(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text != 'Без склада':
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.warehouse[id_orders]
                print(data_orders)
                data_orders['f'] = 264
                time_1 = int(time.time())
                time_1 = time_1 - (time_1 % 86400) + time.altzone
                data_orders['tf'] = time_1 + data_orders['tf']
                data_orders['tt'] = time_1 + data_orders['tt']
                orders.warehouses_for_route.update({id_orders: data_orders})
                orders_list.append(message.text)
                await message.answer(f'Конечный склад "{message.text}" добавлен в список для состовления маршрута')
                await States.STATE_CREATE_ROUTS.set()
                keyboard = types.ReplyKeyboardMarkup(row_width=2)
                keyboard.add(types.KeyboardButton('Да'))
                keyboard.add(types.KeyboardButton('Нет'))
                data = ''
                for _ in orders_list:
                    data += _ + '\n'
                await message.answer(f'Создать маршрут согласно следуещего списка заявок?:\n{data}', reply_markup=keyboard)
            except Exception as e:
                await message.answer('Некоректный склад')
        else:
            await States.STATE_CREATE_ROUTS.set()
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            keyboard.add(types.KeyboardButton('Да'))
            keyboard.add(types.KeyboardButton('Нет'))
            data = ''
            for _ in orders_list:
                data += _ + '\n'
            await message.answer(f'Создать маршрут согласно следуещего списка заявок?:\n{data}', reply_markup=keyboard)
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_CREATE_ROUTS, content_types=types.ContentTypes.TEXT)
async def create_route(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text == 'Да':
            df = pd.read_csv('user.csv', delimiter=',')
            user_id = df['user_id'].tolist()
            phone = df['phone_number'].tolist()
            pointer_user_id = user_id.index(message.from_user.id)
            phone = phone[pointer_user_id]
            driver = orders.get_driver(str(phone))

            orders.craete_route(list(orders.orders_for_route.values()),
                                list(orders.warehouses_for_route.values()),
                                driver)
            orders.orders_for_route.clear()
            orders.warehouses_for_route.clear()
            orders_list.clear()
            await message.answer('Маршрут создан', reply_markup=types.ReplyKeyboardRemove())
            await state.finish()
            orders.user_name = None
            orders.user_id = None

        elif message.text == 'Нет':
            orders.orders_for_route.clear()
            orders_list.clear()
            await message.answer('Отмена создания маршрута!', reply_markup=types.ReplyKeyboardRemove())
            await state.finish()
            orders.user_name = None
            orders.user_id = None
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(commands="add_orders")
async def cmd_add_orders(message: types.Message, state: FSMContext):
    if orders.user_id is None:
        user_id = message.from_user.id
        df = pd.read_csv('user.csv', delimiter=',')
        df_user_id = df['user_id'].tolist()
        if user_id in df_user_id:
            phone = df['phone_number'].tolist()
            pointer_user_id = df_user_id.index(user_id)
            phone = phone[pointer_user_id]
            driver = orders.get_driver(str(phone))

            # заносим имя менеджера и его id в обьект
            df_first_name = df['first_name'].tolist()
            df_last_name = df['last_name'].tolist()
            if df_last_name[pointer_user_id] == 'nan':
                orders.user_name = f'{df_first_name[pointer_user_id]} '
            else:
                orders.user_name = f'{df_first_name[pointer_user_id]} ' \
                                   f'{df_last_name[pointer_user_id]}'
            orders.user_id = message.from_user.id
            orders.user_id = message.from_user.id

            order_data = orders.get_orders()
            orders_route = list()
            for key, route in order_data[0]['order_routes'].items():
                if route['st']['u'] == driver and route['st']['s'] == 1:
                    orders_route = route['ord']
            if len(orders_route) != 0:
                data = ''
                for key, order in order_data[0]['orders'].items():
                    if order['uid'] in orders_route:
                        data += f"{order['n']}\n"
                keyboard = types.ReplyKeyboardMarkup(row_width=2)
                keyboard.add(types.KeyboardButton('Да'))
                keyboard.add(types.KeyboardButton('Нет'))
                await message.answer('Ващ маршрут состоит из следующих заявок:.\n'
                                     f'{data}'
                                     'Добавить новую заявку?',
                                     reply_markup=keyboard)
                await States.STATE_INITIAL_ADD_ORDERS.set()

            else:
                await message.answer('За вами не закреплен маршрут.\n'
                                     'Для создания маршрута воспользуйтесь командой /start_route')
        else:
            await message.answer('Мы не знакомы.\n'
                                 'Пройдите авторизацию, отправив команду /start')
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_INITIAL_ADD_ORDERS, content_types=types.ContentTypes.TEXT)
async def initial_add_orders(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text == 'Да':
            await States.STATE_GET_TAG_ADD_ORDERS.set()
            orders.get_orders()
            keyboard = loyaut_keyboard_tags()
            await message.answer('Выбирите тег', reply_markup=keyboard)
        elif message.text == 'Нет':
            await message.answer('Команда отменена!', reply_markup=types.ReplyKeyboardRemove())
            await state.finish()
            orders.user_name = None
            orders.user_id = None
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_GET_TAG_ADD_ORDERS, content_types=types.ContentTypes.TEXT)
async def get_tag_add_orders(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text in orders.data_by_tags.keys():
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            for tag, order in orders.data_by_tags[message.text].items():
                data = order['n']
                keyboard.add(types.KeyboardButton(f'{tag}: {data}'))

            keyboard.add(types.KeyboardButton('Назад <-'))
            await state.update_data(tag_selected=message.text.casefold())
            await message.answer('Выбирите нужную заявку.\n'
                                 'Для выбора другого тега нажмите "Назад <-".',
                                 reply_markup=keyboard)
            await States.STATE_FINAL_ADD_ORDERS.set()
        else:
            await message.answer('Нет такого тега')
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_FINAL_ADD_ORDERS, content_types=types.ContentTypes.TEXT)
async def final_add_orders(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        user_id = message.from_user.id
        df = pd.read_csv('user.csv', delimiter=',')
        df_user_id = df['user_id'].tolist()
        data = []
        for _ in orders.orders_list.values():
            data.append(_['n'])
        if message.text[message.text.find(':') + 2:] in data:
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.orders_list[id_orders]
                data_orders['f'] = 1
                time_1 = int(time.time())
                time_1 = time_1 - (time_1 % 86400) + time.altzone
                data_orders['tf'] = time_1 + data_orders['tf']
                data_orders['tt'] = time_1 + data_orders['tt']
                data_orders['callMode'] = "create"
                phone = df['phone_number'].tolist()
                pointer_user_id = df_user_id.index(user_id)
                phone = phone[pointer_user_id]
                driver = orders.get_driver(str(phone))
                order_data = orders.orders
                orders_route = list()
                route_id = int()
                for key, route in order_data[0]['order_routes'].items():
                    if route['st']['u'] == driver and route['st']['s'] == 1:
                        orders_route = route['ord']
                        route_id = route['uid']
                if len(orders_route) != 0:
                    data.clear()
                    for key, order in order_data[0]['orders'].items():
                        if order['uid'] in orders_route:
                            order['callMode'] = "update"
                            data.append(order)
                    data.sort(key=lambda dat: dat['p']['r']['vt'])
                    order_list = data
                    data_len = len(data) - 1
                    orders_for_route = []
                    warehouses_for_route = []
                    if data[data_len]['f'] & 8:
                        orders_for_route.append(data[data_len - 1])
                        warehouses_for_route.append(data[data_len])
                        order_list.pop()
                    else:
                        orders_for_route.append(data[data_len])
                    orders_for_route.append(data_orders)
                    gis = {
                        "provider": 1,  # 0-нет, 1-gurtam, 2-google
                        "addPoints": 1,  # 0-не возвращать трек, 1-вернуть трек
                        "speed": 50  # скорость для оптимизации
                    }
                    params = {
                        "itemId": orders.itemIds,
                        "orders": orders_for_route,
                        "units": [driver],
                        "warehouses": warehouses_for_route,
                        "criterions": {},
                        "priority": {driver: {0: 0}},
                        "flags": 131,
                        "gis": gis
                    }

                    request = wialon_api.call('order_optimize', params)
                    order_warehouse = orders_for_route
                    order_warehouse.extend(warehouses_for_route)
                    vt = orders_for_route[0]['p']['r']['vt']
                    i = orders_for_route[0]['p']['r']['i']
                    i += 1
                    for keys, data in request.items():
                        if keys == 'details':
                            pass
                        elif keys == 'success':
                            pass
                        elif keys == 'summary':
                            pass
                        else:
                            t_prev = data['orders'][0]['tm']
                            ml_prev = 0
                            data['orders'].pop(0)
                            for _ in data['orders']:
                                number = _['id']
                                print(number)
                                tm = _['tm'] - t_prev
                                ml = _['ml'] - ml_prev
                                vt = vt + tm
                                data_orders = dict(order_warehouse[number])
                                data_orders['p']['r'] = {
                                    "id": route_id,  # id маршрута
                                    "i": i,  # порядковый номер (0..)
                                    "m": ml,  # пробег с предыдущей точки по плану, м
                                    "t": tm,  # время с предыдущей точки по плану, сек
                                    "vt": vt,  # время посещения по плану, UNIX_TIME
                                    "ndt": 300  # время, за которое должно прийти уведомление, с
                                }
                                if vt >= data_orders['tt']:
                                    data_orders['tt'] = vt + 3600
                                t_prev = _['tm']
                                ml_prev = _['ml']
                                data_orders['u'] = keys
                                data_orders['rp'] = _['p']
                                if data_orders['f'] == 1:
                                    data_orders['callMode'] = 'create'
                                    data_orders['uid'] = 0
                                    data_orders['id'] = 0
                                    data_orders['st'] = 0
                                else:
                                    data_orders['callMode'] = 'update'
                                order_list.append(data_orders)
                                i += 1
                    params = {
                        "itemId": orders.itemIds,
                        "orders": order_list,
                        "routeId": route_id,
                        "callMode": "update"
                    }
                    response = wialon_api.call('order_route_update', params)
                await message.answer(f'Заявка "{message.text}" добавлена маршрут', reply_markup=types.ReplyKeyboardRemove())
                await state.finish()
                data.clear()
                data_orders.clear()
                orders.user_name = None
                orders.user_id = None
            except Exception as e:
                await message.answer('Некоректная заявка')

        elif message.text == 'Назад <-':
            keyboard = loyaut_keyboard_tags()
            await States.STATE_GET_TAG_ADD_ORDERS.set()
            await message.answer('Выбирите тег', reply_markup=keyboard)
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')


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
