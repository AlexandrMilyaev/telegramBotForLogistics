from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.dispatcher.filters.state import State, StatesGroup
from wialon import Wialon, WialonError
import time

comands_types = {
    "/start": "Процедура авторизации",
    "/help": "Описание комант бота",
    "/add_orders": "Добавить заявку в созданый маршрут",
    "/start_route": "Создать новый маршрут",
    "/test": "Это просто для теста"
}


class States(StatesGroup):
    STATE_GET_COMMAND = State()
    STATE_GET_TAG = State()
    STATE_GET_ORDERS = State()
    STATE_CREATE_ROUTS = State()

    STATE_GET_NUMBER = State()


class Orders(Wialon):
    orders_for_route = dict()
    orders_list = dict()
    raw_data = None
    data_by_tags = None
    orders = None
    user_id = None
    itemIds = 22403020

    def __init__(self, wialon_object, **extra_params):
        super().__init__(**extra_params)
        self.wialon_object = wialon_object

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
        except WialonError as e:
            print(e.args)
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
            tags_value = list()
            tags_key = dict(No_tags='')
            for el in self.orders:
                orders = el['orders']
                for name in orders.values():
                    if name['f'] == 32:
                        if name['p']['tags'] == [] or type(name['p']['tags']) == str:
                            tags_value = tags_key.get('No_tags')
                            tags_value = dict(tags_value)
                            tags_value.update({name['id']: name['n']})
                            tags_key['No_tags'] = tags_value
                            self.orders_list.update({name['id']: name['n']})
                        else:
                            for tags in name['p']['tags']:
                                if tags_key.get(tags) is None:
                                    tags_key.update({tags: ''})
                                    tags_key[tags] = {name['id']: name['n']}
                                    self.orders_list.update({name['id']: name['n']})
                                else:
                                    tags_value = tags_key.get(tags)
                                    tags_value.update({name['id']: name['n']})
                                    tags_key[tags] = tags_value
                                    self.orders_list.update({name['id']: name['n']})

        self.data_by_tags = tags_key
        return self.orders

    def craete_route(self, orders_id: list, driver: int):
        gis = {
            "provider": 1,  # 0-нет, 1-gurtam, 2-google
            "addPoints": 1,  # 0-не возвращать трек, 1-вернуть трек
            "speed": 50  # скорость для оптимизации
        }
        params = {
            "itemId": self.itemIds,
            "orders": orders_id,
            "units": [driver],
            "warehouses": [],
            "criterions": {},
            "flags": 3,
            "gis": gis
        }
        try:
            response = self.wialon_object.call('order_optimize', params)
        except WialonError as e:
            print(e.args)
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
            response = self.wialon_object.call('order_optimize', params)
        self.get_orders()
        route_id = int(time.time())
        order_list = list()
        try:
            for keys, data in response.items():
                if keys == 'details':
                    pass
                elif keys == 'success':
                    pass
                elif keys == 'summary':
                    pass
                else:
                    vt = route_id
                    i = 0
                    for _ in data['orders']:
                        number = _['id']
                        vt += _['tm']
                        data_orders = self.orders[0]['orders'][f'{orders_id[number]}']
                        data_orders['f'] = 1
                        data_orders['p']['r'] = {
                            "id": route_id,  # id маршрута
                            "i": i,  # порядковый номер (0..)
                            "m": _['ml'],  # пробег с предыдущей точки по плану, м
                            "t": _['tm'],  # время с предыдущей точки по плану, сек
                            "vt": vt,  # время посещения по плану, UNIX_TIME
                            "ndt": 300  # время, за которое должно прийти уведомление, с
                        }
                        data_orders['u'] = keys
                        data_orders['rp'] = _['p']
                        data_orders['uid'] = 0
                        data_orders['id'] = 0
                        data_orders['st'] = 0
                        time_modul = route_id % 86400
                        time_modul = route_id - time_modul + time.altzone
                        data_orders['tt'] = time_modul + 86400
                        data_orders['tf'] = time_modul
                        data_orders['callMode'] = 'create'

                        i += 1
                        order_list.append(data_orders)
        except WialonError as e:
            print(e.args)

        params = {
            "itemId": self.itemIds,
            "orders": order_list,
            "routeId": route_id,
            "callMode": 'create'
        }
        response = self.wialon_object.call('order_route_update', params)
        return response

    def get_driver(self, phone_number: str):
        '''

        :param phone_number: номер телефона , должен совпасть с номером водителя в Wialon
        :return: если номер телефона совпал возврашаем id назначеного обьекта
                если обьект не назначен возвращаеться 0
                если номер телефона не совпал возвращаем None
        '''
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
        try:
            response = self.wialon_object.call('core_search_items', params)

        except WialonError as e:
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
            response = self.wialon_object.call('core_search_items', params)

        driver = response['items'][0]['drvrs']
        for _ in driver.values():
            if _['p'][-10:] != '':
                number = _['p'][-10:]
                if number == phone_number[-10:]:
                    return _['bu']
        return None


'''
        try:
            spec = {
                "itemsType": "avl_unit",
                "propType": "property",
                "propName": "sys_name",
                "propValueMask": "*",
                "sortType": "sys_name"
            }
            params = {
                "spec": spec,
                "force": 1,
                "flags": 1,
                "from": 0,
                "to": 0
            }
            response = self.wialon_object.call('core_search_items', params)
            return response
        except WialonError as e:
            spec = {
                "itemsType": "avl_unit"
            }
            params = {
                "spec": spec,
                "force": 1,
                "flags": 1,
                "from": 0,
                "to": 0
            }
            res = self.wialon_object.token_login(token=self.token)
            self.wialon_object.sid = res['eid']
            response = self.wialon_object.call('core_search_items', params)
            print(e.args)
            return response

'''
