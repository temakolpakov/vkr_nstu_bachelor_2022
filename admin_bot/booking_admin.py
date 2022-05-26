import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

import config
from admin_bot.admin_funcs import settings
from bot_admin_setup import bot
from config import admins
from helpers_dir.google_sheet_functions import create_order, create_order_without_table
from helpers_dir.helpers import reformat_times, safe_for_markdown, is_phone_valid
from helpers_dir.img_helper import get_colored_image
from keyboards import ru_keyboards_admin as kb
from buttons import ru_buttons as btns
from messages import ru_messages_admin as msgs
from middlewares.answercallback_middleware import set_message_id
from models import get_available_times, get_available_tables_with_people, Table, Restaurant, Order, AdminSend, User
from states_admin import *



# # @dp.message_handler(commands='start', state='*')
async def start(message: types.Message, state: FSMContext, back_flag=False):
    if message.chat.id in admins:
        await message.answer(msgs.you_are_admin.format(config.BOT_NAME), reply_markup=await kb.admin_keyboard())
        return


# @dp.message_handler(text=btns.new_booking, state='*')
async def new_booking(message: types.Message, state: FSMContext, back_flag=False, start_booking_again=False):
    if not back_flag:
        if await state.get_data() != {}:
            await state.finish()

    await Booking.restaurant.set()
    msg_text = msgs.choose_address

    msg_id = await message.answer(msg_text, reply_markup=await kb.restaurants_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains=['restaurant_'], state=Booking.restaurant)
async def chosen_restaurant(query: CallbackQuery, state: FSMContext):
    restaurant_number = int(query.data.split('_')[1])

    if restaurant_number == 1:
        msg_text = msgs.restaurant_1
    elif restaurant_number == 2:
        msg_text = msgs.restaurant_2
    elif restaurant_number == 3:
        msg_text = msgs.restaurant_3
    else:
        await query.message.answer(msgs.something_wrong)
        return
    await state.update_data(restaurant=restaurant_number)
    await Booking.next()
    await query.message.edit_reply_markup(reply_markup=await kb.edit_restaurants_keyboard(restaurant_number))
    await query.message.answer(msg_text, reply_markup=await kb.booking_keyboard(), parse_mode=types.ParseMode.MARKDOWN_V2)

    msg_id = await query.message.answer(msgs.how_many, reply_markup=await kb.how_many_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains=['how_many_'], state=Booking.how_many)
