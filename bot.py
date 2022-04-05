import calendar
import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, callback_query, ParseMode, ReplyKeyboardMarkup, \
    KeyboardButton, InputMedia, InputMediaPhoto, CallbackQuery
from aiogram.utils import executor, exceptions
from aiogram.utils.deep_linking import get_start_link, decode_payload
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import buttons
import config
import asyncio
from models import *
import messages as msgs
from google_sheet_functions import *
import datetime
import logging
import random
import re
from aiogram.types import ChatActions
from img_helper import get_colored_image
from config import admins, broadcaster_queue
from logging_middleware import LoggingMiddleware
import phonenumbers
import uuid

bot = Bot(config.BOT_TOKEN)
storage = MemoryStorage()  # внутреннее хранилище бота, позволяющее отслеживать FMS (Finite State Maschine)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(
    filename=config.LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
log = logging.getLogger('bot')

phone_regex = '^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'

excluded_from_middleware = ['PREV-YEAR_', 'NEXT-YEAR_', 'PREV-MONTH_', 'NEXT-MONTH_', 'settings',
                            'yes_interrupt', 'no_interrupt', 'new_booking', 'presence_yes_', 'presence_maybe_',
                            'presence_no']

group_commands = ['/enableinfo', '/disableinfo']


# для того, чтоб пропадали крутилки на андроиде
class MiddlewareAnswerCallback(BaseMiddleware):
    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        if callback_query.data == ' ':
            await callback_query.answer(msgs.not_active)
        if not any([i in callback_query.data for i in excluded_from_middleware]):
            if callback_query.message.message_id != message_ids.get(callback_query.message.chat.id):
                await callback_query.answer(msgs.alert, show_alert=True)
        await callback_query.answer()


class MiddlewareOnlyPrivate(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.type != 'private':
            if not any([message.text.startswith(i) for i in group_commands]):
                raise CancelHandler()


dp.middleware.setup(MiddlewareAnswerCallback())
dp.middleware.setup(MiddlewareOnlyPrivate())


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


message_ids = {}


async def safe_for_markdown(text):
    excluded = ['.', ':', '-', '~', '!', '+']
    flag = False
    l = len(text)
    text_new = ''
    for i in range(l):
        if text[i] in excluded and text[i - 1] != '\\':
            text_new += fr'\{text[i]}'
        elif text[i] == '(':
            if text[i - 1] != ']' and text[i - 1] != '\\':
                text_new += fr'\{text[i]}'
                flag = True
            else:
                text_new += text[i]
        elif text[i] == ')':
            if flag and text[i - 1] != '\\':
                text_new += fr'\{text[i]}'
                flag = False
            else:
                text_new += text[i]

        else:
            text_new += text[i]
    if '#' in text_new:
        text_new = text_new.replace('\\\\\\', '\\')

    return text_new


async def is_phone_valid(text):
    text = text.strip()
    try:
        phone = phonenumbers.parse(text)
        if phonenumbers.is_possible_number(phone) and phonenumbers.is_valid_number(phone):
            return text

    except:
        pattern = re.compile(phone_regex)
        phone = pattern.search(text)
        if phone and phone.string == text:
            return text
    return None


russian_months = {1: 'Янв', 2: 'Февр', 3: 'Март', 4: 'Апр', 5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Авг', 9: 'Сент',
                  10: 'Окт', 11: 'Нояб', 12: 'Дек'}


async def generate_calendar(year, month, day, now, days_for_booking, selected=None, delete_empty=False):
    lower_bound = now.date()
    upper_bound = lower_bound + datetime.timedelta(days=days_for_booking)
    inline_kb = InlineKeyboardMarkup(row_width=8)
    inline_kb.row()
    inline_kb.insert(InlineKeyboardButton(' ', callback_data=' '))
    inline_kb.insert(InlineKeyboardButton(
        f'{russian_months.get(month)} {str(year)}',
        callback_data=' '
    ))
    inline_kb.insert(InlineKeyboardButton(' ', callback_data=' '))
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


@dp.message_handler(text=buttons.back, state=Booking.restaurant)
async def back_to_main(message: types.Message, state: FSMContext):
    await settings_(message, state)


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


@dp.message_handler(text=buttons.back, state=Booking.confirm_table)
async def back_to_tables2(message: types.Message, state: FSMContext):
    await Booking.table.set()
    await rechose_table(message, state)


@dp.message_handler(text=buttons.back, state=Booking.confirmation)
async def back_to_tables(message: types.Message, state: FSMContext):
    await Booking.table.set()
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


@dp.message_handler(text=buttons.back, state=Changing.name)
@dp.message_handler(text=buttons.back, state=Changing.phone)
async def back_to_change_contact(message: types.Message, state: FSMContext):
    await state.finish()
    await settings_menu(message, state)


@dp.message_handler(text=buttons.confirm_choise, state=ChangeTags.tag)
@dp.message_handler(text=buttons.back, state=ChangeTags.tag)
async def back_to_tags2(message: types.Message, state: FSMContext):
    await state.finish()
    await change_tag3(message, state)


@dp.message_handler(text=buttons.back, state=Settings.change_contact)
@dp.message_handler(text=buttons.back, state=Settings.change_tag)
async def back_to_main_settings(message: types.Message, state: FSMContext):
    await state.finish()
    await settings(message, state)


@dp.message_handler(text=buttons.back)
async def back_to_menu(message: types.Message):
    await settings(message, dp.current_state())


@dp.callback_query_handler(text='settings', state='*')
async def settings_callback(query: CallbackQuery, state: FSMContext):
    await settings(query.message, state)


@dp.message_handler(text=buttons.menu, state=Booking)
async def settings_yes_no(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes_interrupt, callback_data='yes_interrupt'),
                 InlineKeyboardButton(buttons.no_interrupt, callback_data='no_interrupt'))
    await message.answer(msgs.interrupting_booking, reply_markup=keyboard)


@dp.callback_query_handler(text='yes_interrupt', state=Booking)
async def yes_interrupt(query: CallbackQuery, state: FSMContext):
    await state.finish()
    await settings(query.message, state, True)


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


@dp.message_handler(text=buttons.back_to_menu)
@dp.message_handler(text=buttons.back_to_menu, state=Changing)
async def settings_(message: types.Message, state: FSMContext):
    if not state:
        state = dp.current_state()
    else:
        await state.finish()
    await settings(message, state)


