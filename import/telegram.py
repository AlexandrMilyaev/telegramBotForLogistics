
from aiogram.dispatcher.filters.state import State, StatesGroup
from wialon import Wialon, WialonError
import time

comands_types = {
    "/start": "Процедура авторизации",
    "/help": "Описание комант бота",
    "/add_orders": "Добавить заявку в созданый маршрут",
    "/start_route": "Создать новый маршрут"
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


class Orders(Wialon):
    orders_for_route = dict()
    warehouses_for_route = dict()
    orders_list = dict()
    raw_data = None
    data_by_tags = None
    warehouse = dict()
    orders = None
    user_id = None
    user_name = None
    itemIds = 22403020
    token = None
    save_time = int(time.time())

    def __init__(self, wialon_object, token,  **extra_params):
        super().__init__(**extra_params)
        self.wialon_object = wialon_object
        self.token = token
        print(self.token)

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
            tags_key = dict(No_tags='')
            for el in self.orders:
                orders = el['orders']
                for name in orders.values():
                    if name['f'] == 32 and name['p']['r'] is None:
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
                    elif name['f'] & 4 and name['p']['r'] is None:
                        self.warehouse.update({name['id']: name})
                        print(name)

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
            print(e.args)
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
                    t_prev = data['orders'][0]['tm']
                    ml_prev = 0
                    vt = (route_id % 86400)
                    for _ in data['orders']:
                        data_orders = dict()
                        number = _['id']
                        if type(order_warehouse[number]) is int:
                            data_orders = self.orders[0]['orders'][f'{order_warehouse[number]}']
                            data_orders['f'] = 1
                        elif type(order_warehouse[number]) is dict:
                            data_orders = order_warehouse[number]
                        # if ((route_id + time.altzone) % 86400) >= _['tm']:
                        if ((route_id + 10800) % 86400) >= _['tm']: # вместо 10800 нужно подставить временную зону
                        #if (route_id % 86400) >= _['tm']:
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
            print(e.args)

        params = {
            "itemId": self.itemIds,
            "orders": order_list,
            "routeId": route_id,
            "callMode": 'create'
        }
        try:
            response = self.wialon_object.call('order_route_update', params)
        except Exception as e:
            print(e.args)
        return response

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