async def chosen_how_many(query: CallbackQuery, state: FSMContext):
    how_many = int(query.data.split('_')[2])
    await state.update_data(how_many=how_many)
    await Booking.next()
    now = datetime.datetime.now(tz=config.timezone)
    today = now.strftime('%d.%m.%Y')
    tomorrow = (now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    day_after_tomorrow = (now + datetime.timedelta(days=2)).strftime('%d.%m.%Y')
    today_cut = now.strftime('%d.%m')
    tomorrow_cut = (now + datetime.timedelta(days=1)).strftime('%d.%m')
    day_after_tomorrow_cut = (now + datetime.timedelta(days=2)).strftime('%d.%m')

    await query.message.edit_reply_markup(reply_markup=await kb.edit_how_many_keyboard(how_many))
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    msg_id = await query.message.answer(msgs.choose_date,
                                        reply_markup=await kb.date_booking_keyboard(today_cut, tomorrow_cut, today,
                                                                                    tomorrow, day_after_tomorrow_cut,
                                                                                    day_after_tomorrow))
    await set_message_id(msg_id)


async def rechose_how_many(message: types.Message, state: FSMContext):
    restaurant_number = (await state.get_data()).get('restaurant')
    if restaurant_number == 1:
        msg_text = msgs.restaurant_1
    elif restaurant_number == 2:
        msg_text = msgs.restaurant_2
    elif restaurant_number == 3:
        msg_text = msgs.restaurant_3
    else:
        await message.answer(msgs.something_wrong)
        return
    await state.update_data(restaurant=restaurant_number)
    await message.answer(msg_text, parse_mode=types.ParseMode.MARKDOWN_V2)
    msg_id = await message.answer(msgs.how_many, reply_markup=await kb.how_many_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='bigger_number', state=Booking.how_many)
async def bigger_number(query: CallbackQuery, state: FSMContext):
    await state.update_data(how_many='bigger_number')
    await query.message.edit_reply_markup(await kb.bigger_number_how_many_keyboard())
    msg_id = await query.message.answer(
        msgs.for_bigger_number.format(config.PHONES[(await state.get_data()).get('restaurant')]),
        reply_markup=await kb.back_to_menu2_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='back_to_menu2', state=Booking.how_many)
async def back_to_menu2(query: CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.answer(msgs.main_menu, reply_markup=await kb.admin_keyboard())


async def rechose_date_booking(message: types.Message, state: FSMContext):
    date_booking = (await state.get_data()).get('date_booking')
    now = datetime.datetime.now(tz=config.timezone)
    today = now.strftime('%d.%m.%Y')
    tomorrow = (now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    day_after_tomorrow = (now + datetime.timedelta(days=2)).strftime('%d.%m.%Y')
    today_cut = now.strftime('%d.%m')
    tomorrow_cut = (now + datetime.timedelta(days=1)).strftime('%d.%m')
    day_after_tomorrow_cut = (now + datetime.timedelta(days=2)).strftime('%d.%m')

    msg_id = await message.answer(msgs.choose_date,
                                  reply_markup=await kb.date_booking_keyboard(today_cut, tomorrow_cut, today, tomorrow,
                                                                              day_after_tomorrow_cut,
                                                                              day_after_tomorrow))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains=['date_booking_'], state=Booking.date_booking)
async def chosen_date_booking(query: CallbackQuery, state: FSMContext):
    date_booking = query.data.split('_')[2]
    if date_booking == 'later':
        await date_booking_later(query, state)
        return
    new_date = ''
    if len(date_booking.split('.')[0]) == 1:
        new_date += '0' + date_booking.split('.')[0]
    else:
        new_date += date_booking.split('.')[0]
    new_date += '.'
    if len(date_booking.split('.')[1]) == 1:
        new_date += '0' + date_booking.split('.')[1]
    else:
        new_date += date_booking.split('.')[1]
    date_booking = new_date
    d = datetime.datetime.strptime(query.data.split('_')[2], '%d.%m.%Y')
    await state.update_data(date_booking=date_booking)
    await Booking.next()

    now = datetime.datetime.now(tz=config.timezone)
    today = now.strftime('%d.%m')
    tomorrow = (now + datetime.timedelta(days=1)).strftime('%d.%m')
    day_after_tomorrow = (now + datetime.timedelta(days=2)).strftime('%d.%m')
    if 'cal' in query.data:
        selected = date_booking
        keyboard = await kb.generate_calendar(d.year, d.month, d.day, now, config.DAYS_FOR_BOOKING, selected,
                                              delete_empty=True)
    else:

        if date_booking in [today, tomorrow, day_after_tomorrow]:
            keyboard = await kb.chosen_date_booking_keyboard(date_booking, today, tomorrow, day_after_tomorrow)
        else:
            selected = date_booking
            keyboard = await kb.generate_calendar(d.year, d.month, d.day, now, config.DAYS_FOR_BOOKING, selected,
                                                  delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)

    approximate_times = [['с 9 до 12', '9-12'], ['c 12 до 14', '12-14'], ['с 14 до 16', '14-16'],
                         ['с 16 до 18', '16-18'], ['с 18 до 20', '18-20'], ['с 20 до 22', '20-22']]
    now = datetime.datetime.now(tz=config.timezone)
    day_now = now.strftime('%d.%m')
    time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE))
    time_in_advance_str = time_in_advance.strftime('%H:%M')
    if day_now == date_booking:
        for j, i in enumerate(approximate_times):
            if time_in_advance.hour >= int(i[1].split('-')[1]):
                approximate_times[j] = [' ', 'pass']
            elif (now - datetime.timedelta(minutes=15)) >= datetime.datetime(now.year, now.month, now.day,
                                                                             int(i[1].split('-')[1]) - 1, 45, 0, 0,
                                                                             config.timezone):
                approximate_times[j] = [' ', 'pass']

    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    time_available = await get_available_times(restaurant_number, how_many, date_booking)
    if time_available != True:
        for j, i in enumerate(approximate_times):
            if i[1] == 'pass':
                continue
            bottom = int(i[1].split('-')[0])
            upper = int(i[1].split('-')[1])
            time_intervals = sum([[str(k)] * 4 for k in range(bottom, upper)], [])
            for k, l in enumerate(time_intervals):
                if len(l) == 1:
                    time_intervals[k] = '0' + l
            time_00 = [i + ':00' for i in time_intervals[::4]]
            time_15 = [i + ':15' for i in time_intervals[1::4]]
            time_30 = [i + ':30' for i in time_intervals[2::4]]
            time_45 = [i + ':45' for i in time_intervals[3::4]]

            time_00, time_15, time_30, time_45 = await reformat_times(time_available,
                                                                      [time_00, time_15, time_30, time_45])
            f = False
            for k in [time_00, time_15, time_30, time_45]:
                for l in k:
                    if l != ' ':
                        f = True
            if not f:
                approximate_times[j] = [' ', 'pass']
    if all([' ' == i[0] for i in approximate_times[:3]]) and \
            all([' ' == i[0] for i in approximate_times[3:]]):
        await query.message.answer(msgs.sorry_not_available_times)
        await Booking.date_booking.set()
        await rechose_date_booking(query.message, state)
        return
    msg_id = await query.message.answer(await safe_for_markdown(msgs.approximate_time),
                                        parse_mode=types.ParseMode.MARKDOWN_V2,
                                        reply_markup=await kb.approximate_time_keyboard(approximate_times))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='date_booking_later', state=Booking.date_booking)
async def date_booking_later(query: CallbackQuery, state: FSMContext):
    await state.update_data(date_booking='later')
    now = datetime.datetime.now(tz=config.timezone)
    keyboard = await kb.generate_calendar(now.year, now.month, now.day, now, config.DAYS_FOR_BOOKING, delete_empty=True)
    await query.message.edit_reply_markup(keyboard)