@dp.message_handler(text=buttons.back_to_settings)
@dp.message_handler(text=buttons.back_to_settings, state=Changing)
async def settings2_(message: types.Message, state: FSMContext):
    if not state:
        state = dp.current_state()
    else:
        await state.finish()
    await settings_menu(message, state)


@dp.message_handler(text=buttons.menu, state='*')
async def settings(message: types.Message, state: FSMContext, interrupted=False):
    if state:
        if await state.get_data() != {}:
            await message.answer(msgs.interrupted)
        await state.finish()

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.new_booking))
    keyboard.add(KeyboardButton(buttons.settings_menu))
    msg_text = msgs.main_menu.format(config.restaurant_name) if not interrupted else msgs.interrupted_booking
    await message.answer(msg_text, reply_markup=keyboard)


@dp.message_handler(text=buttons.settings_menu)
@dp.message_handler(text=buttons.settings_menu, state="*")
async def settings_menu(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.change_name, callback_data='change_name'))
    keyboard.add(InlineKeyboardButton(buttons.change_phone, callback_data='change_phone'))

    if state:
        await state.finish()
    user = await User.get_or_none(chat_id=message.chat.id)
    await Settings.change_contact.set()

    if user:
        name = user.name if user.name else 'нет'
        phone = user.phone if user.phone else 'нет'

        await set_keyboard_settings(message, msgs.your_data, parse_mode=types.ParseMode.MARKDOWN_V2)

        msg_id = await message.answer(msgs.current_name_phone_tags.format(name, phone), reply_markup=keyboard)
    else:
        await set_keyboard_settings(message, msgs.your_data, parse_mode=types.ParseMode.MARKDOWN_V2)
        msg_id = await message.answer(msgs.current_name_phone_tags.format('нет', 'нет'), reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='change_contact')
async def change_contact(query: CallbackQuery):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.change_name, callback_data='change_name'))
    keyboard.add(InlineKeyboardButton(buttons.change_phone, callback_data='change_phone'))
    await Settings.change_contact.set()
    user = await User.get_or_none(chat_id=query.message.chat.id)
    if user:
        name = user.name if user.name else 'нет'
        phone = user.phone if user.phone else 'нет'

        await set_keyboard_settings(query.message, msgs.current_name_phone.format(name, phone))

        msg_id = await query.message.answer(msgs.if_want_change, reply_markup=keyboard)
    else:
        await set_keyboard_settings(query.message, msgs.current_name_phone.format('нет', 'нет'))
        msg_id = await query.message.answer(msgs.if_want_change, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


async def change_contact2(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.change_name, callback_data='change_name'))
    keyboard.add(InlineKeyboardButton(buttons.change_phone, callback_data='change_phone'))
    user = await User.get_or_none(chat_id=message.chat.id)
    await Settings.change_contact.set()
    if user:
        name = user.name if user.name else 'нет'
        phone = user.phone if user.phone else 'нет'

        await set_keyboard_settings(message, msgs.current_name_phone.format(name, phone))

        msg_id = await message.answer(msgs.if_want_change, reply_markup=keyboard)
    else:
        await set_keyboard_settings(message, msgs.current_name_phone.format('нет', 'нет'))
        msg_id = await message.answer(msgs.if_want_change, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='change_tags')
async def change_tag(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.choose_all, callback_data='choose_all_tags'),
                 InlineKeyboardButton(buttons.choose_no_one, callback_data='choose_no_one_tags'))
    keyboard.add(InlineKeyboardButton(buttons.choose_what_to_on, callback_data='choose_what_to_on_tags'))
    user = await User.get_or_none(chat_id=query.message.chat.id)
    await Settings.change_tag.set()
    tags_all = await Tag.filter(visible=True)
    if user:
        tags = await TagSubscription.filter(user=user)
        tag_names = []
        for i in tags:
            tag_names.append((await i.tag).name)
        if not len(tag_names):
            tag_names.append('нет')
        await set_keyboard_settings(query.message, msgs.current_tags.format('\n'.join(tag_names)))
    else:
        await set_keyboard_settings(query.message, msgs.current_tags.format('нет'))
    msg_id = await query.message.answer(msgs.if_want_change_tags.format('\n'.join([i.name for i in tags_all])),
                                        reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


async def change_tag2(query: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.choose_all, callback_data='choose_all_tags'),
                 InlineKeyboardButton(buttons.choose_no_one, callback_data='choose_no_one_tags'))
    keyboard.add(InlineKeyboardButton(buttons.choose_what_to_on, callback_data='choose_what_to_on_tags'))
    user = await User.get_or_none(chat_id=query.message.chat.id)
    await Settings.change_tag.set()
    tags_all = await Tag.filter(visible=True)
    if user:
        tags = await TagSubscription.filter(user=user)
        tag_names = []
        for i in tags:
            tag_names.append((await i.tag).name)
        if not len(tag_names):
            tag_names.append('нет')
        await set_keyboard_settings(query.message, msgs.current_tags.format('\n'.join(tag_names)))
    else:
        await set_keyboard_settings(query.message, msgs.current_tags.format('нет'))
    msg_id = await query.message.answer(msgs.if_want_change_tags.format('\n'.join([i.name for i in tags_all])),
                                        reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


async def change_tag3(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.choose_all, callback_data='choose_all_tags'),
                 InlineKeyboardButton(buttons.choose_no_one, callback_data='choose_no_one_tags'))
    keyboard.add(InlineKeyboardButton(buttons.choose_what_to_on, callback_data='choose_what_to_on_tags'))
    user = await User.get_or_none(chat_id=message.chat.id)
    await Settings.change_tag.set()
    tags_all = await Tag.filter(visible=True)
    if user:
        tags = await TagSubscription.filter(user=user)
        tag_names = []
        for i in tags:
            tag_names.append((await i.tag).name)
        if not len(tag_names):
            tag_names.append('нет')
        await set_keyboard_settings(message, msgs.current_tags.format('\n'.join(tag_names)))
    else:
        await set_keyboard_settings(message, msgs.current_tags.format('нет'))
    msg_id = await message.answer(msgs.if_want_change_tags.format('\n'.join([i.name for i in tags_all])),
                                  reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='choose_all_tags', state=Settings.change_tag)
