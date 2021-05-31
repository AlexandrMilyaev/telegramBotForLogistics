#! venv/bin/python3

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from wialon import Wialon, WialonError
import os
try:
    from telegram import States, comands_types, Orders, exp_calc
except:
    import sys
    dir_path = os.path.dirname(os.path.realpath('import/telegram.py'))
    sys.path.insert(0, dir_path)
    from telegram import States, comands_types, Orders, exp_calc

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
import time
import logging
import config
import pandas as pd
import requests
print('Telegram activate!')

delay = 180


def loyaut_keyboard_tags():
    inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)
    data = list()
    for keys in orders.data_by_tags.keys():
        data.append(keys)
    data.sort()
    for keys in data:
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
format_log = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename="logFile.log", level=logging.INFO, format=format_log)
log = logging.getLogger(os.path.basename(__file__))
log.info("Start program")
orders_list = list()
df = pd.DataFrame({
    'phone_number',
    'first_name',
    'last_name',
    'user_id'
})




@dp.message_handler(commands="start")
async def cmd_test(message: types.Message):
    log.info(f"(command /start) message: {message.text}, user_id: {message.from_user.id}")

    if orders.user_id is None:
        inline_kb_full = types.ReplyKeyboardMarkup(row_width=2)
        inline_kb_full.add(types.KeyboardButton('Отправить свой контакт ☎️', request_contact=True))
        await States.STATE_GET_NUMBER.set()
        await message.answer("Отправьте свой номер телефона для идентификации",
                             reply_markup=inline_kb_full)
    else:
        await message.answer(f'Я заблокирован пользователем {orders.user_name}')

@dp.message_handler(state=States.STATE_GET_NUMBER, content_types=types.ContentTypes.CONTACT)
async def get_number(message: types.Message, state: FSMContext):
    log.info(f"(command /start.STATE_GET_NUMBER) message: {message.contact},"
             f" user_id: {message.from_user.id}({message.from_user.username})")

    df = pd.read_csv('user.csv', delimiter=',')
    phone = df['phone_number'].tolist()
    try:
        phone.index(int(dict(message.contact)['phone_number']))
        await message.answer('Ваш номер уже присутствует в списке авторизированиых номеров.\n'
                             'Отправьте команду /help для получения информации'
                             ' по доступным командам.'
                             , reply_markup=types.ReplyKeyboardRemove())
        log.info(f"(command /start.STATE_GET_NUMBER): Номер уже авторизирован")
    except ValueError:
        driver = orders.get_driver(dict(message.contact)['phone_number'])
        log.info(f"(command /start.STATE_GET_NUMBER): get_driver: {driver}")
        if driver is None:
            log.info(f"(command /start.STATE_GET_NUMBER): Номер отсутствует в списке разрешенных номеров")
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
                log.info(f"(command /start.STATE_GET_NUMBER): Авторизация успешна, но не привязан автомобиль")
            else:
                await message.answer('Авторизация прошла успешно.\n'
                                     'Отпраьте команду /help для получения информации'
                                     ' по доступным командам.'
                                     , reply_markup=types.ReplyKeyboardRemove())
                log.info(f"(command /start.STATE_GET_NUMBER): авторизация успешна")
    finally:
        phone.clear()
        await state.finish()
        log.info(f"(command /start.STATE_GET_NUMBER): Выход")


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
    df = pd.read_csv('user.csv', delimiter=',')
    user_id = df['user_id'].tolist()
    phone = df['phone_number'].tolist()
    pointer_user_id = user_id.index(message.from_user.id)
    phone = phone[pointer_user_id]
    driver = orders.get_driver(str(phone))
    print(driver)

    spec = {
        "itemsType": "avl_resource",
        "propType": "property",
        "propName": "sys_id",
        "propValueMask": '*',
        "sortType": "sys_id"
    }
    params = {
        "spec": spec,
        "force": 1,
        "flags": 1,
        "from": 0,
        "to": 0
    }
    data = wialon_api.call('core_search_items', params)
    print(data)
    for el in data['items']:
        if el['uacl'] & 0x600000000: # Просмотр заявок и его свойств, создание/редактирование/удаление заявок
            return print(el['id'])
    return print(None)