# @dp.callback_query_handler(text_contains=['approximate_time_'], state=Booking.approximate_time)
async def chosen_approximate_time(query: CallbackQuery, state: FSMContext):
    approximate_time = query.data.split('_')[2]
    if approximate_time == 'pass':
        return
    await state.update_data(approximate_time=approximate_time)
    await Booking.next()

    approximate_times = ['9-12', '12-14', '14-16', '16-18', '18-20', '20-22']
    approximate_times_full = [['с 9 до 12', '9-12'], ['c 12 до 14', '12-14'], ['с 14 до 16', '14-16'],
                              ['с 16 до 18', '16-18'], ['с 18 до 20', '18-20'], ['с 20 до 22', '20-22']]
    approximate_times_full[approximate_times.index(approximate_time)][0] = btns.check_mark + approximate_times_full[
        approximate_times.index(approximate_time)][0]
    now = datetime.datetime.now(tz=config.timezone)
    day_now = now.strftime('%d.%m')
    date_booking = (await state.get_data()).get('date_booking')
    if day_now == date_booking:
        for j, i in enumerate(approximate_times_full):
            if now.hour + 1 >= int(i[1].split('-')[1]):
                approximate_times_full[j] = [' ', 'pass']
            elif (now - datetime.timedelta(minutes=15)) >= datetime.datetime(now.year, now.month, now.day,
                                                                             int(i[1].split('-')[1]) - 1, 45, 0, 0,
                                                                             config.timezone):
                approximate_times_full[j] = [' ', 'pass']
    for i in range(len(query.message.reply_markup.inline_keyboard[0])):
        if query.message.reply_markup.inline_keyboard[0][i]['text'] == ' ':
            approximate_times_full[i] = [' ', 'pass']
    for i in range(len(query.message.reply_markup.inline_keyboard[1])):
        if query.message.reply_markup.inline_keyboard[1][i]['text'] == ' ':
            approximate_times_full[i + 3] = [' ', 'pass']

    await query.message.edit_reply_markup(reply_markup=await kb.approximate_time_keyboard(approximate_times_full))
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    bottom = int(approximate_time.split('-')[0])
    upper = int(approximate_time.split('-')[1])
    time_intervals = sum([[str(i)] * 4 for i in range(bottom, upper)], [])
    for i, j in enumerate(time_intervals):
        if len(j) == 1:
            time_intervals[i] = '0' + j
    time_00 = [i + ':00' for i in time_intervals[::4]]
    time_15 = [i + ':15' for i in time_intervals[1::4]]
    time_30 = [i + ':30' for i in time_intervals[2::4]]
    time_45 = [i + ':45' for i in time_intervals[3::4]]
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    time_available = await get_available_times(restaurant_number, how_many, date_booking)
    if time_available != True:
        time_00, time_15, time_30, time_45 = await reformat_times(time_available, [time_00, time_15, time_30, time_45])

    msg_id = await query.message.answer(await safe_for_markdown(msgs.exact_time),
                                        parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=await kb.exact_time_keyboard(time_00, time_15, time_30, time_45))
    await set_message_id(msg_id)


async def rechose_approximate_time(message: types.Message, state: FSMContext):
    approximate_times = ['9-12', '12-14', '14-16', '16-18', '18-20', '20-22']
    approximate_times_full = [['с 9 до 12', '9-12'], ['c 12 до 14', '12-14'], ['с 14 до 16', '14-16'],
                              ['с 16 до 18', '16-18'], ['с 18 до 20', '18-20'], ['с 20 до 22', '20-22']]
    approximate_time = (await state.get_data()).get('approximate_time')

    now = datetime.datetime.now(tz=config.timezone)
    day_now = now.strftime('%d.%m')
    date_booking = (await state.get_data()).get('date_booking')
    time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE))
    time_in_advance_str = time_in_advance.strftime('%H:%M')
    if day_now == date_booking:
        for j, i in enumerate(approximate_times_full):
            if time_in_advance.hour >= int(i[1].split('-')[1]):
                approximate_times_full[j] = [' ', 'pass']
            elif (now - datetime.timedelta(minutes=15)) >= datetime.datetime(now.year, now.month, now.day,
                                                                             int(i[1].split('-')[1]) - 1, 45, 0, 0,
                                                                             config.timezone):
                approximate_times[j] = [' ', 'pass']
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    time_available = await get_available_times(restaurant_number, how_many, date_booking)
    if time_available != True:
        for j, i in enumerate(approximate_times_full):
            if i[1] == 'pass' or i[1]:
                continue
            bottom = int(i[1].split('-')[0])
            upper = int(i[1].split('-')[1])
            time_intervals = sum([[str(k)] * 4 for k in range(bottom, upper)], [])
            for k, l in enumerate(time_intervals):
                if len(l) == 1:
                    time_intervals[k] = '0' + l
            time_00 = [i + ':00' for i in time_intervals[::4]]
            time_15 = [i + ':15' for i in time_intervals[1::4]]
            time_30 = [i + ':30' for i in time_intervals[2::4]]
            time_45 = [i + ':45' for i in time_intervals[3::4]]

            time_00, time_15, time_30, time_45 = await reformat_times(time_available,
                                                                      [time_00, time_15, time_30, time_45])
            f = False
            for k in [time_00, time_15, time_30, time_45]:
                for l in k:
                    if l != ' ':
                        f = True
            if not f:
                approximate_times_full[j] = [' ', 'pass']

    msg_id = await message.answer(await safe_for_markdown(msgs.approximate_time),
                                  parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=await kb.approximate_time_keyboard(approximate_times_full))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains=['exact_time_'], state=Booking.exact_time)
