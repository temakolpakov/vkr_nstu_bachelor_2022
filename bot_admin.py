import calendar
import aiogram
import phonenumbers
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, callback_query, ParseMode, ReplyKeyboardMarkup, \
    KeyboardButton, InputMedia, InputMediaPhoto, CallbackQuery, ContentType
from aiogram.utils import executor, exceptions
from aiogram.utils.deep_linking import get_start_link, decode_payload
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
# from aiogram.contrib.middlewares.logging import LoggingMiddleware
from tortoise.query_utils import Q

import buttons
import config
import asyncio

from img_helper import get_colored_image
from models import *
import messages_admin as msgs
from google_sheet_functions import *
import datetime
import logging
import random
import re
from aiogram.types import ChatActions
from config import admins, broadcaster_queue
import validators
from logging_middleware import LoggingMiddleware
from states_admin import *
from bot_admin_setup import bot, dp
from middlewares.answercallback_middleware import set_message_id
from helpers import is_phone_valid, safe_for_markdown

remember_this_message = {}



russian_months = {1: 'Янв', 2: 'Февр', 3: 'Март', 4: 'Апр', 5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Авг', 9: 'Сент',
                  10: 'Окт', 11: 'Нояб', 12: 'Дек'}

async def generate_calendar(year, month, day, now, days_for_booking, selected=None, delete_empty=False):
    lower_bound = now.date()
    upper_bound = lower_bound + datetime.timedelta(days=days_for_booking)
    inline_kb = InlineKeyboardMarkup(row_width=8)
    inline_kb.row()
    # inline_kb.insert(InlineKeyboardButton(
    #     "<<",
    #     callback_data=f'PREV-YEAR_{year}_{month}_1'
    # ))
    inline_kb.insert(InlineKeyboardButton(' ', callback_data=' '))
    inline_kb.insert(InlineKeyboardButton(
        f'{russian_months.get(month)} {str(year)}',
        callback_data=' '
    ))
    inline_kb.insert(InlineKeyboardButton(' ', callback_data=' '))

    # inline_kb.insert(InlineKeyboardButton(
    #     ">>",
    #     callback_data=f'NEXT-YEAR_{year}_{month}_1'
    # ))
    inline_kb.row()
    for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        inline_kb.insert(InlineKeyboardButton(day, callback_data=' '))
    month_calendar = calendar.monthcalendar(year, month)
    first_day = None
    last_day = None
    if not delete_empty:
        for week in month_calendar:
            inline_kb.row()
            for day in week:
                if (day == 0):
                    inline_kb.insert(InlineKeyboardButton(" ", callback_data=' '))
                    continue
                d = datetime.date(year, month, day)
                if lower_bound <= d <= upper_bound:
                    if d.strftime('%d.%m') == selected:
                        day2 = buttons.check_mark + f'{day}'
                    else:
                        day2 = str(day)
                    inline_kb.insert(InlineKeyboardButton(
                        day2, callback_data=f'date_booking_{day}.{month}.{year}_cal'
                    ))
                    if not first_day:
                        first_day = d
                    last_day = d
                else:
                    inline_kb.insert(InlineKeyboardButton(" ", callback_data=' '))
    else:
        for week in month_calendar:
            row = []
            for day in week:
                if (day == 0):
                    row.append(InlineKeyboardButton(" ", callback_data=' '))
                    continue
                d = datetime.date(year, month, day)
                if lower_bound <= d <= upper_bound:
                    if d.strftime('%d.%m') == selected:
                        day2 = buttons.check_mark + f'{day}'
                    else:
                        day2 = str(day)
                    row.append(InlineKeyboardButton(
                        day2, callback_data=f'date_booking_{day}.{month}.{year}_cal'
                    ))
                    if not first_day:
                        first_day = d
                    last_day = d
                else:
                    row.append(InlineKeyboardButton(" ", callback_data=' '))
            not_empty = False
            for i in row:
                if i.text != ' ':
                    not_empty = True
                    break
            if not_empty:
                inline_kb.row()
                for i in row:
                    inline_kb.insert(i)
    if first_day == lower_bound and last_day == upper_bound:
        return inline_kb
    inline_kb.row()
    if first_day != lower_bound:
        inline_kb.insert(InlineKeyboardButton(
            "←", callback_data=f'PREV-MONTH_{year}_{month}_{day}'
        ))
    else:
        inline_kb.insert(InlineKeyboardButton(" ", callback_data=' '))
    inline_kb.insert(InlineKeyboardButton(" ", callback_data=' '))
    if last_day != upper_bound:
        inline_kb.insert(InlineKeyboardButton(
            "→", callback_data=f'NEXT-MONTH_{year}_{month}_{day}'
        ))
    else:
        inline_kb.insert(InlineKeyboardButton(" ", callback_data=' '))

    return inline_kb


@dp.callback_query_handler(text_contains=['PREV-YEAR_'], state=Booking.date_booking)
async def prev_year(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)
    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date - datetime.timedelta(days=365)
    keyboard = await generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                       delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query_handler(text_contains=['NEXT-YEAR_'], state=Booking.date_booking)
async def next_year(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)
    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date + datetime.timedelta(days=365)
    keyboard = await generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                       delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query_handler(text_contains=['PREV-MONTH_'], state=Booking.date_booking)
async def prev_month(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)

    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date - datetime.timedelta(days=1)
    keyboard = await generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                       delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query_handler(text_contains=['NEXT-MONTH_'], state=Booking.date_booking)
async def next_month(query: CallbackQuery, state: FSMContext):
    now = datetime.datetime.now(tz=config.timezone)

    year = query.data.split('_')[1]
    month = query.data.split('_')[2]
    temp_date = datetime.datetime(int(year), int(month), 1, tzinfo=config.timezone)
    new_date = temp_date + datetime.timedelta(days=31)
    keyboard = await generate_calendar(new_date.year, new_date.month, new_date.day, now, config.DAYS_FOR_BOOKING,
                                       delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)


@dp.message_handler(text=buttons.back, state=Broadcast.text)
async def back_to_admin_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message, state)


@dp.message_handler(text=buttons.back, state=Broadcast.next_step)
async def back_to_broadcast_text(message: types.Message, state: FSMContext):
    await Broadcast.tags.set()
    await state.update_data(tags=[])
    await broadcast_menu(message, state)


@dp.message_handler(text=buttons.back, state=Broadcast.attachment)
async def back_to_broadcast_next_step(message: types.Message, state: FSMContext):
    await Broadcast.next_step.set()
    await broadcast_text_handler2(message, state)

@dp.message_handler(text=buttons.back, state=Broadcast.attachment2)
async def back_to_broadcast_atach(message: types.Message, state: FSMContext):
    cur_atachments = (await state.get_data()).get('attachment')
    if len(cur_atachments['links']):
        if len(cur_atachments['links'][-1]) != 2:
            cur_atachments['links'].pop(-1)
    await state.update_data(attachment=cur_atachments)
    await Broadcast.next_step.set()
    await broadcast_text_handler2(message, state)

@dp.message_handler(text=buttons.back, state=Broadcast.conf_)
@dp.message_handler(text=buttons.back, state=Broadcast.tags)
async def back_to_broadcast_next_step2(message: types.Message, state: FSMContext):
    await Broadcast.next_step.set()
    await broadcast_text_handler2(message, state)


@dp.message_handler(text=buttons.back, state=AddTag.name)
@dp.message_handler(text=buttons.back, state=DelTag.name)
async def back_to_tags_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await admin_tags2(message, state)


@dp.message_handler(text=buttons.back, state=DelTag.confirmation)
async def back_to_del_tags(message: types.Message, state: FSMContext):
    await DelTag.name.set()
    await del_tag2(message)


@dp.message_handler(text=buttons.back, state=BroadcastHistoryStates.tags)
async def back_to_start(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message, state)


