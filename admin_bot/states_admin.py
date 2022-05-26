from aiogram.dispatcher.filters.state import State, StatesGroup


class AddTag(StatesGroup):
    name = State()


class DelTag(StatesGroup):
    name = State()
    confirmation = State()


class Broadcast(StatesGroup):
    text = State()
    next_step = State()
    attachment = State()
    attachment2 = State()
    conf_ = State()
    tags = State()
    confirmation = State()


class BroadcastHistoryStates(StatesGroup):
    tags = State()
    id = State()
    wait = State()


class Booking(StatesGroup):
    restaurant = State()
    how_many = State()
    date_booking = State()
    approximate_time = State()
    exact_time = State()
    table = State()
    confirmation = State()
    name = State()
    phone = State()
    final = State()
    remind = State()

class DelBooking(StatesGroup):
    id = State()
    confirmation = State()