async def chosen_exact_time(query: CallbackQuery, state: FSMContext):
    exact_time = query.data.split('_')[2]
    if exact_time == ' ':
        return
    now = datetime.datetime.now(tz=config.timezone)
    now_time = now.strftime('%H:%M')
    time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE)).strftime('%H:%M')
    if now.strftime('%d.%m') == (await state.get_data()).get('date_booking') and exact_time <= time_in_advance:
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        if now.hour >= int((await state.get_data()).get('approximate_time').split('-')[1]) - 1:
            await Booking.approximate_time.set()
            await rechose_approximate_time(query.message, state)
            return
        await Booking.exact_time.set()
        await rechose_exact_time(query.message, state)
        return
    # elif now.strftime('%d.%m') > (await state.get_data()).get('date_booking'):
    elif now.strftime('%m.%d') > '.'.join([(await state.get_data()).get('date_booking').split('.')[1],
                                           (await state.get_data()).get('date_booking').split('.')[0]]):
        await Booking.date_booking.set()
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        await rechose_date_booking(query.message, state)
        return
    await state.update_data(exact_time=exact_time)
    await Booking.next()

    approximate_time = (await state.get_data()).get('approximate_time')
    bottom = int(approximate_time.split('-')[0])
    upper = int(approximate_time.split('-')[1])
    time_intervals = sum([[str(i)] * 4 for i in range(bottom, upper)], [])
    for i, j in enumerate(time_intervals):
        if len(j) == 1:
            time_intervals[i] = '0' + j
    time_00 = [i + ':00' for i in time_intervals[::4]]
    time_15 = [i + ':15' for i in time_intervals[1::4]]
    time_30 = [i + ':30' for i in time_intervals[2::4]]
    time_45 = [i + ':45' for i in time_intervals[3::4]]
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    time_available = await get_available_times(restaurant_number, how_many, date_booking)
    if time_available != True:
        time_00, time_15, time_30, time_45 = await reformat_times(time_available, [time_00, time_15, time_30, time_45])

    for i in [time_00, time_15, time_30, time_45]:
        if exact_time in i:
            i[i.index(exact_time)] = btns.check_mark + i[i.index(exact_time)]
    await query.message.edit_reply_markup(reply_markup=await kb.exact_time_keyboard(time_00, time_15, time_30, time_45))
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    # await state.update_data(table=msgs.yes_no)

    msg_id = await query.message.answer(msgs.want_choose_table, reply_markup=await kb.choose_table_keyboard())
    await set_message_id(msg_id)


async def rechose_exact_time(message: types.Message, state: FSMContext):
    approximate_time = (await state.get_data()).get('approximate_time')
    exact_time = (await state.get_data()).get('exact_time')
    bottom = int(approximate_time.split('-')[0])
    upper = int(approximate_time.split('-')[1])
    time_intervals = sum([[str(i)] * 4 for i in range(bottom, upper)], [])
    for i, j in enumerate(time_intervals):
        if len(j) == 1:
            time_intervals[i] = '0' + j
    time_00 = [i + ':00' for i in time_intervals[::4]]
    time_15 = [i + ':15' for i in time_intervals[1::4]]
    time_30 = [i + ':30' for i in time_intervals[2::4]]
    time_45 = [i + ':45' for i in time_intervals[3::4]]
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    time_available = await get_available_times(restaurant_number, how_many, date_booking)
    if time_available != True:
        time_00, time_15, time_30, time_45 = await reformat_times(time_available, [time_00, time_15, time_30, time_45])

    msg_id = await message.answer(await safe_for_markdown(msgs.exact_time), parse_mode=types.ParseMode.MARKDOWN_V2,
                                  reply_markup=await kb.exact_time_keyboard(time_00, time_15, time_30, time_45))
    await set_message_id(msg_id)


async def rechoose_table_yes_no(message: types.Message, state: FSMContext):
    msg_id = await message.answer(msgs.want_choose_table, reply_markup=await kb.choose_table_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text=['choose_table_yes'], state=Booking.table)