async def choose_all_tags(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    user = (await User.get_or_create(chat_id=query.message.chat.id))[0]
    tags = await Tag.filter(visible=True)
    for i in tags:
        await TagSubscription.get_or_create(user=user, tag=i)
    await query.message.answer(msgs.tags_changed)
    await change_tag2(query, state)


@dp.callback_query_handler(text='choose_no_one_tags', state=Settings.change_tag)
async def choose_no_one_tags(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    user = (await User.get_or_create(chat_id=query.message.chat.id))[0]
    await TagSubscription.filter(user=user).delete()
    tags = await TagSubscription.filter(user=user)
    tag_names = []
    for i in tags:
        tag_names.append((await i.tag).name)
    if not len(tag_names):
        tag_names.append('нет')
    await query.message.answer(msgs.tags_changed)
    await change_tag2(query, state)


@dp.callback_query_handler(text='choose_what_to_on_tags', state=Settings.change_tag)
async def choose_what_to_on_tags(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    user = (await User.get_or_create(chat_id=query.message.chat.id))[0]
    tags = await Tag.filter(visible=True)
    await ChangeTags.tag.set()
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        rel = await TagSubscription.get_or_none(user=user, tag=i)
        if rel:
            keyboard.add(
                InlineKeyboardButton(buttons.check_mark + i.name, callback_data=f'choose_what_to_on_tags_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_what_to_on_tags_{i.id}'))
    await set_keyboard_confirm(query.message, msgs.choose_tags_)
    msg_id = await query.message.answer(msgs.chosen_are_marked, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text_contains='choose_what_to_on_tags_', state=ChangeTags.tag)
async def choose_what_to_on_tags_handler(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    tag_id = int(query.data.split('_')[5])
    tag = await Tag.get_or_none(id=tag_id)
    user = await User.get(chat_id=query.message.chat.id)
    rel = await TagSubscription.get_or_none(user=user, tag=tag)
    if rel:
        await rel.delete()
    else:
        await TagSubscription.create(user=user, tag=tag)
    keyboard = InlineKeyboardMarkup()
    tags = await Tag.filter(visible=True)
    for i in tags:
        rel = await TagSubscription.get_or_none(user=user, tag=i)
        if rel:
            keyboard.add(
                InlineKeyboardButton(buttons.check_mark + i.name, callback_data=f'choose_what_to_on_tags_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_what_to_on_tags_{i.id}'))
    await query.message.edit_reply_markup(keyboard)


@dp.callback_query_handler(text='back_to_tags', state=ChangeTags.tag)
async def back_to_tags(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await state.finish()
    await change_tag2(query, state)


@dp.callback_query_handler(text='change_name', state=Settings.change_contact)
async def change_name(query: callback_query):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await query.message.answer(msgs.enter_new_name)
    await Changing.name.set()


@dp.callback_query_handler(text='change_phone', state=Settings.change_contact)
async def change_phone(query: callback_query):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await query.message.answer(msgs.enter_new_phone)
    await Changing.phone.set()


@dp.message_handler(text=buttons.change_name)
async def change_name_(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back_to_settings))
    await message.answer(msgs.enter_new_name, reply_markup=keyboard)
    await Changing.name.set()


@dp.message_handler(text=buttons.change_phone)
async def change_phone_(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back_to_settings))
    await message.answer(msgs.enter_new_phone, reply_markup=keyboard)
    await Changing.phone.set()


@dp.message_handler(lambda text: text not in buttons.reply_keyboard_buttons, state=Changing.name)
async def changing_name(message: types.Message, state: FSMContext):
    await state.finish()
    user = await User.get_or_none(chat_id=message.chat.id)
    if not user:
        user = await User.create(chat_id=message.chat.id, name=message.text.strip())
    else:
        user.name = message.text.strip()
        await user.save()

    await message.answer(msgs.name_changed)
    await settings_menu(message, state)


@dp.message_handler(lambda text: text not in buttons.reply_keyboard_buttons, state=Changing.phone)
async def changing_phone(message: types.Message, state: FSMContext):
    text = message.text.strip()
    phone = await is_phone_valid(text)
    if phone is None:
        await message.answer(msgs.phone_is_wrong)
        return
    await state.finish()
    user = await User.get_or_none(chat_id=message.chat.id)
    if not user:
        user = await User.create(chat_id=message.chat.id, phone=phone)
    else:
        user.phone = phone
        await user.save()

    await message.answer(msgs.phone_changed)
    await settings_menu(message, state)


@dp.message_handler(text=buttons.booking, state='*')
@dp.message_handler(text=buttons.new_booking, state='*')
async def booking_handler(message: types.Message, state: FSMContext):
    await start(message, state)


@dp.callback_query_handler(text='new_booking')
@dp.callback_query_handler(text='new_booking', state='*')
async def new_booking_handler(query: CallbackQuery, state: FSMContext):
    await start(query.message, state, start_booking_again=True)


@dp.message_handler(commands='start', state='*')
async def start(message: types.Message, state: FSMContext, back_flag=False, start_booking_again=False):
    user = await User.get_or_none(chat_id=message.chat.id)
    if not user:
        text = message.text
        if len(text.split()) == 1:
            await message.answer(msgs.its_test)
            return
        elif len(text.split()) == 2:
            code = text.split()[1]
            activation_code = await ActivationCode.get_or_none(code=code)
            if activation_code:
                await activation_code.delete()
                await message.answer(msgs.test_allowed)
            else:
                await message.answer(msgs.wrong_code)
                return
    if not back_flag:
        if await state.get_data() != {}:
            await state.finish()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.soviet_restaurant, callback_data='restaurant_1'))
    keyboard.add(InlineKeyboardButton(buttons.big_avenue_restaurant, callback_data='restaurant_2'))
    keyboard.add(InlineKeyboardButton(buttons.volynskyi_restaurant, callback_data='restaurant_3'))

    await Booking.restaurant.set()
    if start_booking_again:
        msg_text = msgs.choose_address
    else:
        msg_text = msgs.start_message.format(await msgs.get_times_of_day(datetime.datetime.now(tz=config.timezone).hour)
                                             )
    msg_id = await message.answer(msg_text, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id
    user = await User.get_or_none(chat_id=message.chat.id)
    if not user:
        username = message.from_user.username if message.from_user.username else message.from_user.full_name
        await User.create(chat_id=message.chat.id, username=username)
    else:
        if user.username is None:
            username = message.from_user.username if message.from_user.username else message.from_user.full_name
            user.username = username
            await user.save()


async def set_keyboard_booking(message: types.Message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back))
    keyboard.add(KeyboardButton(buttons.menu))
    await message.answer(text, parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=keyboard)


async def set_keyboard_main_menu(message: types.Message, text, parse_mode=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.new_booking))
    keyboard.add(KeyboardButton(buttons.settings_menu))
    await message.answer(text, parse_mode=parse_mode, reply_markup=keyboard)