@dp.message_handler(text=buttons.back, state=BroadcastHistoryStates.id)
@dp.message_handler(text=buttons.back, state=BroadcastHistoryStates.wait)
async def back_to_broadcast_history(message: types.Message, state: FSMContext):
    await BroadcastHistoryStates.tags.set()
    await state.update_data(tags=[])
    await broadcast_history(message, state, False)


@dp.message_handler(text=buttons.back, state=Booking.restaurant)
async def back_to_main(message: types.Message, state: FSMContext):
    await start(message, state)


@dp.message_handler(text=buttons.back, state=Booking.how_many)
async def back_to_restaurants(message: types.Message, state: FSMContext):
    how_many = (await state.get_data()).get('how_many')
    if how_many == 'bigger_number':
        await state.update_data(how_many=None)
        await rechose_how_many(message, state)
    else:
        await start(message, state, back_flag=True)


@dp.message_handler(text=buttons.back, state=Booking.date_booking)
async def back_to_how_many(message: types.Message, state: FSMContext):
    date_booking = (await state.get_data()).get('date_booking')
    if date_booking == 'later':
        await state.update_data(date_booking=None)
        await rechose_date_booking(message, state)
    else:
        await Booking.previous()
        await rechose_how_many(message, state)


@dp.message_handler(text=buttons.back, state=Booking.approximate_time)
async def back_to_date_booking(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_date_booking(message, state)


@dp.message_handler(text=buttons.back, state=Booking.exact_time)
async def back_to_approximate_time(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_approximate_time(message, state)


@dp.message_handler(text=buttons.back, state=Booking.table)
async def back_to_exact_time(message: types.Message, state: FSMContext):
    table = (await state.get_data()).get('table')
    await state.update_data(table=msgs.yes_no)
    if table == msgs.not_important or table == msgs.yes_no or table is None:
        await Booking.previous()
        await rechose_exact_time(message, state)
    else:
        await rechoose_table_yes_no(message, state)


@dp.message_handler(text=buttons.back, state=Booking.confirmation)
async def back_to_tables(message: types.Message, state: FSMContext):
    await Booking.previous()
    table = (await state.get_data()).get('table')
    if table == msgs.not_important:
        await state.update_data(table=msgs.yes_no)
        await rechoose_table_yes_no(message, state)
    else:
        await rechose_table(message, state)


@dp.message_handler(text=buttons.back, state=Booking.name)
async def back_to_confirmation(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_confirm(message, state)


@dp.message_handler(text=buttons.back, state=Booking.phone)
async def back_to_name(message: types.Message, state: FSMContext):
    await Booking.previous()
    await rechose_name(message, state)


@dp.message_handler(text=buttons.back, state=Booking.final)
async def back_to_confirmation2(message: types.Message, state: FSMContext):
    await Booking.confirmation.set()
    await rechose_confirm(message, state)


@dp.message_handler(text=buttons.back, state=Booking.remind)
async def back_to_confirmation3(message: types.Message, state: FSMContext):
    await Booking.confirmation.set()
    await rechose_confirm(message, state)


@dp.message_handler(text=buttons.back)
async def back_to_admin_menu2(message: types.Message):
    await set_message_id(message)
    await start(message, None)



async def set_keyboard_admin(message, text, parse_mode=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.new_booking))
    # keyboard.add(KeyboardButton(buttons.broadcast), KeyboardButton(buttons.tags))
    # keyboard.add(KeyboardButton(buttons.broadcast_history))
    await message.answer(text, reply_markup=keyboard, parse_mode=parse_mode)


async def set_keyboard_back(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back))
    await message.answer(text, reply_markup=keyboard)


async def set_keyboard_back_and_all(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.choose_all_broadcast))
    keyboard.add(KeyboardButton(buttons.back))
    if remember_this_message.get(message.chat.id):
        await bot.edit_message_reply_markup(message.chat.id, remember_this_message.get(message.chat.id),
                                            reply_markup=keyboard)
    else:
        msg = await message.answer(text, reply_markup=keyboard)
        return msg


async def set_keyboard_back_and_next(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    # keyboard.add(KeyboardButton(buttons.choose_all_broadcast))
    keyboard.add(KeyboardButton(buttons.next))
    keyboard.add(KeyboardButton(buttons.back))
    await message.answer(text, reply_markup=keyboard)



async def set_keyboard_booking(message: types.Message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back))
    keyboard.add(KeyboardButton(buttons.menu))
    await message.answer(text, parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=keyboard)

@dp.message_handler(commands='start', state='*')
async def start(message: types.Message, state: FSMContext, back_flag=False):
    if message.chat.id in admins:
        await set_keyboard_admin(message, msgs.you_are_admin.format(config.BOT_NAME))
        return

@dp.message_handler(text=buttons.new_booking, state='*')
async def new_booking(message: types.Message, state: FSMContext, back_flag=False, start_booking_again=False):
    if not back_flag:
        if await state.get_data() != {}:
            await state.finish()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.soviet_restaurant, callback_data='restaurant_1'))
    keyboard.add(InlineKeyboardButton(buttons.big_avenue_restaurant, callback_data='restaurant_2'))
    keyboard.add(InlineKeyboardButton(buttons.volynskyi_restaurant, callback_data='restaurant_3'))

    await Booking.restaurant.set()
    msg_text = msgs.choose_address
    # if start_booking_again:
    #     msg_text = msgs.choose_address
    # else:
    #     msg_text = msgs.start_message.format(await msgs.get_times_of_day(datetime.datetime.now(tz=config.timezone).hour)
    #                                          )
    msg_id = await message.answer(msg_text, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains=['restaurant_'], state=Booking.restaurant)
async def chosen_restaurant(query: CallbackQuery, state: FSMContext):
    restaurant_number = int(query.data.split('_')[1])
    keyboard = InlineKeyboardMarkup()
    buttons_rows = [InlineKeyboardButton(str(i), callback_data=f'how_many_{i}') for i in range(1, 7)]
    keyboard.row(*buttons_rows[:3])
    keyboard.row(*buttons_rows[3:])
    keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                 InlineKeyboardButton('7', callback_data='how_many_7'),
                 InlineKeyboardButton(' ', callback_data=' '))
    keyboard.add(InlineKeyboardButton(buttons.bigger_number, callback_data='bigger_number'))
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
    edit_keyboard = InlineKeyboardMarkup()
    if restaurant_number == 1:
        edit_keyboard.add(
            InlineKeyboardButton(buttons.check_mark + buttons.soviet_restaurant, callback_data='restaurant_1'))
        edit_keyboard.add(InlineKeyboardButton(buttons.big_avenue_restaurant, callback_data='restaurant_2'))
        edit_keyboard.add(InlineKeyboardButton(buttons.volynskyi_restaurant, callback_data='restaurant_3'))
    elif restaurant_number == 2:
        edit_keyboard.add(
            InlineKeyboardButton(buttons.soviet_restaurant, callback_data='restaurant_1'))
        edit_keyboard.add(
            InlineKeyboardButton(buttons.check_mark + buttons.big_avenue_restaurant, callback_data='restaurant_2'))
        edit_keyboard.add(InlineKeyboardButton(buttons.volynskyi_restaurant, callback_data='restaurant_3'))
    elif restaurant_number == 3:
        edit_keyboard.add(
            InlineKeyboardButton(buttons.soviet_restaurant, callback_data='restaurant_1'))
        edit_keyboard.add(InlineKeyboardButton(buttons.big_avenue_restaurant, callback_data='restaurant_2'))
        edit_keyboard.add(
            InlineKeyboardButton(buttons.check_mark + buttons.volynskyi_restaurant, callback_data='restaurant_3'))

    await query.message.edit_reply_markup(reply_markup=edit_keyboard)
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    await set_keyboard_booking(query.message, msg_text)

    msg_id = await query.message.answer(msgs.how_many, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains=['how_many_'], state=Booking.how_many)
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
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.today.format(today_cut), callback_data=f'date_booking_{today}'))
    keyboard.add(InlineKeyboardButton(buttons.tomorrow.format(tomorrow_cut), callback_data=f'date_booking_{tomorrow}'))
    keyboard.add(InlineKeyboardButton(buttons.day_after_tomorrow.format(day_after_tomorrow_cut),
                                      callback_data=f'date_booking_{day_after_tomorrow}'))
    keyboard.add(InlineKeyboardButton(buttons.later, callback_data=f'date_booking_later'))
    edit_keyboard = InlineKeyboardMarkup()
    buttons_rows = []
    for i in range(1, 7):
        if i == how_many:
            buttons_rows.append(InlineKeyboardButton(buttons.check_mark + str(i), callback_data=f'how_many_{i}'))
        else:
            buttons_rows.append(InlineKeyboardButton(str(i), callback_data=f'how_many_{i}'))

    edit_keyboard.row(*buttons_rows[:3])
    edit_keyboard.row(*buttons_rows[3:])
    if how_many == 7:
        edit_keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                          InlineKeyboardButton(buttons.check_mark + '7', callback_data='how_many_7'),
                          InlineKeyboardButton(' ', callback_data=' '))
    else:
        edit_keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                          InlineKeyboardButton('7', callback_data='how_many_7'),
                          InlineKeyboardButton(' ', callback_data=' '))
    edit_keyboard.add(InlineKeyboardButton(buttons.bigger_number, callback_data='bigger_number'))

    await query.message.edit_reply_markup(reply_markup=edit_keyboard)
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    msg_id = await query.message.answer(msgs.choose_date, reply_markup=keyboard)
    await set_message_id(msg_id)


