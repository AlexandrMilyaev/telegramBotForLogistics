import datetime
import logging
import os
import sys
import time
import traceback

import requests
from aiogram.dispatcher.filters.state import State, StatesGroup
from wialon import Wialon, WialonError

log = logging.getLogger(os.path.basename(__file__))

comands_types = {
    "/start": "Процедура авторизации",
    "/help": "Описание комант бота",
    "/add_orders": "Добавить заявку в созданый маршрут",
    "/start_route": "Создать новый маршрут",
    "/send_location": "Отправить координаты",
    "/i_am_here": "Добавить метку по прибытию к клиенту. Создаеться новая заявка"

}


class States(StatesGroup):
    STATE_GET_COMMAND = State()
    STATE_GET_TAG = State()
    STATE_GET_ORDERS = State()
    STATE_INITIAL_WAREHOUSE = State()
    STATE_FINAL_WAREHOUSE = State()
    STATE_CREATE_ROUTS = State()

    STATE_GET_NUMBER = State()

    STATE_INITIAL_ADD_ORDERS = State()
    STATE_GET_TAG_ADD_ORDERS = State()
    STARE_GET_ORDERS_ADD_ORDERS = State()
    STATE_FINAL_ADD_ORDERS = State()


def exp_calc(order: list, time_value: str, ceratain=True):
    '''
    Функция для расчета времени до автозавершения маршрута.
    Нужно подставлять в параметр "exp" присоздании/редактировании маршрута
    :param order: список заявок
    :param time: строка в виде "hh:mm"
    :param ceratain: если True, то возвращаеться время от последней заявки до значения time.
    Если False, то возвращаеться значение time в секундах
    :return: Количество секунд.
    '''
    data = time.strptime(time_value, "%H:%M")
    data = datetime.timedelta(hours=data.tm_hour, minutes=data.tm_min).seconds
    if ceratain is True:
        max_vt = 0
        for el in order:
            max_vt = max(max_vt, el['p']['r']['vt'])
        exp = int(time.time())
        exp -= exp % 86400
        exp += data
        if max_vt < exp:
            return exp - max_vt
        else:
            return max_vt
    else:
        return data


def create_order(**kwargs) -> dict:
    time_now = int(time.time())
    params = {
        'id': 0,
        'tf': time_now - (time_now % 86400),
        'tt': time_now - (time_now % 86400) + 86400,
        'r': 100,
        'trt': 3600
    }
    for key, value in kwargs.items():
        if key == 'n':
            params['n'] = value
            params['p'] = {'n': value}
        elif key == 'a':
            params['p']['a'] = value
        elif key == 'p':
            params['p']['p'] = value
        elif key == 'y':
            params['y'] = value
        elif key == 'x':
            params['x'] = value
        elif key == 'f':
            params['f'] = value
        elif key == 'tf':
            params['tf'] = value
        elif key == 'tt':
            params['tt'] = value
        elif key == 'tft':
            params['tft'] = value
        elif key == 'callMode': params['callMode'] = value

    return params