async def set_keyboard_settings(message, text, parse_mode=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back))
    await message.answer(text, reply_markup=keyboard, parse_mode=parse_mode)


async def set_keyboard_admin(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.admin_menu))
    await message.answer(text, reply_markup=keyboard)


async def set_keyboard_back(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.back))
    await message.answer(text, reply_markup=keyboard)


async def set_keyboard_confirm(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.confirm_choise))
    await message.answer(text, reply_markup=keyboard)


async def set_keyboard_back_and_contact(message, text):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(buttons.give_contact, request_contact=True))
    keyboard.add(KeyboardButton(buttons.back))
    keyboard.add(KeyboardButton(buttons.menu))
    await message.answer(text, reply_markup=keyboard)


@dp.callback_query_handler(text_contains=['restaurant_'], state=Booking.restaurant)
async def chosen_restaurant(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    await set_keyboard_booking(query.message, msg_text)

    msg_id = await query.message.answer(msgs.how_many, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text_contains=['how_many_'], state=Booking.how_many)
async def chosen_how_many(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    msg_id = await query.message.answer(msgs.choose_date, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


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
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='bigger_number', state=Booking.how_many)
async def bigger_number(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='back_to_menu2', state=Booking.how_many)
async def back_to_menu2(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await state.finish()
    await set_keyboard_main_menu(query.message, msgs.main_menu)


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
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text_contains=['date_booking_'], state=Booking.date_booking)
async def chosen_date_booking(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='date_booking_later', state=Booking.date_booking)
async def date_booking_later(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await state.update_data(date_booking='later')
    now = datetime.datetime.now(tz=config.timezone)
    keyboard = await generate_calendar(now.year, now.month, now.day, now, config.DAYS_FOR_BOOKING, delete_empty=True)
    await query.message.edit_reply_markup(keyboard)


async def reformat_times(time_available, times):
    for i in times:
        for j, k in enumerate(i):
            if k not in time_available:
                i[j] = ' '
    return times


@dp.callback_query_handler(text_contains=['approximate_time_'], state=Booking.approximate_time)
async def chosen_approximate_time(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    message_ids[msg_id.chat.id] = msg_id.message_id


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
    if all([' ' == i[0] for i in approximate_times[:3]]) and \
            all([' ' == i[0] for i in approximate_times[3:]]):
        await message.answer(msgs.sorry_not_available_times)
        await Booking.date_booking.set()
        await rechose_date_booking(message, state)
        return
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
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text_contains=['exact_time_'], state=Booking.exact_time)
async def chosen_exact_time(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='choose_table_yes'),
                 InlineKeyboardButton(buttons.no2, callback_data='choose_table_no'))
    msg_id = await query.message.answer(msgs.want_choose_table, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


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
    message_ids[msg_id.chat.id] = msg_id.message_id


async def rechoose_table_yes_no(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='choose_table_yes'),
                 InlineKeyboardButton(buttons.no2, callback_data='choose_table_no'))
    msg_id = await message.answer(msgs.want_choose_table, reply_markup=keyboard)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text=['choose_table_yes'], state=Booking.table)
async def choose_table_yes(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    tables = await get_available_tables_with_people(restaurant_number, how_many, date_booking, exact_time)
    if len(tables) == 0:
        await query.message.answer(msgs.all_tables_busy)
        return
    keyboard = InlineKeyboardMarkup(row_width=5)
    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE)

    await state.update_data(table='choosing')
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton('Зал 2 ' + buttons.page_next, callback_data='tableimage_1'))
    if colored_images[0][2] == 'path':
        msg_id = await bot.send_photo(query.message.chat.id, open(colored_images[0][0], 'rb'), msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        await FileIDs.create(path=colored_images[0][1], file_id=msg_id.photo[-1].file_id)
    else:
        msg_id = await bot.send_photo(query.message.chat.id, colored_images[0][0], msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text=['choose_table_no'], state=Booking.table)
async def choose_table_no(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await state.update_data(table=msgs.not_important)
    await Booking.confirmation.set()
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

    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text_contains=['tableimage_'], state=Booking.table)
async def tableimage_(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    image_number = int(query.data.split('_')[1])
    restaurant_number = (await state.get_data()).get('restaurant')
    how_many = (await state.get_data()).get('how_many')
    date_booking = (await state.get_data()).get('date_booking')
    exact_time = (await state.get_data()).get('exact_time')
    tables = await get_available_tables_with_people(restaurant_number, how_many, date_booking, exact_time)
    if len(tables) == 0:
        await query.message.answer(msgs.all_tables_busy)
        return
    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE)
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        if image_number == len(colored_images) - 1:
            keyboard.add(InlineKeyboardButton(buttons.page_back + f' Зал {image_number}',
                                              callback_data=f'tableimage_{image_number - 1}'),
                         InlineKeyboardButton(' ', callback_data=' '))
        elif image_number == 0:
            keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                         InlineKeyboardButton(f'Зал {image_number + 2} ' + buttons.page_next,
                                              callback_data=f'tableimage_{image_number + 1}'))
        else:
            keyboard.add(InlineKeyboardButton(buttons.page_back + f' Зал {image_number}',
                                              callback_data=f'tableimage_{image_number - 1}'),
                         InlineKeyboardButton(f'Зал {image_number + 2} ' + buttons.page_next,
                                              callback_data=f'tableimage_{image_number + 1}'))
    media = types.MediaGroup()
    if colored_images[image_number][2] == 'path':
        media = types.InputMediaPhoto(open(colored_images[image_number][0], 'rb'), msgs.chose_table,
                                      parse_mode=types.ParseMode.MARKDOWN_V2)
        msg_id = await query.message.edit_media(media, reply_markup=keyboard)
        await FileIDs.create(path=colored_images[image_number][1], file_id=msg_id.photo[-1].file_id)
    else:
        media = types.InputMediaPhoto(colored_images[image_number][0], msgs.chose_table,
                                      parse_mode=types.ParseMode.MARKDOWN_V2)
        msg_id = await query.message.edit_media(media, reply_markup=keyboard)


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
    table_keys = [i[1].keys() for i in config.TEMPLATES_RESTAURANTS_SVG_IDS[restaurant_number]]
    table_keys = sum([list(i) for i in table_keys], [])
    if table not in table_keys:
        await message.answer(msgs.wrong_table_at_all)
        await rechose_table(message, state)
        return
    try:
        table_now = [i[1] for i in tables].index(table)
    except ValueError:
        await message.answer(msgs.wrong_table_not_available)
        await rechose_table(message, state)
        return
    await Booking.next()
    await state.update_data(table=tables[table_now][::])
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes, callback_data='confirm_table'),
                 InlineKeyboardButton(buttons.no, callback_data='confirmnot_table'))
    restaurant = await Restaurant.get(self_id=(await state.get_data()).get('restaurant'))
    table_joint = (await Table.get(table_name=table, restaurant=restaurant)).joint
    text = msgs.confirm_table_joint.format(tables[table_now][::][1],
                                           tables[table_now][::][1]) if table_joint else msgs.confirm_table.format(
        tables[table_now][::][1])
    msg_id = await message.answer(await safe_for_markdown(text), reply_markup=keyboard,
                                  parse_mode=types.ParseMode.MARKDOWN_V2)
    message_ids[msg_id.chat.id] = msg_id.message_id
    return


