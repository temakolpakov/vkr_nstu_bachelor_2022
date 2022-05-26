from booking import *
from settings_handlers import *
from buttons import ru_buttons as btns
from messages import ru_messages as msgs
import datetime

from bot_setup import dp
from states import *


# @dp.message_handler(text=btns.back, state=Booking.restaurant)
async def back_to_main(message: types.Message, state: FSMContext):
    await settings_(message, state)


# @dp.message_handler(text=btns.back, state=Booking.how_many)
async def back_to_restaurants(message: types.Message, state: FSMContext):
    how_many = (await state.get_data()).get('how_many')
    if how_many == 'bigger_number':
        await state.update_data(how_many=None)
        await rechose_how_many(message, state)
    else:
        await start(message, state, back_flag=True)


# @dp.message_handler(text=btns.back, state=Booking.date_booking)
async def back_to_how_many(message: types.Message, state: FSMContext):
    date_booking = (await state.get_data()).get('date_booking')
    if date_booking == 'later':
        await state.update_data(date_booking=None)
        await rechose_date_booking(message, state)
    else:
        await Booking.previous()
        await rechose_how_many(message, state)


# @dp.message_handler(text=btns.back, state=Booking.approximate_time)
async def back_to_date_booking(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_date_booking(message, state)


# @dp.message_handler(text=btns.back, state=Booking.exact_time)
async def back_to_approximate_time(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_approximate_time(message, state)


# @dp.message_handler(text=btns.back, state=Booking.table)
async def back_to_exact_time(message: types.Message, state: FSMContext):
    table = (await state.get_data()).get('table')
    await state.update_data(table=msgs.yes_no)
    if table == msgs.not_important or table == msgs.yes_no or table is None:
        await Booking.previous()
        await rechose_exact_time(message, state)
    else:
        await rechoose_table_yes_no(message, state)


# @dp.message_handler(text=btns.back, state=Booking.confirm_table)
async def back_to_tables2(message: types.Message, state: FSMContext):
    await Booking.table.set()
    await rechose_table(message, state)


# @dp.message_handler(text=btns.back, state=Booking.confirmation)
async def back_to_tables(message: types.Message, state: FSMContext):
    await Booking.table.set()
    table = (await state.get_data()).get('table')
    if table == msgs.not_important:
        await state.update_data(table=msgs.yes_no)
        await rechoose_table_yes_no(message, state)
    else:
        await rechose_table(message, state)


# @dp.message_handler(text=btns.back, state=Booking.name)
async def back_to_confirmation(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_confirm(message, state)


# @dp.message_handler(text=btns.back, state=Booking.phone)
async def back_to_name(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_name(message, state)


# @dp.message_handler(text=btns.back, state=Booking.final)
async def back_to_confirmation2(message: types.Message, state: FSMContext):
    await Booking.confirmation.set()
    await rechose_confirm(message, state)


# @dp.message_handler(text=btns.back, state=Booking.remind)
async def back_to_confirmation3(message: types.Message, state: FSMContext):
    await Booking.confirmation.set()
    await rechose_confirm(message, state)


# @dp.message_handler(text=btns.back, state=Changing.name)
# @dp.message_handler(text=btns.back, state=Changing.phone)
async def back_to_change_contact(message: types.Message, state: FSMContext):
    await state.finish()
    await settings_menu(message, state)


# @dp.message_handler(text=btns.confirm_choise, state=ChangeTags.tag)
# @dp.message_handler(text=btns.back, state=ChangeTags.tag)
async def back_to_tags2(message: types.Message, state: FSMContext):
    await state.finish()
    await change_tag3(message, state)


# @dp.message_handler(text=btns.back, state=Settings.change_contact)
# @dp.message_handler(text=btns.back, state=Settings.change_tag)
async def back_to_main_settings(message: types.Message, state: FSMContext):
    await state.finish()
    await settings(message, state)


# @dp.message_handler(text=btns.back)
async def back_to_menu(message: types.Message):
    await settings(message, dp.current_state())


# @dp.message_handler(text=btns.back_to_menu)
# @dp.message_handler(text=btns.back_to_menu, state=Changing)
async def settings_(message: types.Message, state: FSMContext):
    if not state:
        state = dp.current_state()
    else:
        await state.finish()
    await settings(message, state)


# @dp.message_handler(text=btns.back_to_settings)
# @dp.message_handler(text=btns.back_to_settings, state=Changing)
async def settings2_(message: types.Message, state: FSMContext):
    if not state:
        state = dp.current_state()
    else:
        await state.finish()
    await settings_menu(message, state)
