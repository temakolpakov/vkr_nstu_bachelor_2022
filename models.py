import datetime

from tortoise.models import Model
from tortoise import fields
from tortoise import Tortoise
import config


class Restaurant(Model):
    """Таблица ресторанов"""
    id = fields.IntField(pk=True)
    restaurant_name = fields.TextField()
    self_id = fields.IntField(null=True)


class Table(Model):
    """Таблица столиков"""
    id = fields.IntField(pk=True)
    restaurant = fields.ForeignKeyField('models.Restaurant', 'table_restaurant')
    table_name = fields.TextField()
    chairs = fields.IntField()
    joint = fields.BooleanField(default=False)
    colnum = fields.TextField()
    colnum_joint = fields.TextField(null=True)


class ActivationCode(Model):
    """Таблица кодов активации для тестов"""
    id = fields.IntField(pk=True)
    code = fields.TextField()


class User(Model):
    """Таблица пользователей"""
    id = fields.IntField(pk=True)
    chat_id = fields.BigIntField()
    name = fields.TextField(null=True)
    phone = fields.TextField(null=True)
    username = fields.TextField(null=True)

    class Meta:
        table = 'user'


class Order(Model):
    """Таблца бронирований"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', 'order_user')
    restaurant = fields.ForeignKeyField('models.Restaurant', 'order_restaurant', null=True)
    table = fields.ForeignKeyField('models.Table', 'order_table', null=True)
    how_many = fields.IntField()
    date = fields.TextField()
    time = fields.TextField()
    remind = fields.IntField(null=True)
    reminded = fields.BooleanField(null=True)
    confirmation_presence = fields.BooleanField(null=True)
    table_range = fields.TextField(null=True)
    table_joint_range = fields.TextField(null=True)


class Tag(Model):
    """Таблца разделов для рассылки"""
    id = fields.IntField(pk=True)
    name = fields.TextField()
    visible = fields.BooleanField(default=True)


class TagSubscription(Model):
    """Таблца подписок на разделы"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', 'subscription_user')
    tag = fields.ForeignKeyField('models.Tag', 'subscription_tag')


class BroadcastModel(Model):
    """Таблца рассылки"""
    id = fields.IntField(pk=True)
    chat_id = fields.BigIntField()
    text = fields.TextField()
    link = fields.JSONField(null=True)
    photo = fields.TextField(null=True)
    video = fields.TextField(null=True)


class BroadcastHistory(Model):
    """Таблца истории рассылок"""
    id = fields.IntField(pk=True)
    tags = fields.JSONField()
    text = fields.TextField()
    link = fields.JSONField(null=True)
    photo = fields.TextField(null=True)
    video = fields.TextField(null=True)
    time = fields.DatetimeField(True)


class AdminChat(Model):
    """Таблца админских чатов"""
    id = fields.IntField(pk=True)
    chat_id = fields.BigIntField()
    restaurant = fields.IntField(null=True)


class AdminSend(Model):
    """Таблца рассылок в админские чаты"""
    id = fields.IntField(pk=True)
    text = fields.TextField()
    restaurant = fields.IntField(null=True)


class OrderToDelete(Model):
    """Таблца бронирований на удаление"""
    id = fields.IntField(pk=True)
    order = fields.ForeignKeyField('models.Order', 'order_to_delete')
    datetime = fields.TextField()


class FileIDs(Model):
    """Таблца связок файла и id"""
    id = fields.IntField(pk=True)
    path = fields.TextField()
    file_id = fields.TextField()


async def get_available_times(restaurant_number, how_many, date):
    """
    Функция поиска свободного времени
    :param restaurant_number: int
    :param how_many: int
    :param date: str
    :return: list( times)
    """
    restaurant = await Restaurant.get(self_id=restaurant_number)
    suitable_tables_ids = await Table.filter(restaurant=restaurant, chairs__gte=how_many).values_list('id', flat=True)
    now = datetime.datetime.now(tz=config.timezone)
    today = False
    if now.strftime('%d.%m') == date:
        today = True
    free_times = config.etalon_times[::]  # для отлинковки
    time_in_advance = '00:00'
    if today:
        now_time = now.strftime('%H:%M')
        time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE)).strftime('%H:%M')
        for i in free_times:
            if i <= time_in_advance:
                free_times[free_times.index(i)] = ''
    orders_date = await Order.filter(restaurant=restaurant,
                                     date=date,
                                     time__gte=time_in_advance,
                                     table_id__in=suitable_tables_ids)
    for j, i in enumerate(free_times):
        if i == '':
            continue
        orders_current_time = [order for order in orders_date if order.time == i]
        tables_busy = []
        tables_joint = []
        for order in orders_current_time:
            table = await order.table
            if not table.joint:
                tables_busy.append(table.id)
            else:
                if table not in tables_joint:
                    tables_joint.append(table)
        for k in tables_joint:
            orders_with_joint = [order.how_many for order in orders_date if order.time == i and order.table_id == k.id]
            if k.chairs - sum(orders_with_joint) < how_many:
                tables_busy.append(k.id)
        if sorted(tables_busy) == suitable_tables_ids:
            for k in range(config.AVERAGE_TIME_VISIT):
                try:
                    free_times[j + k] = ''
                except:
                    pass
    return free_times


async def get_available_tables_with_people(restaurant_number, how_many, date, exact_time):
    """
    Функция поиска свободного времени с количеством свободных мест
    :param restaurant_number: int
    :param how_many: int
    :param date: str
    :param exact_time: str
    :return: list( table_id, table_name, chairs)
    """
    restaurant = await Restaurant.get(self_id=restaurant_number)
    suitable_tables_ids = await Table.filter(restaurant=restaurant, chairs__gte=how_many).values_list('id', flat=True)
    tables_joint = await Table.filter(restaurant=restaurant, chairs__gte=how_many, joint=True).values_list('id',
                                                                                                           flat=True)
    now = datetime.datetime.now(tz=config.timezone)
    today = False
    if now.strftime('%d.%m') == date:
        today = True
    free_times = config.etalon_times[::]  # для отлинковки
    time_in_advance = '00:00'
    if today:
        now_time = now.strftime('%H:%M')
        time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE)).strftime('%H:%M')
        for i in free_times:
            if i <= time_in_advance:
                free_times[free_times.index(i)] = ''
    orders_date = await Order.filter(restaurant=restaurant,
                                     date=date,
                                     table_id__in=suitable_tables_ids)
    to_check = config.etalon_times[max(0, config.etalon_times_dict[exact_time] - config.AVERAGE_TIME_VISIT):
                                   min(len(config.etalon_times),
                                       config.etalon_times_dict[exact_time] + config.AVERAGE_TIME_VISIT)]
    free_tables = []
    for table in suitable_tables_ids:
        if table not in tables_joint:
            orders_table = [order for order in orders_date if order.time in to_check and order.table_id == table]
            if len(orders_table) == 0:
                table_obj = await Table.get(id=table)
                free_tables.append([table, int(table_obj.table_name), table_obj.chairs])
        else:
            orders_table_how_many = [order.how_many for order in orders_date if order.time in to_check and order.table_id == table]
            table_obj = await Table.get(id=table)
            if len(orders_table_how_many) == 0 or table_obj.chairs - sum(orders_table_how_many) >= how_many:
                free_tables.append([table, int(table_obj.table_name), table_obj.chairs - sum(orders_table_how_many)])

    return free_tables


async def init():
    await Tortoise.init(
        config.TORTOISE_ORM
    )
    await Tortoise.generate_schemas()