class Orders(Wialon):
    driver_data = dict()
    orders_for_route = dict()
    warehouses_for_route = dict()
    orders_list = dict()
    raw_data = None
    data_by_tags = None
    warehouse = dict()
    orders = None
    user_id = None
    user_name = None
    itemIds = None
    token = None
    save_time = int(time.time())

    def __init__(self, wialon_object, token, **extra_params):
        super().__init__(**extra_params)
        self.wialon_object = wialon_object
        self.token = token
        self.itemIds = self.get_resource_for_orders()

    def get_orders(self):
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
            orders = self.wialon_object.call('core_search_items', params)
            self.orders = orders['items']
        except Exception as e:
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
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
            orders = self.wialon_object.call('core_search_items', params)
            self.orders = orders['items']
        finally:
            tags_key = dict(No_tags='')
            for el in self.orders:
                orders = el['orders']
                for name in orders.values():

                    if name['f'] == 32 and name['p']['r'] is None:

                        try:
                            if name['p']['tags'] == [] or type(name['p']['tags']) == str:
                                tags_value = tags_key.get('No_tags')
                                tags_value = dict(tags_value)
                                tags_value.update({name['id']: name})
                                tags_key['No_tags'] = tags_value
                                self.orders_list.update({name['id']: name})
                            else:
                                for tags in name['p']['tags']:
                                    if tags_key.get(tags) is None:
                                        tags_key.update({tags: ''})
                                        tags_key[tags] = {name['id']: name}
                                        self.orders_list.update({name['id']: name})
                                    else:
                                        tags_value = tags_key.get(tags)
                                        tags_value.update({name['id']: name})
                                        tags_key[tags] = tags_value
                                        self.orders_list.update({name['id']: name})
                        except:
                            print(name)
                            tags_value = tags_key.get('No_tags')
                            tags_value = dict(tags_value)
                            tags_value.update({name['id']: name})
                            tags_key['No_tags'] = tags_value
                            self.orders_list.update({name['id']: name})
                    elif name['f'] & 4 and name['p']['r'] is None:
                        self.warehouse.update({name['id']: name})

        self.data_by_tags = tags_key
        return self.orders

    def craete_route(self, orders_id: list, warehouses: list, driver: int):
        gis = {
            "provider": 1,  # 0-нет, 1-gurtam, 2-google
            "addPoints": 1,  # 0-не возвращать трек, 1-вернуть трек
            "speed": 50  # скорость для оптимизации
        }
        params = {
            "itemId": self.itemIds,
            "orders": orders_id,
            "units": [driver],
            "warehouses": warehouses,
            "criterions": {},
            "flags": 131,
            "gis": gis
        }
        try:
            response = self.wialon_object.call('order_optimize', params)

        except WialonError as e:
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
            response = self.wialon_object.call('order_optimize', params)
        self.get_orders()
        route_id = int(time.time())
        order_list = list()
        order_warehouse = orders_id
        order_warehouse.extend(warehouses)
        try:
            for keys, data in response.items():
                if keys == 'details':
                    pass
                elif keys == 'success':
                    pass
                elif keys == 'summary':
                    pass
                else:
                    i = 0
                    # записываем данные о посещении первой точки. Проверяем на TypeError
                    # Виалон бывает возвращает заявки (orders) в виде списка в списке orders: [[]]
                    try:
                        t_prev = data['orders'][0]['tm']
                    except TypeError:
                        element_orders = data['orders'][0]
                        data['orders'] = element_orders
                        t_prev = data['orders'][0]['tm']
                    ml_prev = 0
                    vt = (route_id % 86400)
                    for _ in data['orders']:
                        data_orders = dict()
                        number = _['id']
                        if type(order_warehouse[number]) is int:
                            data_orders = self.orders[0]['orders'][f'{order_warehouse[number]}']
                            data_orders['f'] = 0
                        elif type(order_warehouse[number]) is dict:
                            data_orders = order_warehouse[number]
                        # if ((route_id + time.altzone) % 86400) >= _['tm']:
                        if ((route_id + 10800) % 86400) >= _['tm']:  # вместо 10800 нужно подставить временную зону
                            # if (route_id % 86400) >= _['tm']:
                            tm = _['tm'] - t_prev
                            ml = _['ml'] - ml_prev
                            vt = vt + tm
                            data_orders['p']['r'] = {
                                "id": route_id,  # id маршрута
                                "i": i,  # порядковый номер (0..)
                                "m": ml,  # пробег с предыдущей точки по плану, м
                                "t": tm,  # время с предыдущей точки по плану, сек
                                "vt": _['tm'],  # время посещения по плану, UNIX_TIME
                                "ndt": 300  # время, за которое должно прийти уведомление, с
                            }
                            t_prev = _['tm']
                            ml_prev = _['ml']
                        else:
                            tm = _['tm'] - t_prev
                            ml = _['ml'] - ml_prev
                            vt = _['tm']
                            data_orders['p']['r'] = {
                                "id": route_id,  # id маршрута
                                "i": i,  # порядковый номер (0..)
                                "m": ml,  # пробег с предыдущей точки по плану, м
                                "t": tm,  # время с предыдущей точки по плану, сек
                                "vt": vt,  # время посещения по плану, UNIX_TIME
                                "ndt": 300  # время, за которое должно прийти уведомление, с
                            }
                            t_prev = _['tm']
                            ml_prev = _['ml']
                        data_orders['u'] = keys
                        data_orders['rp'] = _['p']
                        data_orders['uid'] = 0
                        data_orders['id'] = 0
                        data_orders['st'] = 0
                        data_orders['callMode'] = 'create'
                        order_list.append(data_orders)
                        i += 1
        except WialonError as e:
            log.info(f'Ошибка: {e.args}')

        exp = exp_calc(order_list, "23:59")
        params = {
            "itemId": self.itemIds,
            "orders": order_list,
            "routeId": route_id,
            "exp": exp,
            "callMode": 'create'
        }
        try:
            response = self.wialon_object.call('order_route_update', params)
        except Exception as e:
            log.info(f'Ошибка: {e.args}')
        return response

    def update_route(self, order, driver):
        data_orders = dict()
        orders_route = list()
        data = list()
        route_id = int()
        for key, route in self.orders[0]['order_routes'].items():
            if route['st']['u'] == driver and route['st']['s'] == 1:
                orders_route = route['ord']
                route_id = route['uid']
        if len(orders_route) != 0:
            for key, order_ in self.orders[0]['orders'].items():
                if order_['uid'] in orders_route:
                    # order['callMode'] = ''
                    data.append(order_)
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


            __ = order
            time_now = int(time.time())

            __['tf'] = time_now - (time_now % 86400) - 10800
            __['tt'] = __['tf'] + 86400
            __['f'] = 0
            __['u'] = str(driver)
            __['callMode'] = 'create'
            orders_for_route.append(__)


            gis = {
                "provider": 1,  # 0-нет, 1-gurtam, 2-google
                "addPoints": 1,  # 0-не возвращать трек, 1-вернуть трек
                "speed": 50  # скорость для оптимизации
            }
            params = {
                "itemId": self.itemIds,
                "orders": orders_for_route,
                "units": [driver],
                "warehouses": warehouses_for_route,
                "criterions": {},
                "priority": {driver: {0: 0}},
                "flags": 131,
                "gis": gis
            }

            request = self.wialon_object.call('order_optimize', params)

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
                    # записываем данные о посещении первой точки. Проверяем на TypeError
                    # Виалон бывает возвращает заявки (orders) в виде списка в списке orders: [[]]
                    try:
                        t_prev = data['orders'][0]['tm']
                    except TypeError:
                        element_orders = data['orders'][0]
                        data['orders'] = element_orders
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

                        if data_orders['f'] == 0:
                            data_orders['callMode'] = 'create'
                            data_orders['uid'] = 0
                            data_orders['id'] = 0
                            data_orders['st'] = 0
                            dp = data_orders['uid']

                        else:
                            data_orders['callMode'] = 'update'
                            # data_orders['p']['r']['vt'] -= _['tm']
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
                "itemId": self.itemIds,
                "orders": order_list,
                "routeId": route_id,
                "exp": exp,  # здесь указываем, через сколько закрываем маршрут
                "callMode": "update"
            }

            try:
                response = self.wialon_object.call('order_route_update', params)
                data.clear()
                data_orders.clear()
                return response
            except Exception as e:
                tb = sys.exc_info()[2]
                tbinfo = traceback.format_tb(tb)[0]
                log.error(f'Traceback info:\n{tbinfo}\n{e.args}')
                log.info(f'Params: {params}')
                data.clear()
                data_orders.clear()
                return e.args

    def copy_order(self, id: int, flags: int) -> dict:
        '''
        Функция возвращает копию заявки по id
        :param id: id заявки в Logistics
        :param flags: флаг заявки
        :return: словарь з параметрами заявки
        '''
        data_orders = None
        try:
            data_orders = self.orders_list[id]
        except:
            data_orders = self.warehouse[id]
        finally:
            data_orders['f'] = flags
            time_1 = int(time.time())
            time_1 = time_1 - (time_1 % 86400) - 10800  # вместо 10800 нужно подставить временную зону
            data_orders['tf'] = time_1 + data_orders['tf']
            data_orders['tt'] = time_1 + data_orders['tt']
            return data_orders

    def get_driver(self, phone_number: str):
        """
        :param phone_number: номер телефона , должен совпасть с номером водителя в Wialon
        :return: если номер телефона совпал возврашаем id назначеного обьекта
                если обьект не назначен возвращаеться 0
                если номер телефона не совпал возвращаем None
        """
        spec = {
            "itemsType": "avl_resource",
            "propType": "propitemname",
            "propName": "drivers",
            "propValueMask": "*",
            "sortType": "drivers"
        }
        params = {
            "spec": spec,
            "force": 1,
            "flags": 256,
            "from": 0,
            "to": 0
        }
        response = None
        try:
            response = self.wialon_object.call('core_search_items', params)
        except WialonError:
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
            response = self.wialon_object.call('core_search_items', params)
        finally:
            driver = response['items'][0]['drvrs']
            for _ in driver.values():
                if _['p'][-10:] != '':
                    number = _['p'][-10:]
                    if number == phone_number[-10:]:
                        return _['bu']
        return None

    def get_last_navigation(self, driver):
        params = {
            "id": driver,
            "flags": 1024
        }
        response = None
        try:
            response = self.wialon_object.call('core_search_item', params)
        except WialonError:
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
            response = self.wialon_object.call('core_search_item', params)
        finally:
            return response['item']['pos']

    def get_resource_for_orders(self):
        '''
        :return: функция возвращает id ресурса, в котором нужно создать заявки
        '''
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
        data = self.wialon_object.call('core_search_items', params)
        for el in data['items']:
            if el['uacl'] & 0x600000000:  # Просмотр заявок и его свойств, создание/редактирование/удаление заявок
                return el['id']
        return None

    def import_messages(self, file, unit_id):
        files = {'file': file}
        base_url = 'https://hst-api.wialon.com/wialon/ajax.html?'
        params = {"itemId": unit_id}

        url = base_url + 'svc=exchange/import_messages&params={"itemId":%s}&sid=%s'
        r = requests.post(url % (unit_id, self.wialon_object.sid), files=files)
        return r.text