@dp.callback_query_handler(text='confirm_table', state=Booking.confirm_table)
async def confirm_table(query: CallbackQuery, state: FSMContext):
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
            restaurant = await Restaurant.get(self_id=data['restaurant'])
            table_joint = (await Table.get(table_name=data['table'][1], restaurant=restaurant)).joint

            if table_joint:
                table_joint = msgs.joint_table
            else:
                table_joint = ''
            msg_text = msgs.information_about.format(msgs.restaurants[int(data['restaurant'])],
                                                     data['date_booking'] + ' ' +
                                                     data['exact_time'],
                                                     data['how_many'], msgs.guests[data['how_many']],
                                                     data['table'][1],
                                                     table_joint)

    msg_id = await query.message.answer(
        await safe_for_markdown(msg_text), reply_markup=keyboard,
        parse_mode=types.ParseMode.MARKDOWN_V2)

    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='confirmnot_table', state=Booking.confirm_table)
async def confirmnot_table(query: CallbackQuery, state: FSMContext):
    await Booking.table.set()
    await rechose_table(query.message, state)


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
    colored_images = await get_colored_image(restaurant_number, [i[1] for i in tables], config.PATH_TO_SAVE)
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton(f'Зал 2 ' + buttons.page_next, callback_data='tableimage_1'))
    if colored_images[0][2] == 'path':
        msg_id = await bot.send_photo(message.chat.id, open(colored_images[0][0], 'rb'), msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        await FileIDs.create(path=colored_images[0][1], file_id=msg_id.photo[-1].file_id)
    else:
        msg_id = await bot.send_photo(message.chat.id, colored_images[0][0], msgs.chose_table,
                                      reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='confirm', state=Booking.confirmation)
async def confirm(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
    user = await User.get_or_none(chat_id=query.message.chat.id)
    if not user or user.name is None or user.phone is None:
        await Booking.next()
        await register2(query, state)
    else:
        await state.update_data(name=user.name)
        await state.update_data(phone=user.phone)
        await Booking.final.set()
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='final_confirm'),
                     InlineKeyboardButton(buttons.no2, callback_data='wrong_final_confirm'))
        msg_id = await query.message.answer(await safe_for_markdown(msgs.personal_data.format(user.name, user.phone)),
                                            reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
        message_ids[msg_id.chat.id] = msg_id.message_id


async def rechose_confirm(message: types.Message, state: FSMContext):
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
            restaurant = await Restaurant.get(self_id=data['restaurant'])
            table_joint = (await Table.get(table_name=data['table'], restaurant=restaurant)).joint
            if table_joint:
                table_joint = msgs.joint_table
            else:
                table_joint = ''
            msg_text = msgs.information_about.format(msgs.restaurants[int(data['restaurant'])],
                                                     data['date_booking'] + ' ' +
                                                     data['exact_time'],
                                                     data['how_many'], msgs.guests[data['how_many']],
                                                     data['table'][1],
                                                     table_joint)

        msg_id = await message.answer(
            await safe_for_markdown(msg_text), reply_markup=keyboard,
            parse_mode=types.ParseMode.MARKDOWN_V2)
        message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='register', state=Booking.name)
async def register(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await query.message.answer(msgs.enter_name)


async def register2(query: CallbackQuery, state: FSMContext):
    await query.message.answer(await safe_for_markdown(msgs.give_your_data), parse_mode=types.ParseMode.MARKDOWN_V2)
    await set_keyboard_back_and_contact(query.message, msgs.enter_name)


@dp.message_handler(lambda text: text not in buttons.reply_keyboard_buttons, state=Booking.name)
async def name_handler(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Booking.next()
    await set_keyboard_booking(message, msgs.phone_request)


@dp.message_handler(content_types=types.ContentType.CONTACT, state=Booking.name)
async def contact_handler(message: types.Message, state: FSMContext):
    contact = message.contact
    await state.update_data(name=contact.first_name)
    await state.update_data(phone=contact.phone_number)
    await Booking.final.set()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.yes2, callback_data='final_confirm'),
                 InlineKeyboardButton(buttons.no2, callback_data='wrong_final_confirm'))
    await set_keyboard_booking(message, msgs.thanks_for_contact)
    async with state.proxy() as data:
        msg_id = await message.answer(
            await safe_for_markdown(msgs.personal_data2.format(data.get('name'), data.get('phone'))),
            reply_markup=keyboard, parse_mode=types.ParseMode.MARKDOWN_V2)
    message_ids[msg_id.chat.id] = msg_id.message_id