async def choose_table_yes(query: CallbackQuery, state: FSMContext):
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    tables = await get_available_tables_with_people(restaurant_number, how_many, date_booking, exact_time)

    if len(tables) == 0:
        await query.message.answer(msgs.all_tables_busy)
        return

    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE, True)

    await state.update_data(table='choosing')
    keyboard = await kb.choose_table_yes_keyboard(colored_images)
    if colored_images[0][2] == 'path':
        msg_id = await bot.send_photo(query.message.chat.id, open(colored_images[0][0], 'rb'), msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        # await FileIDs.create(path=colored_images[0][1], file_id=msg_id.photo[-1].file_id)
    else:
        msg_id = await bot.send_photo(query.message.chat.id, colored_images[0][0], msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        await set_message_id(msg_id)


# @dp.callback_query_handler(text=['choose_table_no'], state=Booking.table)
async def choose_table_no(query: CallbackQuery, state: FSMContext):
    await state.update_data(table=msgs.not_important)
    await Booking.next()

    async with state.proxy() as data:
        if data['table'] == msgs.not_important:
            msg_text = msgs.information_about2.format(msgs.restaurants[int(data['restaurant'])],
                                                      data['date_booking'] + ' ' +
                                                      data['exact_time'],
                                                      data['how_many'], msgs.guests[data['how_many']])
        else:
            msg_text = msgs.information_about.format(msgs.restaurants[int(data['restaurant'])],
                                                     data['date_booking'] + ' ' +
                                                     data['exact_time'],
                                                     data['how_many'], msgs.guests[data['how_many']],
                                                     data['table'][1])

        msg_id = await query.message.answer(
            await safe_for_markdown(msg_text), reply_markup=await kb.confirm_keyboard(),
            parse_mode=types.ParseMode.MARKDOWN_V2)

    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains=['tableimage_'], state=Booking.table)
async def tableimage_(query: CallbackQuery, state: FSMContext):
    image_number = int(query.data.split('_')[1])
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    tables = await get_available_tables_with_people(restaurant_number, how_many, date_booking, exact_time)
    if len(tables) == 0:
        await query.message.answer(msgs.all_tables_busy)
        return
    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE, True)
    keyboard = await kb.tableimage_keyboard(colored_images, image_number)

    media = types.MediaGroup()
    if colored_images[image_number][2] == 'path':
        media = types.InputMediaPhoto(open(colored_images[image_number][0], 'rb'), msgs.chose_table,
                                      parse_mode=types.ParseMode.MARKDOWN_V2)
        msg_id = await query.message.edit_media(media, reply_markup=keyboard)
        # await FileIDs.create(path=colored_images[image_number][1], file_id=msg_id.photo[-1].file_id)
    else:
        media = types.InputMediaPhoto(colored_images[image_number][0], msgs.chose_table,
                                      parse_mode=types.ParseMode.MARKDOWN_V2)
        msg_id = await query.message.edit_media(media, reply_markup=keyboard)


# # @dp.callback_query_handler(text_contains=['table_'], state=Booking.table)
# @dp.message_handler(state=Booking.table)
async def chosen_tables(message: types.Message, state: FSMContext):
    table = message.text.strip()
    if not table.isdigit():
        await message.answer(msgs.only_digits_tables)
        return
    table = int(table)
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    tables = await get_available_tables_with_people(restaurant_number, how_many, date_booking, exact_time)
    if len(tables) == 0:
        await message.answer(msgs.all_tables_busy)
        return

    try:
        table_now = [i[1] for i in tables].index(table)
    except ValueError:
        await message.answer(msgs.only_tables_in_images)
        return
    await Booking.next()
    await state.update_data(table=tables[table_now][::])


    async with state.proxy() as data:
        if data['table'] == msgs.not_important:
            msg_text = msgs.information_about2.format(msgs.restaurants[int(data['restaurant'])],
                                                      data['date_booking'] + ' ' +
                                                      data['exact_time'],
                                                      data['how_many'], msgs.guests[data['how_many']])
        else:
            msg_text = msgs.information_about.format(msgs.restaurants[int(data['restaurant'])],
                                                     data['date_booking'] + ' ' +
                                                     data['exact_time'],
                                                     data['how_many'], msgs.guests[data['how_many']],
                                                     data['table'][1])

    msg_id = await message.answer(
        await safe_for_markdown(msg_text), reply_markup=await kb.confirm_keyboard(),
        parse_mode=types.ParseMode.MARKDOWN_V2)

    await set_message_id(msg_id)


async def rechose_table(message: types.Message, state: FSMContext):
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    tables = await get_available_tables_with_people(restaurant_number, how_many, date_booking, exact_time)

    if len(tables) == 0:
        await message.answer(msgs.all_tables_busy)
        return
    media = types.MediaGroup()
    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE, True)
    keyboard = await kb.choose_table_yes_keyboard(colored_images)
    if colored_images[0][2] == 'path':
        msg_id = await bot.send_photo(message.chat.id, open(colored_images[0][0], 'rb'), msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        # await FileIDs.create(path=colored_images[0][1], file_id=msg_id.photo[-1].file_id)
    else:
        msg_id = await bot.send_photo(message.chat.id, colored_images[0][0], msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='confirm', state=Booking.confirmation)
async def confirm(query: CallbackQuery, state: FSMContext):
    date = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    now = datetime.datetime.now(tz=config.timezone)
    now = datetime.datetime.now(tz=config.timezone)
    now_time = now.strftime('%H:%M')
    time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE)).strftime('%H:%M')
    if now.strftime('%d.%m') == (await state.get_data()).get('date_booking') and exact_time <= time_in_advance:
        if now.hour >= int((await state.get_data()).get('approximate_time').split('-')[1]) - 1:
            await Booking.approximate_time.set()
            await rechose_approximate_time(query.message, state)
            return
        await Booking.exact_time.set()
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        await rechose_exact_time(query.message, state)
        return
    elif now.strftime('%m.%d') > '.'.join([(await state.get_data()).get('date_booking').split('.')[1],
                                           (await state.get_data()).get('date_booking').split('.')[0]]):
        await Booking.date_booking.set()
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        await rechose_date_booking(query.message, state)
        return
    table = (await state.get_data()).get('table')
    if table != msgs.not_important:
        av_tables = await get_available_tables_with_people((await state.get_data()).get('restaurant'),
                                                           (await state.get_data()).get('how_many'),
                                                           (await state.get_data()).get('date_booking'),
                                                           (await state.get_data()).get('exact_time'))
        if table not in av_tables:
            await Booking.table.set()
            await query.message.answer(msgs.wrong_table)
            await rechose_table(query.message, state)
            return
    await Booking.next()
    await register2(query, state)


