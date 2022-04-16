from aiogram.dispatcher.filters.state import State, StatesGroup


class Booking(StatesGroup):
    restaurant = State()
    how_many = State()
    date_booking = State()
    approximate_time = State()
    exact_time = State()
    table = State()
    confirm_table = State()
    confirmation = State()
    name = State()
    phone = State()
    final = State()
    remind = State()


class Changing(StatesGroup):
    name = State()
    phone = State()


class AddTag(StatesGroup):
    name = State()


class DelTag(StatesGroup):
    name = State()


class Settings(StatesGroup):
    change_contact = State()
    change_tag = State()


class ChangeTags(StatesGroup):
    tag = State()