async def rechose_name(message: types.Message, state: FSMContext):
    await set_keyboard_back_and_contact(message, msgs.enter_name)


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
    message_ids[msg_id.chat.id] = msg_id.message_id


@dp.callback_query_handler(text='final_confirm', state=Booking.final)
async def final_confirm(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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

    flag = True
    for i in remind_buttons[:4]:
        if i[1] != '':
            flag = False
    if not flag:
        keyboard.add(InlineKeyboardButton(remind_buttons[0][1], callback_data=f'remind_{remind_buttons[0][0]}'),
                     InlineKeyboardButton(remind_buttons[1][1], callback_data=f'remind_{remind_buttons[1][0]}'))
        keyboard.add(InlineKeyboardButton(remind_buttons[2][1], callback_data=f'remind_{remind_buttons[2][0]}'),
                     InlineKeyboardButton(remind_buttons[3][1], callback_data=f'remind_{remind_buttons[3][0]}'))
        keyboard.add(InlineKeyboardButton(remind_buttons[4][1], callback_data=f'remind_{remind_buttons[4][0]}'))
        msg_id = await query.message.answer(msgs.remind, reply_markup=keyboard)
        message_ids[msg_id.chat.id] = msg_id.message_id
    else:
        await remind_handler_2(query, state, None)


@dp.callback_query_handler(text_contains=['remind_'], state=Booking.remind)
async def remind_handler(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
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
                                                                       user.name,
                                                                       user.phone, order.id)
        order.table_range = table_range
        order.table_joint_range = table_joint_range
        order.table = await Table.get(table_name=table[1], restaurant=restaurant)
        await order.save()
        people = msgs.people_many if int(data['how_many']) > 1 else msgs.people_one
        if data['table'] == msgs.not_important:
            msg_text = msgs.booking_success2.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,

                                                    data['date_booking'] + ' ' + data['exact_time'],
                                                    data['how_many'], msgs.guests[data['how_many']])
            msg_text_admin = msgs.admin_booking_info2.format(msgs.restaurants[data.get('restaurant')],
                                                             msgs.mention.format(user.chat_id, user.name),
                                                             user.phone,
                                                             data['date_booking'] + ' ' + data['exact_time'],
                                                             data['how_many'], msgs.guests[data['how_many']], order.id)
        else:
            msg_text = msgs.booking_success.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,

                                                   data['date_booking'] + ' ' + data['exact_time'],
                                                   data['how_many'], msgs.guests[data['how_many']], data['table'][1])
            msg_text_admin = msgs.admin_booking_info.format(msgs.restaurants[data.get('restaurant')],
                                                            msgs.mention.format(user.chat_id, user.name),
                                                            user.phone,
                                                            data['date_booking'] + ' ' + data['exact_time'],
                                                            data['how_many'], msgs.guests[data['how_many']],
                                                            data['table'][1], order.id)
        if data.get('remind'):
            reminds = {24: '24 часа', 12: '12 часов', 6: '6 часов', 2: '2 часа'}
            msg_text += msgs.with_remind.format(reminds[data['remind']])
        msg_text += msgs.for_cancel.format(config.PHONES[data.get('restaurant')])
        await set_keyboard_main_menu(query.message,
                                     await safe_for_markdown(msg_text), parse_mode=types.ParseMode.MARKDOWN_V2)
        await admin_sender(msg_text_admin, data.get('restaurant'))

    await state.finish()


async def remind_handler_2(query: CallbackQuery, state: FSMContext, remind):
    keyboard = InlineKeyboardMarkup()
    date = (await state.get_data()).get('date_booking')
    time = (await state.get_data()).get('exact_time')
    now = datetime.datetime.now(tz=config.timezone)
    time_book = datetime.datetime.strptime(f'{date}.{now.year} {time}', '%d.%m.%Y %H:%M')
    now = now.replace(tzinfo=None)

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
                                                                       user.name,
                                                                       user.phone, order.id)
        order.table_range = table_range
        order.table_joint_range = table_joint_range
        order.table = await Table.get(table_name=table[1], restaurant=restaurant)
        await order.save()
        people = msgs.people_many if int(data['how_many']) > 1 else msgs.people_one
        if data['table'] == msgs.not_important:
            msg_text = msgs.booking_success2.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,

                                                    data['date_booking'] + ' ' + data['exact_time'],
                                                    data['how_many'], msgs.guests[data['how_many']])
            msg_text_admin = msgs.admin_booking_info2.format(msgs.restaurants[data.get('restaurant')],
                                                             msgs.mention.format(user.chat_id, user.name),
                                                             user.phone,

                                                             data['date_booking'] + ' ' + data['exact_time'],
                                                             data['how_many'], msgs.guests[data['how_many']], order.id)
        else:
            msg_text = msgs.booking_success.format(msgs.restaurants[data.get('restaurant')], user.name, user.phone,
                                                   data['date_booking'] + ' ' + data['exact_time'],
                                                   data['how_many'], msgs.guests[data['how_many']], data['table'][1])
            msg_text_admin = msgs.admin_booking_info.format(msgs.restaurants[data.get('restaurant')],
                                                            msgs.mention.format(user.chat_id, user.name),
                                                            user.phone,
                                                            data['date_booking'] + ' ' + data['exact_time'],
                                                            data['how_many'], msgs.guests[data['how_many']],
                                                            data['table'][1], order.id)
        if data.get('remind'):
            reminds = {24: '24 часа', 12: '12 часов', 6: '6 часов', 2: '2 часа'}
            msg_text += msgs.with_remind.format(reminds[data['remind']])
        msg_text += msgs.for_cancel.format(config.PHONES[data.get('restaurant')])

        await set_keyboard_main_menu(query.message,
                                     await safe_for_markdown(msg_text), parse_mode=types.ParseMode.MARKDOWN_V2)
        await admin_sender(msg_text_admin, data.get('restaurant'))
    await state.finish()


@dp.callback_query_handler(text='wrong_final_confirm', state=Booking.final)
async def wrong_final_confirm(query: CallbackQuery, state: FSMContext):
    if query.message.message_id != message_ids.get(query.message.chat.id):
        return
    await Booking.name.set()
    await register2(query, state)