async def rechose_confirm(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        # people = msgs.people_many if int(data['how_many']) > 1 else msgs.people_one
        if data['table'] == msgs.not_important:
            msg_text = msgs.information_about2.format(msgs.restaurants[int(data['restaurant'])],
                                                      data['date_booking'] + ' ' +
                                                      data['exact_time'],
                                                      data['how_many'], msgs.guests[data['how_many']])
        else:
            msg_text = msgs.information_about.format(msgs.restaurants[int(data['restaurant'])],
                                                     data['date_booking'] + ' ' +
                                                     data['exact_time'],
                                                     data['how_many'], msgs.guests[data['how_many']],
                                                     data['table'][1])

        msg_id = await message.answer(
            await safe_for_markdown(msg_text), reply_markup=await kb.confirm_keyboard(),
            parse_mode=types.ParseMode.MARKDOWN_V2)
        await set_message_id(msg_id)


# @dp.callback_query_handler(text='register', state=Booking.name)
async def register(query: CallbackQuery, state: FSMContext):
    await query.message.answer(msgs.enter_name)


async def register2(query: CallbackQuery, state: FSMContext):
    await query.message.answer(await safe_for_markdown(msgs.give_your_data), parse_mode=types.ParseMode.MARKDOWN_V2)
    await query.message.answer(msgs.enter_name)


# @dp.message_handler(lambda text: text not in btns.reply_keyboard_buttons, state=Booking.name)
async def name_handler(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Booking.next()
    await message.answer(msgs.phone_request)


async def rechose_name(message: types.Message, state: FSMContext):
    await message.answer(msgs.enter_name)


# @dp.message_handler(lambda text: text not in btns.reply_keyboard_buttons, state=Booking.phone)
async def phone_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()
    phone = await is_phone_valid(text)
    if phone is None:
        await message.answer(msgs.phone_is_wrong)
        return
    await state.update_data(phone=phone)
    await Booking.next()

    async with state.proxy() as data:
        msg_id = await message.answer(
            await safe_for_markdown(msgs.personal_data2.format(data.get('name'), data.get('phone'))),
            reply_markup=await kb.final_confirm_keyboard(), parse_mode=types.ParseMode.MARKDOWN_V2)
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='final_confirm', state=Booking.final)
async def final_confirm(query: CallbackQuery, state: FSMContext):
    await Booking.next()
    date = (await state.get_data()).get('date_booking')
    time = (await state.get_data()).get('exact_time')
    exact_time = (await state.get_data()).get('exact_time')
    now = datetime.datetime.now(tz=config.timezone)
    now_time = now.strftime('%H:%M')
    time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE)).strftime('%H:%M')
    if now.strftime('%d.%m') == (await state.get_data()).get('date_booking') and exact_time <= time_in_advance:
        if now.hour >= int((await state.get_data()).get('approximate_time').split('-')[1]) - 1:
            await Booking.approximate_time.set()
            await rechose_approximate_time(query.message, state)
            return
        await Booking.exact_time.set()
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        await rechose_exact_time(query.message, state)
        return
    # elif now.strftime('%d.%m') > (await state.get_data()).get('date_booking'):
    elif now.strftime('%m.%d') > '.'.join([(await state.get_data()).get('date_booking').split('.')[1],
                                           (await state.get_data()).get('date_booking').split('.')[0]]):

        await Booking.date_booking.set()
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        await rechose_date_booking(query.message, state)
        return
    table = (await state.get_data()).get('table')
    if table != msgs.not_important:
        av_tables = await get_available_tables_with_people(
            (await state.get_data()).get('restaurant'),
            (await state.get_data()).get('how_many'),
            (await state.get_data()).get('date_booking'),
            (await state.get_data()).get('exact_time'))
        if table not in av_tables:
            await Booking.table.set()
            await query.message.answer(msgs.wrong_table)
            await rechose_table(query.message, state)
            return
    time_book = datetime.datetime.strptime(f'{date}.{now.year} {time}', '%d.%m.%Y %H:%M')
    await remind_handler_2(query, state, None)