async def rechose_how_many(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    buttons_rows = []
    for i in range(1, 7):
        buttons_rows.append(InlineKeyboardButton(str(i), callback_data=f'how_many_{i}'))
    keyboard.row(*buttons_rows[:3])
    keyboard.row(*buttons_rows[3:])
    keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                 InlineKeyboardButton('7', callback_data='how_many_7'),
                 InlineKeyboardButton(' ', callback_data=' '))
    keyboard.add(InlineKeyboardButton(buttons.bigger_number, callback_data='bigger_number'))

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
    msg_id = await message.answer(msgs.how_many, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text='bigger_number', state=Booking.how_many)
async def bigger_number(query: CallbackQuery, state: FSMContext):
    await state.update_data(how_many='bigger_number')
    keyboard = InlineKeyboardMarkup()
    buttons_rows = []
    for i in range(1, 7):
        buttons_rows.append(InlineKeyboardButton(str(i), callback_data=f'how_many_{i}'))
    keyboard.row(*buttons_rows[:3])
    keyboard.row(*buttons_rows[3:])
    keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                 InlineKeyboardButton('7', callback_data='how_many_7'),
                 InlineKeyboardButton(' ', callback_data=' '))
    keyboard.add(InlineKeyboardButton(buttons.check_mark + buttons.bigger_number, callback_data='bigger_number'))
    await query.message.edit_reply_markup(keyboard)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.back_to_menu2, callback_data='back_to_menu2'))
    msg_id = await query.message.answer(
        msgs.for_bigger_number.format(config.PHONES[(await state.get_data()).get('restaurant')]), reply_markup=keyboard)
    await set_message_id(msg_id)

@dp.callback_query_handler(text='back_to_menu2', state=Booking.how_many)
async def back_to_menu2(query: CallbackQuery, state: FSMContext):
    await state.finish()
    await set_keyboard_admin(query.message, msgs.main_menu)


async def rechose_date_booking(message: types.Message, state: FSMContext):
    date_booking = (await state.get_data()).get('date_booking')
    now = datetime.datetime.now(tz=config.timezone)
    today = now.strftime('%d.%m.%Y')
    tomorrow = (now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    day_after_tomorrow = (now + datetime.timedelta(days=2)).strftime('%d.%m.%Y')
    today_cut = now.strftime('%d.%m')
    tomorrow_cut = (now + datetime.timedelta(days=1)).strftime('%d.%m')
    day_after_tomorrow_cut = (now + datetime.timedelta(days=2)).strftime('%d.%m')
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.today.format(today_cut), callback_data=f'date_booking_{today}'))
    keyboard.add(InlineKeyboardButton(buttons.tomorrow.format(tomorrow_cut), callback_data=f'date_booking_{tomorrow}'))
    keyboard.add(InlineKeyboardButton(buttons.day_after_tomorrow.format(day_after_tomorrow_cut),
                                      callback_data=f'date_booking_{day_after_tomorrow}'))

    keyboard.add(InlineKeyboardButton(buttons.later, callback_data=f'date_booking_later'))

    msg_id = await message.answer(msgs.choose_date, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains=['date_booking_'], state=Booking.date_booking)
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
    keyboard = InlineKeyboardMarkup()
    if 'cal' in query.data:
        selected = date_booking
        keyboard = await generate_calendar(d.year, d.month, d.day, now, config.DAYS_FOR_BOOKING, selected,
                                           delete_empty=True)
    else:

        if date_booking in [today, tomorrow, day_after_tomorrow]:
            if date_booking == today:
                keyboard.add(InlineKeyboardButton(buttons.check_mark + buttons.today.format(today),
                                                  callback_data=f'date_booking_{today}'))
            else:
                keyboard.add(InlineKeyboardButton(buttons.today.format(today), callback_data=f'date_booking_{today}'))
            if date_booking == tomorrow:
                keyboard.add(InlineKeyboardButton(buttons.check_mark + buttons.tomorrow.format(tomorrow),
                                                  callback_data=f'date_booking_{tomorrow}'))
            else:
                keyboard.add(
                    InlineKeyboardButton(buttons.tomorrow.format(tomorrow), callback_data=f'date_booking_{tomorrow}'))
            if date_booking == day_after_tomorrow:
                keyboard.add(
                    InlineKeyboardButton(buttons.check_mark + buttons.day_after_tomorrow.format(day_after_tomorrow),
                                         callback_data=f'date_booking_{day_after_tomorrow}'))
            else:
                keyboard.add(InlineKeyboardButton(buttons.day_after_tomorrow.format(day_after_tomorrow),
                                                  callback_data=f'date_booking_{day_after_tomorrow}'))
            keyboard.add(InlineKeyboardButton(buttons.later, callback_data=f'date_booking_later'))
        else:
            selected = date_booking
            keyboard = await generate_calendar(d.year, d.month, d.day, now, config.DAYS_FOR_BOOKING, selected,
                                               delete_empty=True)
    await query.message.edit_reply_markup(reply_markup=keyboard)
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)

    approximate_times = [['с 9 до 12', '9-12'], ['c 12 до 14', '12-14'], ['с 14 до 16', '14-16'],
                         ['с 16 до 18', '16-18'], ['с 18 до 20', '18-20'], ['с 20 до 22', '20-22']]
    keyboard = InlineKeyboardMarkup()
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

    first_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1]}') for i in approximate_times[:3]]
    second_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1]}') for i in approximate_times[3:]]
    keyboard.row(*first_row)
    keyboard.row(*second_row)
    msg_id = await query.message.answer(await safe_for_markdown(msgs.approximate_time),
                                        parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text='date_booking_later', state=Booking.date_booking)
async def date_booking_later(query: CallbackQuery, state: FSMContext):
    await state.update_data(date_booking='later')
    now = datetime.datetime.now(tz=config.timezone)
    keyboard = await generate_calendar(now.year, now.month, now.day, now, config.DAYS_FOR_BOOKING, delete_empty=True)
    await query.message.edit_reply_markup(keyboard)
    # msg_id = await query.message.answer(msgs.choose_date, reply_markup=keyboard)
    # await set_message_id(msg_id


async def reformat_times(time_available, times):
    for i in times:
        for j, k in enumerate(i):
            if k not in time_available:
                i[j] = ' '
    return times