@dp.callback_query_handler(text_contains=['presence_yes_'])
@dp.callback_query_handler(text_contains=['presence_yes_'], state='*')
async def presence_yes_callback(query: CallbackQuery, state: FSMContext):
    order_id = int(query.data.split('_')[2])
    order = await Order.get_or_none(id=order_id)
    if not order:
        await query.answer(msgs.there_is_no_order)
        return
    if not order.confirmation_presence:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(buttons.check_mark + buttons.presence_yes, callback_data=f'presence_yes_{order.id}'))
        keyboard.add(InlineKeyboardButton(buttons.presence_no, callback_data=f'presence_maybe_{order.id}'))
        await query.message.edit_reply_markup(keyboard)
        order.confirmation_presence = True
        await order.save()
        await confirm_order_table(order.restaurant, order.date, order.table_range)
        await query.message.answer(msgs.confirmation_presence_yes)
    else:
        await query.answer(msgs.already_confirmed)


@dp.callback_query_handler(text_contains=['presence_maybe_'])
@dp.callback_query_handler(text_contains=['presence_maybe_'], state='*')
async def presence_maybe_callback(query: CallbackQuery, state: FSMContext):
    order_id = int(query.data.split('_')[2])
    order_id = int(query.data.split('_')[2])
    order = await Order.get_or_none(id=order_id)
    if not order:
        await query.answer(msgs.there_is_no_order)
        return
    if order.confirmation_presence:
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(buttons.presence_yes, callback_data=f'presence_yes_{order.id}'))
    keyboard.add(
        InlineKeyboardButton(buttons.check_mark + buttons.presence_no, callback_data=f'presence_maybe_{order.id}'))
    await query.message.edit_reply_markup(keyboard)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(buttons.presence_no2, callback_data=f'presence_no_{order_id}'))
    keyboard.add(InlineKeyboardButton(buttons.presence_yes2, callback_data=f'presence_yes_{order_id}'))
    await query.message.answer(msgs.confirmation_presence_maybe, reply_markup=keyboard)


@dp.callback_query_handler(text_contains=['presence_no'])
@dp.callback_query_handler(text_contains=['presence_no'], state='*')
async def presence_no_callback(query: CallbackQuery, state: FSMContext):
    order_id = int(query.data.split('_')[2])
    order = await Order.get_or_none(id=order_id)
    if not order:
        await query.answer(msgs.there_is_no_order)
        return
    if order.confirmation_presence:
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(buttons.check_mark + buttons.presence_no2, callback_data=f'presence_no_{order_id}'))

    keyboard.add(InlineKeyboardButton(buttons.presence_yes2, callback_data=f'presence_yes_{order_id}'))
    await query.message.edit_reply_markup(keyboard)
    await delete_order(order.restaurant, order.date, order.table_range, order.table_joint_range)
    await order.delete()
    await query.message.answer(msgs.confirmation_presence_no)


@dp.message_handler(commands=['enableinfo'], chat_type='group')
@dp.message_handler(commands=['enableinfo'], chat_type='supergroup')
async def enableinfo(message: types.Message, state: FSMContext):
    password = message.text.split()
    if len(password) != 2:
        await message.answer(msgs.wrong_password)
        return
    password = password[1]
    if password in config.RESTAURANT_PASSWORDS.values():
        chat_ = await AdminChat.get_or_none(chat_id=message.chat.id)
        restaurant_number = list(config.RESTAURANT_PASSWORDS.keys())[
            list(config.RESTAURANT_PASSWORDS.values()).index(password)]
        if chat_:
            await message.answer(msgs.already_in_base.format(msgs.restaurants[chat_.restaurant]))
        else:
            await AdminChat.create(chat_id=message.chat.id, restaurant=restaurant_number)
            await message.answer(msgs.good_password.format(msgs.restaurants[restaurant_number]))
    else:
        await message.answer(msgs.wrong_password)


@dp.message_handler(commands=['disableinfo'], chat_type='group')
@dp.message_handler(commands=['disableinfo'], chat_type='supergroup')
async def disableinfo(message: types.Message, state: FSMContext):
    chat_ = await AdminChat.get_or_none(chat_id=message.chat.id)
    if chat_:
        await chat_.delete()
        await message.answer(msgs.deleted_from_base)
    else:
        await message.answer(msgs.not_in_base)


@dp.message_handler(commands=['get'])
async def getcode(message: types.Message, state: FSMContext):
    if message.chat.id not in config.admins:
        return
    if len(message.text.split()) == 1:
        uid = uuid.uuid4()
        await ActivationCode.create(code=uid)
        await message.answer(msgs.activation_code.format(uid))
    elif len(message.text.split()) == 2 and message.text.split()[1].isdigit():
        uids = []
        for i in range(int(message.text.split()[1])):
            uid = uuid.uuid4()
            uids.append(str(uid))
            await ActivationCode.create(code=uid)
        await message.answer(msgs.activation_codes.format('\n'.join(uids)))


async def admin_sender(msg_text, restaurant_number):
    await AdminSend.create(text=msg_text, restaurant=restaurant_number)


async def broadcast_sender(user_id, text, reply_markup=None, markdown=None, photo=None, video=None):
    try:
        if not photo and not video:
            await bot.send_message(user_id, text, disable_web_page_preview=True,
                                   reply_markup=reply_markup, parse_mode=markdown)
        elif photo:
            await bot.send_photo(user_id, open(photo, 'rb'), caption=text, reply_markup=reply_markup,
                                 parse_mode=markdown)
        elif video:
            await bot.send_video(user_id, open(video, 'rb'), caption=text, reply_markup=reply_markup,
                                 parse_mode=markdown)
    except exceptions.BotBlocked:
        log.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        log.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        log.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await broadcast_sender(user_id, text,
                                      reply_markup=reply_markup, markdown=markdown, photo=photo,
                                      video=video)  # Recursive call
    except exceptions.UserDeactivated:
        log.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.MigrateToChat as e:
        log.exception(f"Target [ID:{user_id}]: failed")
        log.error(text)
        adm_chat = await AdminChat.get_or_none(chat_id=user_id)
        if adm_chat:
            adm_chat.chat_id = e.migrate_to_chat_id
            await adm_chat.save()
        return await broadcast_sender(adm_chat.chat_id, text,
                                      reply_markup=reply_markup, markdown=markdown, photo=photo,
                                      video=video)
    except exceptions.TelegramAPIError:
        log.exception(f"Target [ID:{user_id}]: failed")
        log.error(text)

    else:
        log.info(f"Target [ID:{user_id}]: success")
        return True
    return False