# @dp.callback_query_handler(text_contains=['remind_'], state=Booking.remind)
async def remind_handler(query: CallbackQuery, state: FSMContext):
    remind = query.data.split('_')[1]
    if not remind.isdigit():
        if remind == 'none':
            return
        remind = None
    else:
        remind = int(remind)

    date = (await state.get_data()).get('date_booking')
    time = (await state.get_data()).get('exact_time')
    exact_time = (await state.get_data()).get('exact_time')

    now = datetime.datetime.now(tz=config.timezone)
    time_in_advance = (now + datetime.timedelta(minutes=15 * config.BOOK_IN_ADVANCE)).strftime('%H:%M')
    if now.strftime('%d.%m') == (await state.get_data()).get('date_booking') and exact_time <= time_in_advance:
        await Booking.exact_time.set()
        await query.message.answer(msgs.wrong_exact_time.format(15 * config.BOOK_IN_ADVANCE))
        await rechose_exact_time(query.message, state)
        return

    time_book = datetime.datetime.strptime(f'{date}.{now.year} {time}', '%d.%m.%Y %H:%M')
    now = now.replace(tzinfo=None)
    time_plus_2 = now + datetime.timedelta(hours=2)
    time_plus_6 = now + datetime.timedelta(hours=6)
    time_plus_12 = now + datetime.timedelta(hours=12)
    time_plus_24 = now + datetime.timedelta(hours=24)
    remind_btns = [[24, 'За 24 часа'], [12, 'За 12 часов'], [6, 'За 6 часов'], [2, 'За 2 часа'],
                   ['no', 'Не напоминать']]
    if not (time_book > time_plus_24):
        remind_btns[0][0] = 'none'
        remind_btns[0][1] = ''
    if not (time_book > time_plus_12):
        remind_btns[1][0] = 'none'
        remind_btns[1][1] = ''
    if not (time_book > time_plus_6):
        remind_btns[2][0] = 'none'
        remind_btns[2][1] = ''
    if not (time_book > time_plus_2):
        remind_btns[3][0] = 'none'
        remind_btns[3][1] = ''
    _remind = remind
    if not _remind:
        _remind = 'no'
    for i in range(len(remind_btns)):
        if _remind == remind_btns[i][0]:
            remind_btns[i][1] = btns.check_mark + remind_btns[i][1]


    await query.message.edit_reply_markup(reply_markup=await kb.remind_keyboard(remind_btns))
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    await state.update_data(remind=remind)
    async with state.proxy() as data:
        user = await User.get_or_none(chat_id=query.message.chat.id)
        if not user:
            user = await User.create(chat_id=query.message.chat.id, name=data.get('name'), phone=data.get('phone'))
        else:
            if data.get('name'):
                user.name = data.get('name')
            if data.get('phone'):
                user.phone = data.get('phone')
            await user.save()
        restaurant = await Restaurant.get(self_id=data.get('restaurant'))
        order = await Order.create(user=user, restaurant=restaurant, how_many=data.get('how_many'),
                                   date=data.get('date_booking'), time=data.get('exact_time'), remind=remind)
        if data.get('table') == msgs.not_important:
            table_range, table_joint_range, table = await create_order_without_table(data.get('restaurant'),
                                                                                     data.get('how_many'),
                                                                                     data.get('date_booking'),
                                                                                     data.get('exact_time'), user.name,
                                                                                     user.phone, order.id)
        else:
            table_range, table_joint_range, table = await create_order(data.get('restaurant'), data.get('how_many'),
                                                                       data.get('date_booking'),
                                                                       data.get('exact_time'), data.get('table'),
                                                                       user.name, user.phone, order.id)
        order.table_range = table_range
        order.table_joint_range = table_joint_range
        order.table = await Table.get(table_name=table[1], restaurant=restaurant)
        await order.save()
        people = msgs.people_many if int(data['how_many']) > 1 else msgs.people_one
        if data['table'] == msgs.not_important:
            msg_text = msgs.booking_success2.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,

                                                    data['date_booking'] + ' ' + data['exact_time'],
                                                    data['how_many'], msgs.guests[data['how_many']])
            msg_text_admin = msgs.admin_booking_info2.format(msgs.restaurants[data.get('restaurant')], user.name,
                                                             user.phone,
                                                             data['date_booking'] + ' ' + data['exact_time'],
                                                             data['how_many'], msgs.guests[data['how_many']], order.id)
        else:
            msg_text = msgs.booking_success.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,

                                                   data['date_booking'] + ' ' + data['exact_time'],
                                                   data['how_many'], msgs.guests[data['how_many']], data['table'][1])
            msg_text_admin = msgs.admin_booking_info.format(msgs.restaurants[data.get('restaurant')], user.name,
                                                            user.phone,
                                                            data['date_booking'] + ' ' + data['exact_time'],
                                                            data['how_many'], msgs.guests[data['how_many']],
                                                            data['table'][1], order.id)
        if data.get('remind'):
            reminds = {24: '24 часа', 12: '12 часов', 6: '6 часов', 2: '2 часа'}
            msg_text += msgs.with_remind.format(reminds[data['remind']])
        # msg_text += msgs.for_cancel.format(config.PHONES[data.get('restaurant')])
        await query.message.answer(await safe_for_markdown(msg_text), parse_mode=types.ParseMode.MARKDOWN_V2,
                                   reply_markup=await kb.admin_keyboard())
        # await admin_sender(msg_text_admin)

    await state.finish()


async def admin_sender(msg_text, restaurant_number):
    await AdminSend.create(text=msg_text, restaurant=restaurant_number)