@dp.callback_query_handler(text_contains=['approximate_time_'], state=Booking.approximate_time)
async def chosen_approximate_time(query: CallbackQuery, state: FSMContext):
    approximate_time = query.data.split('_')[2]
    if approximate_time == 'pass':
        return
    await state.update_data(approximate_time=approximate_time)
    await Booking.next()

    approximate_times = ['9-12', '12-14', '14-16', '16-18', '18-20', '20-22']
    approximate_times_full = [['с 9 до 12', '9-12'], ['c 12 до 14', '12-14'], ['с 14 до 16', '14-16'],
                              ['с 16 до 18', '16-18'], ['с 18 до 20', '18-20'], ['с 20 до 22', '20-22']]
    keyboard = InlineKeyboardMarkup()
    approximate_times_full[approximate_times.index(approximate_time)][0] = buttons.check_mark + approximate_times_full[
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
    first_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1]}') for i in
                 approximate_times_full[:3]]
    second_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1]}') for i in
                  approximate_times_full[3:]]
    keyboard.row(*first_row)
    keyboard.row(*second_row)
    await query.message.edit_reply_markup(reply_markup=keyboard)
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
    keyboard = InlineKeyboardMarkup()
    for i in range(len(time_00)):
        row = [InlineKeyboardButton(time_00[i],
                                    callback_data=f'exact_time_{time_00[i]}'),
               InlineKeyboardButton(time_15[i],
                                    callback_data=f'exact_time_{time_15[i]}'),
               InlineKeyboardButton(time_30[i],
                                    callback_data=f'exact_time_{time_30[i]}'),
               InlineKeyboardButton(time_45[i],
                                    callback_data=f'exact_time_{time_45[i]}')]
        keyboard.row(*row)
    msg_id = await query.message.answer(await safe_for_markdown(msgs.exact_time),
                                        parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=keyboard)
    await set_message_id(msg_id)


async def rechose_approximate_time(message: types.Message, state: FSMContext):
    approximate_times = ['9-12', '12-14', '14-16', '16-18', '18-20', '20-22']
    approximate_times_full = [['с 9 до 12', '9-12'], ['c 12 до 14', '12-14'], ['с 14 до 16', '14-16'],
                              ['с 16 до 18', '16-18'], ['с 18 до 20', '18-20'], ['с 20 до 22', '20-22']]
    approximate_time = (await state.get_data()).get('approximate_time')

    keyboard = InlineKeyboardMarkup()
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

    first_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1].replace(buttons.check_mark, "")}')
                 for i in
                 approximate_times_full[:3]]
    second_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1].replace(buttons.check_mark, "")}')
                  for i
                  in approximate_times_full[3:]]
    keyboard.row(*first_row)
    keyboard.row(*second_row)
    msg_id = await message.answer(await safe_for_markdown(msgs.approximate_time),
                                  parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains=['exact_time_'], state=Booking.exact_time)
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
            i[i.index(exact_time)] = buttons.check_mark + i[i.index(exact_time)]
    keyboard = InlineKeyboardMarkup()
    for i in range(len(time_00)):
        row = [InlineKeyboardButton(time_00[i],
                                    callback_data=f'exact_time_{time_00[i]}'),
               InlineKeyboardButton(time_15[i],
                                    callback_data=f'exact_time_{time_15[i]}'),
               InlineKeyboardButton(time_30[i],
                                    callback_data=f'exact_time_{time_30[i]}'),
               InlineKeyboardButton(time_45[i],
                                    callback_data=f'exact_time_{time_45[i]}')]
        keyboard.row(*row)
    await query.message.edit_reply_markup(reply_markup=keyboard)
    # await ChatActions.typing(0.1)
    # await asyncio.sleep(0.1)
    # await state.update_data(table=msgs.yes_no)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='choose_table_yes'),
                 InlineKeyboardButton(buttons.no2, callback_data='choose_table_no'))
    msg_id = await query.message.answer(msgs.want_choose_table, reply_markup=keyboard)
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

    keyboard = InlineKeyboardMarkup()
    for i in range(len(time_00)):
        row = [InlineKeyboardButton(time_00[i],
                                    callback_data=f'exact_time_{time_00[i]}'),
               InlineKeyboardButton(time_15[i],
                                    callback_data=f'exact_time_{time_15[i]}'),
               InlineKeyboardButton(time_30[i],
                                    callback_data=f'exact_time_{time_30[i]}'),
               InlineKeyboardButton(time_45[i],
                                    callback_data=f'exact_time_{time_45[i]}')]
        keyboard.row(*row)
    msg_id = await message.answer(await safe_for_markdown(msgs.exact_time), parse_mode=types.ParseMode.MARKDOWN_V2,
                                  reply_markup=keyboard)
    await set_message_id(msg_id)


async def rechoose_table_yes_no(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='choose_table_yes'),
                 InlineKeyboardButton(buttons.no2, callback_data='choose_table_no'))
    msg_id = await message.answer(msgs.want_choose_table, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text=['choose_table_yes'], state=Booking.table)
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
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton(buttons.page_next, callback_data='tableimage_1'))
    if colored_images[0][2] == 'path':
        msg_id = await bot.send_photo(query.message.chat.id, open(colored_images[0][0], 'rb'), msgs.chose_table,
                                  reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        # await FileIDs.create(path=colored_images[0][1], file_id=msg_id.photo[-1].file_id)
    else:
        msg_id = await bot.send_photo(query.message.chat.id, colored_images[0][0], msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        await set_message_id(msg_id)


@dp.callback_query_handler(text=['choose_table_no'], state=Booking.table)
async def choose_table_no(query: CallbackQuery, state: FSMContext):
    await state.update_data(table=msgs.not_important)
    await Booking.next()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.confirm, callback_data='confirm'),
                 InlineKeyboardButton(buttons.wrong, callback_data='new_booking'))

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
            await safe_for_markdown(msg_text), reply_markup=keyboard,
            parse_mode=types.ParseMode.MARKDOWN_V2)

    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains=['tableimage_'], state=Booking.table)
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
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        if image_number == len(colored_images) - 1:
            keyboard.add(InlineKeyboardButton(buttons.page_back, callback_data=f'tableimage_{image_number-1}'),
                         InlineKeyboardButton(' ', callback_data=' '))
        elif image_number == 0:
            keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                         InlineKeyboardButton(buttons.page_next, callback_data=f'tableimage_{image_number+1}'))
        else:
            keyboard.add(InlineKeyboardButton(buttons.page_back, callback_data=f'tableimage_{image_number-1}'),
                         InlineKeyboardButton(buttons.page_next, callback_data=f'tableimage_{image_number+1}'))
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


# @dp.callback_query_handler(text_contains=['table_'], state=Booking.table)
@dp.message_handler(state=Booking.table)
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

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.confirm, callback_data='confirm'),
                 InlineKeyboardButton(buttons.wrong, callback_data='new_booking'))

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
        await safe_for_markdown(msg_text), reply_markup=keyboard,
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
    keyboard = InlineKeyboardMarkup(row_width=5)
    media = types.MediaGroup()
    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE, True)
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton(buttons.page_next, callback_data='tableimage_1'))
    if colored_images[0][2] == 'path':
        msg_id = await bot.send_photo(message.chat.id, open(colored_images[0][0], 'rb'), msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        # await FileIDs.create(path=colored_images[0][1], file_id=msg_id.photo[-1].file_id)
    else:
        msg_id = await bot.send_photo(message.chat.id, colored_images[0][0], msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
    await set_message_id(msg_id)


@dp.callback_query_handler(text='confirm', state=Booking.confirmation)
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
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.confirm, callback_data='confirm'),
                 InlineKeyboardButton(buttons.wrong, callback_data='new_booking'))
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
            await safe_for_markdown(msg_text), reply_markup=keyboard,
            parse_mode=types.ParseMode.MARKDOWN_V2)
        await set_message_id(msg_id)



@dp.callback_query_handler(text='register', state=Booking.name)
async def register(query: CallbackQuery, state: FSMContext):
    await query.message.answer(msgs.enter_name)


