from aiogram import types
from aiogram.dispatcher import FSMContext

from booking_admin import *
from admin_funcs import *
from keyboards import ru_keyboards_admin as kb
from buttons import ru_buttons as btns
from states_admin import *


# @dp.message_handler(text=btns.back, state=Broadcast.text)
async def back_to_admin_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message, state)


# @dp.message_handler(text=btns.back, state=Broadcast.next_step)
async def back_to_broadcast_text(message: types.Message, state: FSMContext):
    await Broadcast.tags.set()
    await state.update_data(tags=[])
    await broadcast_menu(message, state)


# @dp.message_handler(text=btns.back, state=Broadcast.attachment)
async def back_to_broadcast_next_step(message: types.Message, state: FSMContext):
    await Broadcast.next_step.set()
    await broadcast_text_handler2(message, state)


# @dp.message_handler(text=btns.back, state=Broadcast.attachment2)
async def back_to_broadcast_atach(message: types.Message, state: FSMContext):
    cur_atachments = (await state.get_data()).get('attachment')
    if len(cur_atachments['links']):
        if len(cur_atachments['links'][-1]) != 2:
            cur_atachments['links'].pop(-1)
    await state.update_data(attachment=cur_atachments)
    await Broadcast.next_step.set()
    await broadcast_text_handler2(message, state)


# @dp.message_handler(text=btns.back, state=Broadcast.conf_)
# @dp.message_handler(text=btns.back, state=Broadcast.tags)
async def back_to_broadcast_next_step2(message: types.Message, state: FSMContext):
    await Broadcast.next_step.set()
    await broadcast_text_handler2(message, state)


# @dp.message_handler(text=btns.back, state=AddTag.name)
# @dp.message_handler(text=btns.back, state=DelTag.name)
async def back_to_tags_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await admin_tags2(message, state)


# @dp.message_handler(text=btns.back, state=DelTag.confirmation)
async def back_to_del_tags(message: types.Message, state: FSMContext):
    await DelTag.name.set()
    await del_tag2(message)


# @dp.message_handler(text=btns.back, state=BroadcastHistoryStates.tags)
async def back_to_start(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message, state)


# @dp.message_handler(text=btns.back, state=BroadcastHistoryStates.id)
# @dp.message_handler(text=btns.back, state=BroadcastHistoryStates.wait)
async def back_to_broadcast_history(message: types.Message, state: FSMContext):
    await BroadcastHistoryStates.tags.set()
    await state.update_data(tags=[])
    await broadcast_history(message, state, False)


# @dp.message_handler(text=btns.back, state=Booking.restaurant)
async def back_to_main(message: types.Message, state: FSMContext):
    await start(message, state)


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


# @dp.message_handler(text=btns.back, state=Booking.confirmation)
async def back_to_tables(message: types.Message, state: FSMContext):
    await Booking.previous()
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


# @dp.message_handler(text=btns.back)
async def back_to_admin_menu2(message: types.Message):
    await set_message_id(message)
    await start(message, None)