'''         
    orders.get_orders()
    origin = {}
    destination = {}
    waypoints = []
    uid = orders.itemIds
    sid = orders.sid
    data = {
        "origin": origin,
        "destination": destination,
        "waypoints": waypoints,
        "flags": 1
    }
    peyload = {
        "data": data,
        "uid": uid,
        "sid": sid
    }
    request = requests.post('http://hst-api.wialon.com/gis_get_route_via_waypoints', params=peyload)
    print(request.text)


'''





@dp.message_handler(commands="start_route")
async def cmd_start_route(message: types.Message, state: FSMContext):
    log.info(f"(command /start_route): message: {message.text},"
             f" user_id: {message.from_user.id} ({message.from_user.username})")
    if orders.user_id is None:
        user_id = message.from_user.id
        df = pd.read_csv('user.csv', delimiter=',')
        df_user_id = df['user_id'].tolist()
        pointer_user_id = df_user_id.index(user_id)
        phone = df['phone_number'].tolist()
        phone = phone[pointer_user_id]
        driver = orders.get_driver(str(phone))
        df_first_name = df['first_name'].tolist()
        df_last_name = df['last_name'].tolist()
        if user_id in df_user_id:
            # Проверяем, не привязан ли маршрут к водителю

            order_data = orders.get_orders()
            orders_route = list()
            for key, route in order_data[0]['order_routes'].items():
                if route['st']['u'] == driver and route['st']['s'] == 1:
                    orders_route = route['ord']
            log.info(f'orders_route: {orders_route}')
            if len(orders_route) != 0:
                data = ''
                for key, order in order_data[0]['orders'].items():
                    if order['uid'] in orders_route:
                        data += f"{order['n']}\n"

                await message.answer(f'За вами уже закреплен маршрут с заявками:\n'
                                     f'{data}'
                                     f'Для добавления заявки в маршрут, воспользуйтесь командой /add_orders')
                log.info('answer: За вами уже закреплен маршрут')
            else:
                # заносим имя менеджера и его id в обьект

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
                await message.answer('Выбирите тег или название заявки', reply_markup=keyboard)
                orders.save_time = int(time.time())
        else:
            await message.answer('Мы не знакомы.\n'
                                 'Пройдите авторизацию, отправив команду /start')
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
            log.info(f'Выход')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')
            log.info(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_GET_TAG, content_types=types.ContentTypes.TEXT)
