from aiogram.utils.helper import Helper, HelperMode, ListItem
from wialon import Wialon, WialonError

comands_types = {
    "/start": "Приветствие",
    "/help": "Описание комант бота",
    "/get_orders": "Получить список всех доступных заявок",
    "/start_route": "Начало маршрута"
}


class States(Helper):
    mode = HelperMode.snake_case

    STATE_GET_COMMAND = ListItem()
    STATE_CREATE_ROUTS = ListItem()


class Orders(Wialon):
    raw_data = None
    data_by_tags = None
    orders = None

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
            self.data_by_tags = tags_key
        return self.orders
