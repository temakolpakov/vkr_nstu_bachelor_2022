import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aiogram import types

from aiogram.types import CallbackQuery

from aiogram.dispatcher import FSMContext
from models import *
from messages import ru_messages as msgs
from helpers_dir.google_sheet_functions import *

from states import *
from helpers_dir.helpers import is_phone_valid
from middlewares.answercallback_middleware import set_message_id
from keyboards import ru_keyboards as kb


# @dp.callback_query_handler(text='settings', state='*')
async def settings_callback(query: CallbackQuery, state: FSMContext):
    await settings(query.message, state)



# @dp.message_handler(text=btns.menu, state='*')
async def settings(message: types.Message, state: FSMContext, interrupted=False):
    if state:
        if await state.get_data() != {}:
            await message.answer(msgs.interrupted)
        await state.finish()


    msg_text = msgs.main_menu.format(config.restaurant_name) if not interrupted else msgs.interrupted_booking
    await message.answer(msg_text, reply_markup=await kb.main_keyboard())


# @dp.message_handler(text=btns.settings_menu)
# @dp.message_handler(text=btns.settings_menu, state="*")
async def settings_menu(message: types.Message, state: FSMContext):

    if state:
        await state.finish()
    user = await User.get_or_none(chat_id=message.chat.id)
    await Settings.change_contact.set()

    if user:
        name = user.name if user.name else 'нет'
        phone = user.phone if user.phone else 'нет'
        await message.answer(msgs.your_data, parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=await kb.back_keyboard())

        msg_id = await message.answer(msgs.current_name_phone_tags.format(name, phone), reply_markup=await kb.settings_menu_keyboard())
    else:
        await message.answer(msgs.your_data, parse_mode=types.ParseMode.MARKDOWN_V2, reply_markup=await kb.back_keyboard())
        msg_id = await message.answer(msgs.current_name_phone_tags.format('нет', 'нет'), reply_markup=await kb.settings_menu_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='change_contact')
async def change_contact(query: CallbackQuery):
    await Settings.change_contact.set()
    user = await User.get_or_none(chat_id=query.message.chat.id)
    if user:
        name = user.name if user.name else 'нет'
        phone = user.phone if user.phone else 'нет'
        await query.message.answer(msgs.your_data, msgs.current_name_phone.format(name, phone),  reply_markup=await kb.back_keyboard())
        msg_id = await query.message.answer(msgs.if_want_change, reply_markup=await kb.settings_menu_keyboard())
    else:
        await query.message.answer(msgs.your_data, msgs.current_name_phone.format('нет', 'нет'),  reply_markup=await kb.back_keyboard())
        msg_id = await query.message.answer(msgs.if_want_change, reply_markup=await kb.settings_menu_keyboard())
    await set_message_id(msg_id)


async def change_contact2(message: types.Message, state: FSMContext):
    user = await User.get_or_none(chat_id=message.chat.id)
    await Settings.change_contact.set()
    if user:
        name = user.name if user.name else 'нет'
        phone = user.phone if user.phone else 'нет'
        await message.answer(msgs.your_data, msgs.current_name_phone.format(name, phone),  reply_markup=await kb.back_keyboard())
        msg_id = await message.answer(msgs.if_want_change, reply_markup=await kb.settings_menu_keyboard())
    else:
        await message.answer(msgs.your_data, msgs.current_name_phone.format('нет', 'нет'),  reply_markup=await kb.back_keyboard())
        msg_id = await message.answer(msgs.if_want_change, reply_markup=await kb.settings_menu_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='change_tags')
async def change_tag(query: CallbackQuery, state: FSMContext):
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
        await query.message.answer(msgs.current_tags.format('\n'.join(tag_names)), reply_markup=await kb.back_keyboard())
    else:
        await query.message.answer(msgs.current_tags.format('нет'), reply_markup=await kb.back_keyboard())
    msg_id = await query.message.answer(msgs.if_want_change_tags.format('\n'.join([i.name for i in tags_all])),
                                        reply_markup=await kb.change_tags_keyboard())


    await set_message_id(msg_id)