async def register2(query: CallbackQuery, state: FSMContext):
    await query.message.answer(await safe_for_markdown(msgs.give_your_data), parse_mode=types.ParseMode.MARKDOWN_V2)
    await query.message.answer(msgs.enter_name)


@dp.message_handler(lambda text: text not in buttons.reply_keyboard_buttons, state=Booking.name)
async def name_handler(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Booking.next()
    await message.answer(msgs.phone_request)


async def rechose_name(message: types.Message, state: FSMContext):

    await message.answer(msgs.enter_name)


@dp.message_handler(lambda text: text not in buttons.reply_keyboard_buttons, state=Booking.phone)
async def phone_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()
    phone = await is_phone_valid(text)
    if phone is None:
        await message.answer(msgs.phone_is_wrong)
        return
    await state.update_data(phone=phone)
    await Booking.next()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='final_confirm'),
                 InlineKeyboardButton(buttons.no2, callback_data='wrong_final_confirm'))
    async with state.proxy() as data:
        msg_id = await message.answer(
            await safe_for_markdown(msgs.personal_data2.format(data.get('name'), data.get('phone'))),
            reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
    await set_message_id(msg_id)



@dp.callback_query_handler(text='final_confirm', state=Booking.final)
async def final_confirm(query: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
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


@dp.callback_query_handler(text_contains=['remind_'], state=Booking.remind)
async def remind_handler(query: CallbackQuery, state: FSMContext):
    remind = query.data.split('_')[1]
    if not remind.isdigit():
        if remind == 'none':
            return
        remind = None
    else:
        remind = int(remind)

    keyboard = InlineKeyboardMarkup()
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
    remind_buttons = [[24, 'За 24 часа'], [12, 'За 12 часов'], [6, 'За 6 часов'], [2, 'За 2 часа'],
                      ['no', 'Не напоминать']]
    if not (time_book > time_plus_24):
        remind_buttons[0][0] = 'none'
        remind_buttons[0][1] = ''
    if not (time_book > time_plus_12):
        remind_buttons[1][0] = 'none'
        remind_buttons[1][1] = ''
    if not (time_book > time_plus_6):
        remind_buttons[2][0] = 'none'
        remind_buttons[2][1] = ''
    if not (time_book > time_plus_2):
        remind_buttons[3][0] = 'none'
        remind_buttons[3][1] = ''
    _remind = remind
    if not _remind:
        _remind = 'no'
    for i in range(len(remind_buttons)):
        if _remind == remind_buttons[i][0]:
            remind_buttons[i][1] = buttons.check_mark + remind_buttons[i][1]

    keyboard.add(InlineKeyboardButton(remind_buttons[0][1], callback_data=f'remind_{remind_buttons[0][0]}'),
                 InlineKeyboardButton(remind_buttons[1][1], callback_data=f'remind_{remind_buttons[1][0]}'))
    keyboard.add(InlineKeyboardButton(remind_buttons[2][1], callback_data=f'remind_{remind_buttons[2][0]}'),
                 InlineKeyboardButton(remind_buttons[3][1], callback_data=f'remind_{remind_buttons[3][0]}'))
    keyboard.add(InlineKeyboardButton(remind_buttons[4][1], callback_data=f'remind_{remind_buttons[4][0]}'))
    await query.message.edit_reply_markup(reply_markup=keyboard)
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
            table_range, table_joint_range, table = await create_order_without_table(data.get('restaurant'), data.get('how_many'),
                                                           data.get('date_booking'),
                                                           data.get('exact_time'), user.name, user.phone, order.id)
        else:
            table_range, table_joint_range, table = await create_order(data.get('restaurant'), data.get('how_many'), data.get('date_booking'),
                                             data.get('exact_time'), data.get('table'), user.name, user.phone, order.id)
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
        await set_keyboard_admin(query.message,
                                     await safe_for_markdown(msg_text), parse_mode=types.ParseMode.MARKDOWN_V2)
        # await admin_sender(msg_text_admin)

    await state.finish()

async def admin_sender(msg_text, restaurant_number):
    await AdminSend.create(text=msg_text, restaurant=restaurant_number)

async def remind_handler_2(query: CallbackQuery, state: FSMContext, remind):
    keyboard = InlineKeyboardMarkup()
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
            table_range, table_joint_range, table = await create_order_without_table(data.get('restaurant'), data.get('how_many'),
                                                           data.get('date_booking'),
                                                           data.get('exact_time'), user.name, user.phone, order.id)
        else:
            table_range, table_joint_range, table = await create_order(data.get('restaurant'), data.get('how_many'), data.get('date_booking'),
                                             data.get('exact_time'), data.get('table'), user.name, user.phone, order.id)
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

        await set_keyboard_admin(query.message,
                                     await safe_for_markdown(msg_text), parse_mode=types.ParseMode.MARKDOWN_V2)
        await admin_sender(msg_text_admin, data.get('restaurant'))
    await state.finish()


@dp.callback_query_handler(text='wrong_final_confirm', state=Booking.final)
async def wrong_final_confirm(query: CallbackQuery, state: FSMContext):
    await Booking.name.set()
    await register(query, state)


@dp.message_handler(commands=['del'])
async def del_handler(message: types.Message, state: FSMContext):
    m = message.text.split()
    if len(m) != 2:
        await message.answer(msgs.wrong_format_del)
        return
    if not m[1].isdigit():
        await message.answer(msgs.wrong_format_del)
        return
    order = await Order.get_or_none(id=int(m[1]))
    if not order:
        await message.answer(msgs.no_such_id_order)
        return
    await DelBooking.id.set()
    await state.update_data(id=int(m[1]))
    await DelBooking.confirmation.set()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes, callback_data='del_booking_yes'),
                 InlineKeyboardButton(buttons.no, callback_data='del_booking_no'))
    msg_text = msgs.del_booking_confirmation.format(m[1], msgs.restaurants[(await order.restaurant).self_id],
                                                    (await order.user).name, (await order.user).phone, order.date+' '+order.time, order.how_many,  msgs.guests[order.how_many],
                                                    order.table_range, f'{order.table_joint_range} в общих' if order.table_joint_range else '')
    msg_id = await message.answer(msg_text, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains='del_booking_', state=DelBooking.confirmation)
async def del_booking_handler(query: CallbackQuery, state: FSMContext):
    if query.data.split('_')[2] == 'yes':
        async with state.proxy() as data:
            id = data['id']
            order = await Order.get_or_none(id=id)
            if not order:
                await query.message.answer(msgs.no_such_id_order)
                await state.finish()
                return
            if await OrderToDelete.get_or_none(order=order):
                await query.message.answer(msgs.order_in_deleting_queue)
                await state.finish()
                return
            now = datetime.datetime.now(tz=config.timezone)
            now_plus_5 = now + datetime.timedelta(minutes=5)
            now_plus_5_str = now_plus_5.strftime('%m.%d.%Y %H:%M')
            await OrderToDelete.create(order=order, datetime=now_plus_5_str)
            # await delete_order(order.restaurant, order.date, order.table_range)
            # await order.delete()
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(buttons.restore_order, callback_data=f'restore_order_{order.id}'))
        await query.message.answer(msgs.del_booking_in_order, reply_markup=keyboard)
        await state.finish()
    else:
        await state.finish()
        await query.message.answer(msgs.del_booking_cancelled)

@dp.callback_query_handler(text_contains='restore_order_')
async def restore_order(query: CallbackQuery, state: FSMContext):
    order_id = int(query.data.split('_')[2])
    order = await Order.get_or_none(id=order_id)
    if not order:
        await query.answer(msgs.there_is_no_order)
        return
    order_to_delete = await OrderToDelete.get_or_none(order=order)
    if not order_to_delete:
        await query.answer(msgs.order_not_in_deleting_queue)
        return
    await order_to_delete.delete()
    await query.message.answer(msgs.order_restored)