async def remind_handler_2(query: CallbackQuery, state: FSMContext, remind):
    date = (await state.get_data()).get('date_booking')
    time = (await state.get_data()).get('exact_time')
    now = datetime.datetime.now(tz=config.timezone)
    time_book = datetime.datetime.strptime(f'{date}.{now.year} {time}', '%d.%m.%Y %H:%M')
    now = now.replace(tzinfo=None)

    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    await state.update_data(remind=remind)
    async with state.proxy() as data:
        user = await User.get_or_none(chat_id=query.message.chat.id)
        if not user:
            user = await User.create(chat_id=query.message.chat.id, name=data.get('name'), phone=data.get('phone'))
        else:
            if data.get('name'):
                user.name = data.get('name')
            if data.get('phone'):
                user.phone = data.get('phone')
            await user.save()
        restaurant = await Restaurant.get(self_id=data.get('restaurant'))
        order = await Order.create(user=user, restaurant=restaurant, how_many=data.get('how_many'),
                                   date=data.get('date_booking'), time=data.get('exact_time'), remind=remind)
        if data.get('table') == msgs.not_important:
            table_range, table_joint_range, table = await create_order_without_table(data.get('restaurant'),
                                                                                     data.get('how_many'),
                                                                                     data.get('date_booking'),
                                                                                     data.get('exact_time'), user.name,
                                                                                     user.phone, order.id)
        else:
            table_range, table_joint_range, table = await create_order(data.get('restaurant'), data.get('how_many'),
                                                                       data.get('date_booking'),
                                                                       data.get('exact_time'), data.get('table'),
                                                                       user.name, user.phone, order.id)
        order.table_range = table_range
        order.table_joint_range = table_joint_range
        order.table = await Table.get(table_name=table[1], restaurant=restaurant)
        await order.save()
        people = msgs.people_many if int(data['how_many']) > 1 else msgs.people_one
        if data['table'] == msgs.not_important:
            msg_text = msgs.booking_success2.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,

                                                    data['date_booking'] + ' ' + data['exact_time'],
                                                    data['how_many'], msgs.guests[data['how_many']])
            msg_text_admin = msgs.admin_booking_info2.format(msgs.restaurants[data.get('restaurant')], user.name,
                                                             user.phone,

                                                             data['date_booking'] + ' ' + data['exact_time'],
                                                             data['how_many'], msgs.guests[data['how_many']], order.id)
        else:
            msg_text = msgs.booking_success.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,
                                                   data['date_booking'] + ' ' + data['exact_time'],
                                                   data['how_many'], msgs.guests[data['how_many']], data['table'][1])
            msg_text_admin = msgs.admin_booking_info.format(msgs.restaurants[data.get('restaurant')], user.name,
                                                            user.phone,
                                                            data['date_booking'] + ' ' + data['exact_time'],
                                                            data['how_many'], msgs.guests[data['how_many']],
                                                            data['table'][1], order.id)
        if data.get('remind'):
            reminds = {24: '24 часа', 12: '12 часов', 6: '6 часов', 2: '2 часа'}
            msg_text += msgs.with_remind.format(reminds[data['remind']])
        # msg_text += msgs.for_cancel.format(config.PHONES[data.get('restaurant')])

        await query.message.answer(await safe_for_markdown(msg_text), parse_mode=types.ParseMode.MARKDOWN_V2,
                                   reply_markup=await kb.admin_keyboard())
        await admin_sender(msg_text_admin, data.get('restaurant'))
    await state.finish()


# @dp.callback_query_handler(text='wrong_final_confirm', state=Booking.final)
async def wrong_final_confirm(query: CallbackQuery, state: FSMContext):
    await Booking.name.set()
    await register(query, state)


# @dp.message_handler(text=btns.menu, state=Booking)
async def settings_yes_no(message: types.Message, state: FSMContext):
    await message.answer(msgs.interrupting_booking, reply_markup=await kb.interrupt_keyboard())


# @dp.callback_query_handler(text='yes_interrupt', state=Booking)
async def yes_interrupt(query: CallbackQuery, state: FSMContext):
    await state.finish()
    await settings(query.message, state)


# @dp.callback_query_handler(text='no_interrupt', state=Booking)
async def no_interrupt(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    await query.message.answer(msgs.can_continue)
    await forward_to_func(query, state)


async def forward_to_func(query: CallbackQuery, state: FSMContext):
    s = await state.get_state()
    if 'restaurant' in s:
        pass
    elif 'how_many' in s:
        await rechose_how_many(query.message, state)
    elif 'date_booking' in s:
        await rechose_date_booking(query.message, state)
    elif 'approximate_time' in s:
        await rechose_approximate_time(query.message, state)
    elif 'exact_time' in s:
        await rechose_exact_time(query.message, state)
    elif 'confirmation' in s:
        await rechose_confirm(query.message, state)
    elif 'name' in s:
        await rechose_name(query.message, state)
    elif 'phone' in s:
        await rechose_name(query.message, state)
    elif 'final' in s:
        await Booking.confirmation.set()
        await rechose_confirm(query.message, state)
    elif 'remind' in s:
        await Booking.confirmation.set()
        await rechose_confirm(query.message, state)


# # @dp.callback_query_handler(text_contains=['PREV-YEAR_'], state=Booking.date_booking)
async def prev_year(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)
    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date - datetime.timedelta(days=365)
    keyboard = await kb.generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                          delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


# # @dp.callback_query_handler(text_contains=['NEXT-YEAR_'], state=Booking.date_booking)
async def next_year(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)
    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date + datetime.timedelta(days=365)
    keyboard = await kb.generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                          delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


# # @dp.callback_query_handler(text_contains=['PREV-MONTH_'], state=Booking.date_booking)
async def prev_month(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)

    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date - datetime.timedelta(days=1)
    keyboard = await kb.generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                          delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


# # @dp.callback_query_handler(text_contains=['NEXT-MONTH_'], state=Booking.date_booking)
async def next_month(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)

    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date + datetime.timedelta(days=31)
    keyboard = await kb.generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                          delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