async def archivator(flag=False):
    while True:
        now = datetime.datetime.now(tz=config.timezone)
        if now.hour == 23 and now.minute == 55:
            date_now = now.strftime('%d.%m')
            dates_to_create = [(now + datetime.timedelta(days)).strftime('%d.%m') for days in
                               range(1, config.DAYS_FOR_BOOKING + 1)]
            dates_to_create_joint = [f'{date} (Общие)' for date in dates_to_create]
            for i in msgs.restaurants:
                gc = gspread.service_account(config.CREDENTIALS_SHEETS)
                sheet = gc.open_by_url(config.TABLES_DICT[i])
                worksheets = sheet.worksheets()
                await to_archive(i, date_now)
                titles = [j.title for j in worksheets]
                for j in dates_to_create:
                    if j not in titles:
                        await create_wks(i, j)
                        await asyncio.sleep(1)
                for j in dates_to_create_joint:
                    if j not in titles:
                        await create_wks_joint(i, j, True)
                        await asyncio.sleep(1)
            orders = await Order.all()
            now_date = now.strftime('%m.%d')
            for i in orders:
                d = i.date.split('.')
                if d[1] + '.' + d[0] < now_date:
                    await i.delete()

        await asyncio.sleep(60)


async def notificator(flag=False):
    while True:
        now = datetime.datetime.now(tz=config.timezone)
        date_now = now.strftime('%d.%m')
        time_now = now.strftime('%H:%M')
        time_hour_next = (now + datetime.timedelta(hours=1)).strftime('%H:%M')
        orders = await Order.filter(date=date_now, time=time_hour_next, confirmation_presence=None)
        for order in orders:
            user = await order.user
            text = msgs.precense.format(msgs.restaurants[order.restaurant],
                                        order.date, order.time, config.PHONES[order.restaurant])

            await broadcast_sender(user.chat_id, text)
        orders = await Order.filter(date=date_now, time=time_now, confirmation_presence=None)
        if config.DELETE_NOT_CONFIRMED:
            for order in orders:
                await delete_order(order.restaurant, order.date, order.table_range, order.table_joint_range)
                await order.delete()
        await asyncio.sleep(60)


async def reminder(flag=False):
    while True:
        now = datetime.datetime.now(tz=config.timezone)
        date_now = now.strftime('%d.%m')
        time_now = now.strftime('%H:%M')
        time_plus_2 = now + datetime.timedelta(hours=2)
        time_plus_6 = now + datetime.timedelta(hours=6)
        time_plus_12 = now + datetime.timedelta(hours=12)
        time_plus_24 = now + datetime.timedelta(hours=24)
        orders_2 = await Order.filter(remind=2, date=time_plus_2.strftime('%d.%m'), time=time_plus_2.strftime('%H:%M'),
                                      reminded=None)
        orders_6 = await Order.filter(remind=6, date=time_plus_6.strftime('%d.%m'), time=time_plus_6.strftime('%H:%M'),
                                      reminded=None)
        orders_12 = await Order.filter(remind=12, date=time_plus_12.strftime('%d.%m'),
                                       time=time_plus_12.strftime('%H:%M'), reminded=None)
        orders_24 = await Order.filter(remind=24, date=time_plus_24.strftime('%d.%m'),
                                       time=time_plus_24.strftime('%H:%M'), reminded=None)
        for order in orders_2:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[order.restaurant],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        for order in orders_6:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[order.restaurant],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        for order in orders_12:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[order.restaurant],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        for order in orders_24:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[order.restaurant],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        await asyncio.sleep(60)


async def broadcaster(flag=False):
    while True:
        broadcast_q = await BroadcastModel.all()
        if len(broadcast_q) > 0:
            for i in broadcast_q:
                links = i.link
                keyboard = InlineKeyboardMarkup()
                for k in links:
                    keyboard.add(InlineKeyboardButton(links[k][0], url=links[k][1]))
                await broadcast_sender(i.chat_id, i.text, reply_markup=keyboard, photo=i.photo, video=i.video)
                await i.delete()
        admin_broadcast = await AdminSend.all()
        if len(admin_broadcast) > 0:
            for i in admin_broadcast:
                admin_chats = await AdminChat.filter(restaurant=i.restaurant)
                msg_text = i.text
                for j in admin_chats:
                    await broadcast_sender(j.chat_id, msg_text, markdown=types.ParseMode.HTML)
                    await asyncio.sleep(0.07)
                await i.delete()
        await asyncio.sleep(10)


async def deleter_orders(flag=False):
    while True:
        now_str = datetime.datetime.now(tz=config.timezone).strftime('%m.%d.%Y %H:%M')
        order_to_delete = await OrderToDelete.filter(datetime__lte=now_str)
        for i in order_to_delete:
            order = await i.order
            await delete_order(order.restaurant, order.date, order.table_range, order.table_joint_range, order)
            await order.delete()
            await asyncio.sleep(0.5)
        await asyncio.sleep(60)


async def updater_restaurants(flag=False):
    for i in msgs.restaurants:
        await Restaurant.get_or_create(restaurant_name=msgs.restaurants[i], self_id=i)


async def updater_tables(flag=False):
    restaurants = await Restaurant.all()
    for res in restaurants:
        tables = await get_tables(res.self_id)
        for i in tables:
            await Table.get_or_create(restaurant=res, table_name=i[0],
                                      chairs=i[1], joint=i[2],
                                      colnum=i[3], colnum_joint=i[4])


async def tester_order(restaurant, date, tables, how_many, time):
    user = await User.get_or_none(id=8)
    restaurant = await Restaurant.get_or_none(id=1)
    for table in tables:
        await Order.create(restaurant=restaurant,
                           date=date, time=time, how_many=how_many,
                           user=user, table=table)


async def on_startup(*args):
    await init()
    asyncio.create_task(updater_restaurants())
    asyncio.create_task(updater_tables())
    asyncio.create_task(reminder())
    asyncio.create_task(archivator())
    asyncio.create_task(broadcaster())
    asyncio.create_task(deleter_orders())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