@dp.message_handler(text=buttons.menu, state=Booking)
async def settings_yes_no(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes_interrupt, callback_data='yes_interrupt'),
                 InlineKeyboardButton(buttons.no_interrupt, callback_data='no_interrupt'))
    await message.answer(msgs.interrupting_booking, reply_markup=keyboard)


@dp.callback_query_handler(text='yes_interrupt', state=Booking)
async def yes_interrupt(query: CallbackQuery, state: FSMContext):
    await state.finish()
    await settings(query.message, state)


@dp.callback_query_handler(text='no_interrupt', state=Booking)
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

@dp.message_handler(text=buttons.menu, state='*')
async def settings(message: types.Message, state: FSMContext):
    if state:
        if await state.get_data() != {}:
            await message.answer(msgs.interrupted)
        await state.finish()
    if message.chat.id in admins:
        await set_keyboard_admin(message, msgs.you_are_admin.format(config.BOT_NAME))
        return


@dp.message_handler(text=buttons.admin_menu)
async def admin_menu(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.broadcast, callback_data='broadcast'),
                 InlineKeyboardButton(buttons.tags, callback_data='admin_tags'))
    msg_id = await message.answer(msgs.admin_menu, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text='admin_tags')
@dp.callback_query_handler(text='admin_tags', state=AddTag.name)
@dp.callback_query_handler(text='admin_tags', state=DelTag.name)
async def admin_tags(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    if state:
        await state.finish()
    tags = await Tag.filter()
    text = msgs.tag_list.format('\n'.join([i.name for i in tags]))
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.add_tag, callback_data='add_tag'))
    keyboard.add(InlineKeyboardButton(buttons.del_tag, callback_data='del_tag'))
    await query.message.answer(text)
    msg_id = await query.message.answer(msgs.tag_list2, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.message_handler(text=buttons.tags)
async def admin_tags(message: types.Message):
    if message.chat.id not in admins:
        return
    tags = await Tag.all().order_by('id')
    text = msgs.menu
    # text = msgs.tag_list.format('\n'.join([i.name for i in tags]))
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        check = ''
        if i.visible:
            check = buttons.check_mark
        keyboard.add(InlineKeyboardButton(check+' '+i.name, callback_data=f'update_visible_{i.id}'))
    keyboard.add(InlineKeyboardButton(buttons.add_tag, callback_data='add_tag'), InlineKeyboardButton(buttons.del_tag, callback_data='del_tag'))
    await set_keyboard_back(message, text)
    msg_id = await message.answer(msgs.tag_list2, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains='update_visible_')
async def update_visible(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    tag_id = query.data.split('_')[2]
    tag = await Tag.get(id=int(tag_id))
    tag.visible = not tag.visible
    await tag.save()
    tags = await Tag.all().order_by('id')
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        check = ''
        if i.visible:
            check = buttons.check_mark
        keyboard.add(InlineKeyboardButton(check + ' ' + i.name, callback_data=f'update_visible_{i.id}'))
    keyboard.add(InlineKeyboardButton(buttons.add_tag, callback_data='add_tag'),
                 InlineKeyboardButton(buttons.del_tag, callback_data='del_tag'))
    await query.message.edit_reply_markup(keyboard)

async def admin_tags2(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    if state:
        await state.finish()
    tags = await Tag.all().order_by('id')
    text = msgs.menu
    # text = msgs.tag_list.format('\n'.join([i.name for i in tags]))
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        check = ''
        if i.visible:
            check = buttons.check_mark
        keyboard.add(InlineKeyboardButton(check + ' ' + i.name, callback_data=f'update_visible_{i.id}'))
    keyboard.add(InlineKeyboardButton(buttons.add_tag, callback_data='add_tag'),
                 InlineKeyboardButton(buttons.del_tag, callback_data='del_tag'))
    await set_keyboard_back(message, text)
    msg_id = await message.answer(msgs.tag_list2, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text='add_tag')
async def add_tag(query: CallbackQuery):
    if query.message.chat.id not in admins:
        return
    await AddTag.name.set()
    msg_id = await query.message.answer(msgs.add_tag)
    await set_message_id(msg_id)


@dp.message_handler(state=AddTag.name)
async def add_tag_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    await Tag.create(name=message.text)
    await state.finish()
    await message.answer(msgs.tag_added.format(message.text))
    await admin_tags2(message, state)


@dp.callback_query_handler(text='del_tag')
async def del_tag(query: CallbackQuery):
    if query.message.chat.id not in admins:
        return
    tags = await Tag.filter()
    await DelTag.name.set()
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        keyboard.add(InlineKeyboardButton(i.name, callback_data=f'del_tag_{i.id}'))
    msg_id = await query.message.answer(msgs.del_tag, reply_markup=keyboard)
    await set_message_id(msg_id)


async def del_tag2(message: types.Message):
    if message.chat.id not in admins:
        return
    tags = await Tag.filter()
    await DelTag.name.set()
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        keyboard.add(InlineKeyboardButton(i.name, callback_data=f'del_tag_{i.id}'))
    msg_id = await message.answer(msgs.del_tag, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains='del_tag_', state=DelTag.name)
async def del_tag_handler(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    # await state.finish()
    to_delete = int(query.data.split('_')[2])
    await state.update_data(name=to_delete)
    await DelTag.next()
    tag = await Tag.get(id=to_delete)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.confirm, callback_data=f'del_tagconfirm_{to_delete}'))
    msg_id = await query.message.answer(msgs.del_tag_confirm.format(tag.name), reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains='del_tagconfirm_', state=DelTag.confirmation)
async def del_tagconfirm(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    await state.finish()
    to_delete = int(query.data.split('_')[2])
    tag = await Tag.get(id=to_delete)
    await tag.delete()
    await tag.save()

    await query.message.answer(msgs.tag_deleted.format(tag.name))
    await admin_tags2(query.message, state)


@dp.callback_query_handler(text='broadcast')
async def broadcast_handler(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    await Broadcast.text.set()
    await set_keyboard_back(query.message, msgs.enter_text)


@dp.message_handler(text=buttons.broadcast)
async def broadcast_menu(message: types.Message, state: FSMContext, flag=False):
    if message.chat.id not in admins:
        return
    await Broadcast.text.set()
    await set_keyboard_back(message, msgs.enter_text)


@dp.message_handler(state=Broadcast.text)
async def broadcast_text_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    await state.update_data(text=message.text)
    await Broadcast.next()
    await message.answer(msgs.now_message_is)
    await message.answer((await state.get_data()).get('text'))
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.add_photo, callback_data='add_photo'))
    keyboard.add(InlineKeyboardButton(buttons.add_video, callback_data='add_video'))
    keyboard.add(InlineKeyboardButton(buttons.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(buttons.all_ready, callback_data='all_ready'))
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=keyboard)
    await set_message_id(msg_id)


async def broadcast_text_handler2(message: types.Message, state: FSMContext):
    await message.answer(msgs.now_message_is)
    await message.answer((await state.get_data()).get('text'))
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.add_photo, callback_data='add_photo'))
    keyboard.add(InlineKeyboardButton(buttons.add_video, callback_data='add_video'))
    keyboard.add(InlineKeyboardButton(buttons.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(buttons.all_ready, callback_data='all_ready'))
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=keyboard)
    await set_message_id(msg_id)