async def get_tag(message: types.Message, state: FSMContext):
    log.info(f"(command /start_route.STATE_GET_TAG): message: {message.text},"
             f" user_id: {message.from_user.id} ({message.from_user.username})")
    if message.from_user.id == orders.user_id:
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        keyboard.add(types.KeyboardButton('Далее ->'))
        if message.text in orders.data_by_tags.keys():
            data_sort = sorted(orders.data_by_tags[message.text].values(), key = lambda sort: sort['n'])
            for order in data_sort:
                data = order['n']
                tag = order['id']
                keyboard.add(types.KeyboardButton(f'{tag}: {data}'))

            keyboard.add(types.KeyboardButton('Назад <-'))
            await state.update_data(tag_selected=message.text.casefold())
            await message.answer('Выбирите нужные заявки.\n'
                                 'Для выбора другого тега нажмите "Назад <-".\n'
                                 'Для создания маршрута нажмите "Далее ->"',
                                 reply_markup=keyboard)
            await States.STATE_GET_ORDERS.set()
        else:
            data = list()
            for order in orders.orders_list.values():
                name = order['n'].lower()


                print(name)
                if name.find(message.text.lower()) != -1:
                    data.append(order)
            if len(data) == 0:
                await message.answer('Нет заявок по вашему запросу')
            else:
                data.sort(key=lambda sort: sort['n'])
                try:
                    for numbers in range(100):
                        keyboard.add(types.KeyboardButton(f'{data[numbers]["id"]}: {data[numbers]["n"]}'))

                except:
                    pass
                keyboard.add(types.KeyboardButton('Назад <-'))
                await message.answer('Выбирите нужные заявки.\n'
                                     'Для нового поиска нажмите "Назад <-".\n'
                                     'Для создания маршрута нажмите "Далее ->"',
                                     reply_markup=keyboard)
                await States.STATE_GET_ORDERS.set()
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_GET_ORDERS, content_types=types.ContentTypes.TEXT)
async def get_order(message: types.Message, state: FSMContext):
    log.info(f"(command /start_route.STATE_GET_ORDERS): message: {message.text},"
             f" user_id: {message.from_user.id} ({message.from_user.username})")
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
                data_orders = orders.copy_order(id_orders, 1)
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
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_INITIAL_WAREHOUSE, content_types=types.ContentTypes.TEXT)
async def initial_warehouse(message: types.Message, state: FSMContext):
    log.info(f"(command /start_route.STATE_INTIAL_WAREHOUSE): message: {message.text},"
             f" user_id: {message.from_user.id} ({message.from_user.username})")
    if message.from_user.id == orders.user_id:
        if message.text != 'Без склада':
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.copy_order(id_orders, 260)
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
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_FINAL_WAREHOUSE, content_types=types.ContentTypes.TEXT)
async def final_warehouse(message: types.Message, state: FSMContext):
    log.info(f"(command /start_route.STATE_FINAL_WAREHOUSE): message: {message.text},"
             f" user_id: {message.from_user.id} ({message.from_user.username})")
    if message.from_user.id == orders.user_id:
        if message.text != 'Без склада':
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.copy_order(id_orders, 264)
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
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_CREATE_ROUTS, content_types=types.ContentTypes.TEXT)
async def create_route(message: types.Message, state: FSMContext):
    log.info(f"(command /start_route.STATE_CRAETE_ROUTS): message: {message.text},"
             f" user_id: {message.from_user.id} ({message.from_user.username})")
    try:
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
    except Exception as e:
        log.info(f'Ошибка: {e.args}')
        log.info(f'orders: {list(orders.orders_for_route.values())}')
        log.info(f'warehouse: {list(orders.warehouses_for_route.values())}')
        orders.orders_for_route.clear()
        orders_list.clear()
        await message.answer(f'Ошибка создания маршрута: {e.args}', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        orders.user_name = None
        orders.user_id = None

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
                await message.answer('Ваш маршрут состоит из следующих заявок:.\n'
                                     f'{data}'
                                     'Добавить новую заявку?',
                                     reply_markup=keyboard)
                await States.STATE_INITIAL_ADD_ORDERS.set()

            else:
                await message.answer('За вами не закреплен маршрут.\n'
                                     'Для создания маршрута воспользуйтесь командой /start_route')
                orders.user_name = None
                orders.user_id = None
        else:
            await message.answer('Мы не знакомы.\n'
                                 'Пройдите авторизацию, отправив команду /start')
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_INITIAL_ADD_ORDERS, content_types=types.ContentTypes.TEXT)
async def initial_add_orders(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        if message.text == 'Да':
            await States.STATE_GET_TAG_ADD_ORDERS.set()
            orders.get_orders()
            keyboard = loyaut_keyboard_tags()
            await message.answer('Выбирите тег или введите название заявки', reply_markup=keyboard)
        elif message.text == 'Нет':
            await message.answer('Команда отменена!', reply_markup=types.ReplyKeyboardRemove())
            await state.finish()
            orders.user_name = None
            orders.user_id = None
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_GET_TAG_ADD_ORDERS, content_types=types.ContentTypes.TEXT)
async def get_tag_add_orders(message: types.Message, state: FSMContext):
    if message.from_user.id == orders.user_id:
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        if message.text in orders.data_by_tags.keys():
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            data_sort = sorted(orders.data_by_tags[message.text].values(), key=lambda sort: sort['n'])
            for order in data_sort:
                data = order['n']
                tag = order['id']
                keyboard.add(types.KeyboardButton(f'{tag}: {data}'))
            keyboard.add(types.KeyboardButton('Назад <-'))
            await state.update_data(tag_selected=message.text.casefold())
            await message.answer('Выбирите нужную заявку.\n'
                                 'Для выбора другого тега нажмите "Назад <-".',
                                 reply_markup=keyboard)
            await States.STATE_FINAL_ADD_ORDERS.set()
        else:
            data = list()
            for order in orders.orders_list.values():
                name = order['n'].lower()
                if name.find(message.text.lower()) != -1:
                    data.append(order)
            if len(data) == 0:
                await message.answer('Нет заявок по вашему запросу')
            else:
                data.sort(key=lambda sort: sort['n'])
                try:
                    for numbers in range(100):
                        keyboard.add(types.KeyboardButton(f'{data[numbers]["id"]}: {data[numbers]["n"]}'))
                except:
                    pass
                keyboard.add(types.KeyboardButton('Назад <-'))
                await message.answer('Выбирите нужные заявки.\n'
                                     'Для нового поиска нажмите "Назад <-".\n'
                                     'Для создания маршрута нажмите "Далее ->"',
                                     reply_markup=keyboard)
                await States.STATE_FINAL_ADD_ORDERS.set()
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
        else:
            await message.answer(f'Я заблокирован пользователем {orders.user_name}')