async def change_tag2(query: CallbackQuery, state: FSMContext):
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
        await query.message.answer(msgs.current_tags.format('\n'.join(tag_names)),
                                   reply_markup=await kb.back_keyboard())
    else:
        await query.message.answer(msgs.current_tags.format('нет'), reply_markup=await kb.back_keyboard())
    msg_id = await query.message.answer(msgs.if_want_change_tags.format('\n'.join([i.name for i in tags_all])),
                                        reply_markup=await kb.change_tags_keyboard())
    await set_message_id(msg_id)


async def change_tag3(message: types.Message, state: FSMContext):
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
        await message.answer(msgs.current_tags.format('\n'.join(tag_names)),
                                   reply_markup=await kb.back_keyboard())
    else:
        await message.answer(msgs.current_tags.format('нет'), reply_markup=await kb.back_keyboard())
    msg_id = await message.answer(msgs.if_want_change_tags.format('\n'.join([i.name for i in tags_all])),
                                  reply_markup=await kb.change_tags_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='choose_all_tags', state=Settings.change_tag)
async def choose_all_tags(query: CallbackQuery, state: FSMContext):
    user = (await User.get_or_create(chat_id=query.message.chat.id))[0]
    tags = await Tag.filter(visible=True)
    for i in tags:
        await TagSubscription.get_or_create(user=user, tag=i)
    await query.message.answer(msgs.tags_changed)
    await change_tag2(query, state)


# @dp.callback_query_handler(text='choose_no_one_tags', state=Settings.change_tag)
async def choose_no_one_tags(query: CallbackQuery, state: FSMContext):
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


# @dp.callback_query_handler(text='choose_what_to_on_tags', state=Settings.change_tag)
async def choose_what_to_on_tags(query: CallbackQuery, state: FSMContext):
    user = (await User.get_or_create(chat_id=query.message.chat.id))[0]
    tags = await Tag.filter(visible=True)
    await ChangeTags.tag.set()
    await query.message.answer(msgs.choose_tags_, reply_markup=await kb.confirm_keyboard())
    msg_id = await query.message.answer(msgs.chosen_are_marked, reply_markup=await kb.choose_what_to_on_tags_keyboard(tags, user))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains='choose_what_to_on_tags_', state=ChangeTags.tag)
async def choose_what_to_on_tags_handler(query: CallbackQuery, state: FSMContext):
    tag_id = int(query.data.split('_')[5])
    tag = await Tag.get_or_none(id=tag_id)
    user = await User.get(chat_id=query.message.chat.id)
    rel = await TagSubscription.get_or_none(user=user, tag=tag)
    if rel:
        await rel.delete()
    else:
        await TagSubscription.create(user=user, tag=tag)
    tags = await Tag.filter(visible=True)
    await query.message.edit_reply_markup(await kb.choose_what_to_on_tags_keyboard(tags, user))


# @dp.callback_query_handler(text='back_to_tags', state=ChangeTags.tag)
async def back_to_tags(query: CallbackQuery, state: FSMContext):
    await state.finish()
    await change_tag2(query, state)


# @dp.callback_query_handler(text='change_name', state=Settings.change_contact)
async def change_name(query: CallbackQuery):
    await query.message.answer(msgs.enter_new_name)
    await Changing.name.set()


# @dp.callback_query_handler(text='change_phone', state=Settings.change_contact)
async def change_phone(query: CallbackQuery):
    await query.message.answer(msgs.enter_new_phone)
    await Changing.phone.set()


# @dp.message_handler(text=btns.change_name)
async def change_name_(message: types.Message):

    await message.answer(msgs.enter_new_name, reply_markup=await kb.back_to_settings_keyboard())
    await Changing.name.set()


# @dp.message_handler(text=btns.change_phone)
async def change_phone_(message: types.Message):
    await message.answer(msgs.enter_new_phone, reply_markup=await kb.back_to_settings_keyboard())
    await Changing.phone.set()


# @dp.message_handler(lambda text: text not in btns.reply_keyboard_buttons, state=Changing.name)
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


# @dp.message_handler(lambda text: text not in btns.reply_keyboard_buttons, state=Changing.phone)
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