@dp.callback_query_handler(state=Broadcast.next_step)
async def broadcast_next_step_handler(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    if query.data in ['add_photo', 'add_video', 'add_link']:
        await Broadcast.next()
        if query.data == 'add_photo':
            await query.message.answer(msgs.send_photo)
        elif query.data == 'add_video':
            await query.message.answer(msgs.send_video)
        elif query.data == 'add_link':
            await query.message.answer(msgs.send_link)

    elif query.data == 'all_ready':
        await Broadcast.conf_.set()
        cur_atachments = (await state.get_data()).get('attachment')
        if not cur_atachments:
            cur_atachments = {'photos': [],
                              'videos': [],
                              'links': []}
        keyboard = InlineKeyboardMarkup()
        if cur_atachments.get('links'):
            for i in cur_atachments['links']:
                keyboard.add(InlineKeyboardButton(i[0], url=i[1]))
        if cur_atachments.get('photos'):
            await query.message.answer_photo(cur_atachments['photos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        elif cur_atachments.get('videos'):
            await query.message.answer_video(cur_atachments['videos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        else:
            await query.message.answer((await state.get_data()).get('text'), reply_markup=keyboard)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(buttons.all_is_good, callback_data='all_is_good'))
        msg_id = await query.message.answer(msgs.all_is_good, reply_markup=keyboard)
        await set_message_id(msg_id)


@dp.callback_query_handler(text='all_is_good', state=Broadcast.conf_)
async def conf_(query: CallbackQuery, state: FSMContext):
    await Broadcast.tags.set()
    keyboard = InlineKeyboardMarkup()
    # keyboard.add(InlineKeyboardButton(buttons.choose_all_broadcast, callback_data='choose_all_broadcast'))
    tags = await Tag.filter(visible=True)
    for i in tags:
        keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_broadcast_tag_{i.id}'))
    await query.message.answer(msgs.choose_tags_for_broadcast)
    msg_id = await query.message.answer(msgs.chosen_are_marked, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.message_handler(content_types=ContentType.PHOTO, state=Broadcast.attachment)
async def photo_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    cur_atachments = (await state.get_data()).get('attachment')
    if not cur_atachments:
        cur_atachments = {'photos': [],
                          'videos': [],
                          'links': []}
    file_id = message.photo[-1].file_id
    cur_atachments['photos'].append(file_id)
    await state.update_data(attachment=cur_atachments)
    await Broadcast.next_step.set()
    await message.answer(msgs.now_message_is)
    keyboard = InlineKeyboardMarkup()
    if cur_atachments.get('links'):
        for i in cur_atachments['links']:
            keyboard.add(InlineKeyboardButton(i[0], url=i[1]))
    await message.answer_photo(file_id, caption=(await state.get_data()).get('text'), reply_markup=keyboard)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(buttons.all_ready, callback_data='all_ready'))
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.message_handler(content_types=ContentType.VIDEO, state=Broadcast.attachment)
async def video_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    cur_atachments = (await state.get_data()).get('attachment')
    if not cur_atachments:
        cur_atachments = {'photos': [],
                          'videos': [],
                          'links': []}
    file_id = message.video.file_id
    cur_atachments['videos'].append(file_id)
    await state.update_data(attachment=cur_atachments)
    await Broadcast.next_step.set()
    await message.answer(msgs.now_message_is)
    keyboard = InlineKeyboardMarkup()
    if cur_atachments.get('links'):
        for i in cur_atachments['links']:
            keyboard.add(InlineKeyboardButton(i[0], url=i[1]))
    await message.answer_video(file_id, caption=(await state.get_data()).get('text'), reply_markup=keyboard)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(buttons.all_ready, callback_data='all_ready'))
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.message_handler(content_types=ContentType.TEXT, state=Broadcast.attachment)
async def link_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    text = message.text
    cur_atachments = (await state.get_data()).get('attachment')
    if not cur_atachments:
        cur_atachments = {'photos': [],
                          'videos': [],
                          'links': []}
    cur_atachments['links'].append([text])
    await state.update_data(attachment=cur_atachments)
    await Broadcast.attachment2.set()
    await message.answer(msgs.send_link2)

@dp.message_handler(content_types=ContentType.TEXT, state=Broadcast.attachment2)
async def link2_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    text = message.text
    is_url = validators.url(text)
    if not is_url:
        await message.answer(msgs.wrong_format_link)
        return
    cur_atachments = (await state.get_data()).get('attachment')
    cur_atachments['links'][-1].append(text)
    await state.update_data(attachment=cur_atachments)
    await Broadcast.next_step.set()
    await message.answer(msgs.now_message_is)
    keyboard = InlineKeyboardMarkup()
    if cur_atachments.get('links'):
        for i in cur_atachments['links']:
            keyboard.add(InlineKeyboardButton(i[0], url=i[1]))
    if cur_atachments.get('photos'):
        await message.answer_photo(cur_atachments['photos'][0], caption=(await state.get_data()).get('text'),
                                   reply_markup=keyboard)
    elif cur_atachments.get('videos'):
        await message.answer_video(cur_atachments['videos'][0], caption=(await state.get_data()).get('text'),
                                   reply_markup=keyboard)
    else:
        await message.answer((await state.get_data()).get('text'), reply_markup=keyboard)
    keyboard = InlineKeyboardMarkup()
    if not cur_atachments.get('photos') and not cur_atachments.get('videos'):
        keyboard.add(InlineKeyboardButton(buttons.add_photo, callback_data='add_photo'))
        keyboard.add(InlineKeyboardButton(buttons.add_video, callback_data='add_video'))
    keyboard.add(InlineKeyboardButton(buttons.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(buttons.all_ready, callback_data='all_ready'))
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=keyboard)
    await set_message_id(msg_id)


@dp.callback_query_handler(text_contains='choose_broadcast_tag_', state=Broadcast.tags)
async def choose_broadcast_tag_handler(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    tag_id = int(query.data.split('_')[3])
    tags_current = (await state.get_data()).get('tags')
    tags = []
    if tags_current is None:
        tags = [tag_id]
    else:
        if tag_id not in tags_current:
            tags = tags_current + [tag_id]
        else:
            tags_current.pop(tags_current.index(tag_id))
            tags = tags_current
    await state.update_data(tags=tags)
    keyboard = InlineKeyboardMarkup()
    tags_all = await Tag.filter(visible=True)
    for i in tags_all:
        if i.id in tags:
            keyboard.add(
                InlineKeyboardButton(buttons.check_mark + i.name, callback_data=f'choose_broadcast_tag_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_broadcast_tag_{i.id}'))
    if len(tags):
        keyboard.add(InlineKeyboardButton(buttons.next, callback_data='tags_chosen'))
    await query.message.edit_reply_markup(keyboard)


@dp.callback_query_handler(text='tags_chosen', state=Broadcast.tags)
async def broadcast_next(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    await Broadcast.confirmation.set()
    async with state.proxy() as data:
        tags = await Tag.filter(pk__in=data['tags'])
        tags_text = '\n'.join([i.name for i in tags])
        text = msgs.message_for_broadcast.format(tags_text)
        await query.message.answer(text)
        cur_atachments = (await state.get_data()).get('attachment')
        if not cur_atachments:
            cur_atachments = {'photos': [],
                              'videos': [],
                              'links': []}
        keyboard = InlineKeyboardMarkup()
        if cur_atachments.get('links'):
            for i in cur_atachments['links']:
                keyboard.add(InlineKeyboardButton(i[0], url=i[1]))
        if cur_atachments.get('photos'):
            await query.message.answer_photo(cur_atachments['photos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        elif cur_atachments.get('videos'):
            await query.message.answer_video(cur_atachments['videos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        else:
            await query.message.answer((await state.get_data()).get('text'), reply_markup=keyboard)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(buttons.yes, callback_data='broadcast_confirm'),
                     InlineKeyboardButton(buttons.no, callback_data='broadcast_wrong'))
        msg_id = await query.message.answer(msgs.all_is_good, reply_markup=keyboard)
        await set_message_id(msg_id)


@dp.callback_query_handler(text='broadcast_wrong', state=Broadcast.confirmation)
async def broadcast_wrong(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    await state.update_data(tags=None)
    await state.update_data(text=None)
    await state.update_data(attachment=None)
    await broadcast_handler(query, state)


@dp.callback_query_handler(text='broadcast_confirm', state=Broadcast.confirmation)
async def broadcast_confirm(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    async with state.proxy() as data:
        tags = await Tag.filter(pk__in=data['tags']).values_list('id', flat=True)
        tags_name = await Tag.filter(pk__in=data['tags'])

        tags_json = {}
        for i, j in enumerate(tags_name):
            tags_json[i] = j.name
        cur_atachments = (await state.get_data()).get('attachment')
        links_json = {}
        photo = None
        video = None
        if cur_atachments.get('links'):
            for i, j in enumerate(cur_atachments['links']):
                links_json[i] = j
        if cur_atachments.get('photos'):
            photo = cur_atachments['photos'][0]
        if cur_atachments.get('videos'):
            video = cur_atachments['videos'][0]
        text = (await state.get_data()).get('text')
        path = None
        if photo or video:
            file = await bot.get_file(photo if photo else video)
            path = config.PATH_TO_SAVE + file.file_id
            with open(path, 'wb') as f:
                download_file = await bot.download_file(file.file_path, f)
            if photo:
                photo = path
            elif video:
                video = path

        users_to_send = set(await TagSubscription.filter(tag__id__in=tags).values_list('user_id', flat=True))
        for i in users_to_send:
            user = await User.get(id=i)
            await BroadcastModel.create(chat_id=user.chat_id, text=text, link=links_json, photo=photo, video=video)
            # await broadcaster_queue.put([user.chat_id, data['text']])
        await BroadcastHistory.create(tags=tags_json, text=text, link=links_json, photo=photo, video=video)

        await create_broadcast_history(tags_name, text, photo, video, links_json)
        await set_keyboard_admin(query.message, msgs.starting_broadcast)
        await state.finish()


async def create_broadcast_history(tags, text, photo, video, links):
    tags = [f'#{i.name.replace(" ", "_")}' for i in tags]
    tags_text = ' '.join(tags) + ' ⬇️'
    await bot.send_message(config.HISTORY_CHANNEL, tags_text)
    keyboard = InlineKeyboardMarkup()
    for i in links:
        keyboard.add(InlineKeyboardButton(links[i][0], url=links[i][1]))
    if photo:
        await bot.send_photo(config.HISTORY_CHANNEL, open(photo, 'rb'), caption=text, reply_markup=keyboard)
    elif video:
        await bot.send_video(config.HISTORY_CHANNEL, open(video, 'rb'), caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(config.HISTORY_CHANNEL, text, reply_markup=keyboard)


@dp.message_handler(text=buttons.broadcast_history)
async def broadcast_history(message: types.Message, state: FSMContext, flag=False):
    if message.chat.id not in admins:
        return
    broadcast_history_all = await BroadcastHistory.all().count()
    broadcast_history_photos = await BroadcastHistory.filter(photo__not_isnull=True).count()
    broadcast_history_videos = await BroadcastHistory.filter(video__not_isnull=True).count()
    broadcast_history_links = await BroadcastHistory.filter(link__not_isnull=True).count()
    chat_link = await bot.export_chat_invite_link(config.HISTORY_CHANNEL)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.chat_link, url=chat_link))
    await message.answer(msgs.broadcast_history.format(broadcast_history_all, broadcast_history_photos,
                                                       broadcast_history_videos,
                                                       broadcast_history_links), reply_markup=keyboard)



@dp.callback_query_handler(text_contains='broadcast_history_tag_', state=BroadcastHistoryStates.tags)
async def broadcast_history_tag(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    tag_id = int(query.data.split('_')[3])
    tags_current = (await state.get_data()).get('tags')
    tags = []
    if tags_current is None:
        tags = [tag_id]
    else:
        if tag_id not in tags_current:
            tags = tags_current + [tag_id]
        else:
            tags_current.pop(tags_current.index(tag_id))
            tags = tags_current
    await state.update_data(tags=tags)
    keyboard = InlineKeyboardMarkup()
    tags_all = await Tag.filter(visible=True)
    for i in tags_all:
        if i.id in tags:
            keyboard.add(
                InlineKeyboardButton(buttons.check_mark + i.name, callback_data=f'broadcast_history_tag_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'broadcast_history_tag_{i.id}'))
    await query.message.edit_reply_markup(keyboard)


@dp.message_handler(text=buttons.next, state=BroadcastHistoryStates.tags)
async def broadcast_next3(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    if (await state.get_data()).get('tags') is None or len((await state.get_data()).get('tags')) == 0:
        await message.answer(msgs.choose_no_one_tags)
        await broadcast_history(message, state, True)
        return
    await BroadcastHistoryStates.next()
    tags_state = (await state.get_data()).get('tags')
    tags_obj = set(await Tag.filter(id__in=tags_state).values_list('name', flat=True))
    broadcast_history_ = await BroadcastHistory.all().order_by('-time')
    await BroadcastHistoryStates.id.set()
    text = msgs.broadcast_history
    good_history = []
    for i, j in enumerate(broadcast_history_):
        e = [k in list(j.tags.values()) for k in tags_obj]
        if any(e):
            good_history.append(j)
    for j in good_history[:5]:
        tags = ', '.join(j.tags.values())
        text += msgs.broadcast_history_str.format(j.id, j.time.strftime('%d.%m.%Y'), tags, j.text)
    keyboard = InlineKeyboardMarkup()
    if len(good_history) > 5:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton(buttons.page_next, callback_data='broadcast_history_page_1'),
                     )
    else:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton(' ', callback_data=' '),
                     )
    msg_id = await message.answer(text, reply_markup=keyboard)
    await set_message_id(msg_id)
    # text += msgs.broadcast_history_end
    await set_keyboard_back(message, msgs.broadcast_history_end)


@dp.callback_query_handler(text_contains='broadcast_history_page_', state=BroadcastHistoryStates)
async def broadcast_history_page(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    page = int(query.data.split('_')[3])
    tags_state = (await state.get_data()).get('tags')
    tags_obj = set(await Tag.filter(id__in=tags_state).values_list('name', flat=True))
    broadcast_history_ = await BroadcastHistory.all().order_by('-time')
    text = msgs.broadcast_history
    good_history = []
    for i, j in enumerate(broadcast_history_):
        e = [k in list(j.tags.values()) for k in tags_obj]
        if any(e):
            good_history.append(j)
    for j in good_history[page * 5:page * 5 + 5]:
        tags = ', '.join(j.tags.values())
        text += msgs.broadcast_history_str.format(j.id, j.time.strftime('%d.%m.%Y'), tags, j.text)
    keyboard = InlineKeyboardMarkup()
    if len(good_history[page * 5:page * 5 + 5]) == 5:
        if page != 0:
            keyboard.add(InlineKeyboardButton(buttons.page_back, callback_data=f'broadcast_history_page_{page - 1}'),
                         InlineKeyboardButton(buttons.page_next, callback_data=f'broadcast_history_page_{page + 1}'))
        else:
            keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                         InlineKeyboardButton(buttons.page_next, callback_data=f'broadcast_history_page_{page + 1}'))
    else:
        keyboard.add(InlineKeyboardButton(buttons.page_back, callback_data=f'broadcast_history_page_{page - 1}'),
                     InlineKeyboardButton(' ', callback_data=' '))
    await query.message.edit_text(text, reply_markup=keyboard)



@dp.message_handler(state=BroadcastHistoryStates.wait)
@dp.message_handler(state=BroadcastHistoryStates.id)
async def broadcast_history_id(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    if not message.text.isdigit():
        await message.answer(msgs.no_such_id)
        await message.answer(msgs.broadcast_history_end)
        return
    id = int(message.text)
    broadcast_obj = await BroadcastHistory.get_or_none(id=id)
    if not broadcast_obj:
        await message.answer(msgs.no_such_id)
        await message.answer(msgs.broadcast_history_end)
        return
    if broadcast_obj.content_type == 'photo':
        await message.answer_photo(open(broadcast_obj.file_id, 'rb'), broadcast_obj.text)
    elif broadcast_obj.content_type == 'video':
        await message.answer_video(open(broadcast_obj.file_id, 'rb'), caption=broadcast_obj.text)
    else:
        await message.answer(broadcast_obj.text)
    await BroadcastHistoryStates.wait.set()
    await message.answer(msgs.broadcast_history_end)


async def on_startup(*args):
    await init()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