@dp.message_handler(state=States.STATE_FINAL_ADD_ORDERS, content_types=types.ContentTypes.TEXT)
async def final_add_orders(message: types.Message, state: FSMContext):
    global dp
    if message.from_user.id == orders.user_id:
        user_id = message.from_user.id
        df = pd.read_csv('user.csv', delimiter=',')
        df_user_id = df['user_id'].tolist()
        data = []
        for _ in orders.orders_list.values():
            data.append(_['n'])
        if message.text[message.text.find(':') + 2:] in data:
            data_orders = None
            try:
                id_orders = int(message.text[:message.text.find(':')])
                data_orders = orders.copy_order(id_orders, 1)
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
                            # order['callMode'] = ''
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
                                    dp = data_orders['uid']

                                else:
                                    data_orders['callMode'] = 'update'
                                    #data_orders['p']['r']['vt'] -= _['tm']
                                    '''
                                                                        if data_orders['f'] == 264:
                                        dp2 = list(data_orders['dp'])
                                        dp2.append(dp)
                                        data_orders['dp'] = dp2
                                    '''

                                # data_orders['itemId'] = orders.itemIds
                                order_list.append(data_orders)
                                i += 1

                    exp = exp_calc(order_list, "23:59")
                    params = {
                        "itemId": orders.itemIds,
                        "orders": order_list,
                        "routeId": route_id,
                        "exp": exp,  # здесь указываем, через сколько закрываем маршрут
                        "callMode": "update"
                    }
                    try:

                        response = wialon_api.call('order_route_update', params)
                        await message.answer(f'Заявка "{message.text}" добавлена маршрут',
                                             reply_markup=types.ReplyKeyboardRemove())
                        await state.finish()
                        data.clear()
                        data_orders.clear()
                        orders.user_name = None
                        orders.user_id = None
                    except Exception as e:
                        await message.answer(f'Ошибка: {e.args}',
                                             reply_markup=types.ReplyKeyboardRemove())
                        log.info(f'Ошибка: {e.args}')
                        log.info(f'Params: {params}')
                        await state.finish()
                        data.clear()
                        data_orders.clear()
                        orders.user_name = None
                        orders.user_id = None

            except Exception as e:
                await message.answer(f'Ошибка:  {e.args}')
                await state.finish()
                data.clear()
                data_orders.clear()
                orders.user_name = None
                orders.user_id = None
        elif message.text == 'Назад <-':
            keyboard = loyaut_keyboard_tags()
            await States.STATE_GET_TAG_ADD_ORDERS.set()
            await message.answer('Выбирите тег', reply_markup=keyboard)
        orders.save_time = int(time.time())
    else:
        if int(time.time()) > orders.save_time + delay:
            await state.finish()
            orders.user_name = None
            orders.user_id = None
            await message.answer(f'Введите команду еще рас')
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
