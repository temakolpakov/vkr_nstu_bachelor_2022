import datetime

import validators
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, ContentType

import config
from bot_admin_setup import bot
from config import admins
from helpers_dir.google_sheet_functions import create_order, create_order_without_table
from helpers_dir.img_helper import get_colored_image
from keyboards import ru_keyboards_admin as kb
from buttons import ru_buttons as btns
from messages import ru_messages_admin as msgs
from middlewares.answercallback_middleware import set_message_id
from models import get_available_times, get_available_tables_with_people, Table, Restaurant, Order, AdminSend, User, \
    OrderToDelete, Tag, TagSubscription, BroadcastModel, BroadcastHistory
from states_admin import *


# @dp.message_handler(commands=['del'])
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

    msg_text = msgs.del_booking_confirmation.format(m[1], msgs.restaurants[(await order.restaurant).self_id],
                                                    (await order.user).name, (await order.user).phone,
                                                    order.date + ' ' + order.time, order.how_many,
                                                    msgs.guests[order.how_many],
                                                    order.table_range,
                                                    f'{order.table_joint_range} в общих' if order.table_joint_range else '')
    msg_id = await message.answer(msg_text, reply_markup=await kb.del_booking_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains='del_booking_', state=DelBooking.confirmation)
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

        await query.message.answer(msgs.del_booking_in_order, reply_markup=await kb.restore_order_keyboard(order))
        await state.finish()
    else:
        await state.finish()
        await query.message.answer(msgs.del_booking_cancelled)


# @dp.callback_query_handler(text_contains='restore_order_')
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


# @dp.message_handler(text=btns.menu, state='*')
async def settings(message: types.Message, state: FSMContext):
    if state:
        if await state.get_data() != {}:
            await message.answer(msgs.interrupted)
        await state.finish()
    if message.chat.id in admins:
        await message.answer(msgs.you_are_admin.format(config.BOT_NAME), reply_markup=await kb.admin_keyboard())
        return


# @dp.message_handler(text=btns.admin_menu)
async def admin_menu(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return

    msg_id = await message.answer(msgs.admin_menu, reply_markup=await kb.admin_menu_keyboard())
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='admin_tags')
# @dp.callback_query_handler(text='admin_tags', state=AddTag.name)
# @dp.callback_query_handler(text='admin_tags', state=DelTag.name)
async def admin_tags(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    if state:
        await state.finish()
    tags = await Tag.filter()
    text = msgs.tag_list.format('\n'.join([i.name for i in tags]))
    await query.message.answer(text)
    msg_id = await query.message.answer(msgs.tag_list2, reply_markup=await kb.admin_tags_keyboard())
    await set_message_id(msg_id)


# @dp.message_handler(text=btns.tags)
async def admin_tags(message: types.Message):
    if message.chat.id not in admins:
        return
    tags = await Tag.all().order_by('id')
    text = msgs.menu
    await message.answer(text, reply_markup=await kb.back_keyboard())
    msg_id = await message.answer(msgs.tag_list2, reply_markup=await kb.update_visible_keyboard(tags))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains='update_visible_')
async def update_visible(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    tag_id = query.data.split('_')[2]
    tag = await Tag.get(id=int(tag_id))
    tag.visible = not tag.visible
    await tag.save()
    tags = await Tag.all().order_by('id')

    await query.message.edit_reply_markup(await kb.update_visible_keyboard(tags))


async def admin_tags2(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    if state:
        await state.finish()
    tags = await Tag.all().order_by('id')
    text = msgs.menu

    await message.answer(text, reply_markup=await kb.back_keyboard())
    msg_id = await message.answer(msgs.tag_list2, reply_markup=await kb.update_visible_keyboard(tags))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text='add_tag')
async def add_tag(query: CallbackQuery):
    if query.message.chat.id not in admins:
        return
    await AddTag.name.set()
    msg_id = await query.message.answer(msgs.add_tag)
    await set_message_id(msg_id)


# @dp.message_handler(state=AddTag.name)
async def add_tag_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    await Tag.create(name=message.text)
    await state.finish()
    await message.answer(msgs.tag_added.format(message.text))
    await admin_tags2(message, state)


# @dp.callback_query_handler(text='del_tag')
async def del_tag(query: CallbackQuery):
    if query.message.chat.id not in admins:
        return
    tags = await Tag.filter()
    await DelTag.name.set()
    msg_id = await query.message.answer(msgs.del_tag, reply_markup=await kb.del_tag_keyboard(tags))
    await set_message_id(msg_id)


async def del_tag2(message: types.Message):
    if message.chat.id not in admins:
        return
    tags = await Tag.filter()
    await DelTag.name.set()
    msg_id = await message.answer(msgs.del_tag, reply_markup=await kb.del_tag_keyboard(tags))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains='del_tag_', state=DelTag.name)
async def del_tag_handler(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    # await state.finish()
    to_delete = int(query.data.split('_')[2])
    await state.update_data(name=to_delete)
    await DelTag.next()
    tag = await Tag.get(id=to_delete)
    msg_id = await query.message.answer(msgs.del_tag_confirm.format(tag.name),
                                        reply_markup=await kb.del_tagconfirm_keyboard(to_delete))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains='del_tagconfirm_', state=DelTag.confirmation)
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


# @dp.callback_query_handler(text='broadcast')
async def broadcast_handler(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    await Broadcast.text.set()
    await query.message.answer(msgs.enter_text, reply_markup=await kb.back_keyboard())


# @dp.message_handler(text=btns.broadcast)
async def broadcast_menu(message: types.Message, state: FSMContext, flag=False):
    if message.chat.id not in admins:
        return
    await Broadcast.text.set()
    await message.answer(msgs.enter_text, reply_markup=await kb.back_keyboard())


# @dp.message_handler(state=Broadcast.text)
async def broadcast_text_handler(message: types.Message, state: FSMContext):
    if message.chat.id not in admins:
        return
    await state.update_data(text=message.text)
    await Broadcast.next()
    await message.answer(msgs.now_message_is)
    await message.answer((await state.get_data()).get('text'))
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=await kb.add_attachments_keyboard({}))
    await set_message_id(msg_id)


async def broadcast_text_handler2(message: types.Message, state: FSMContext):
    await message.answer(msgs.now_message_is)
    await message.answer((await state.get_data()).get('text'))

    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=await kb.add_attachments_keyboard({}))
    await set_message_id(msg_id)


# @dp.callback_query_handler(state=Broadcast.next_step)
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
        keyboard = await kb.cur_atachments_keyboard(cur_atachments)
        if cur_atachments.get('photos'):
            await query.message.answer_photo(cur_atachments['photos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        elif cur_atachments.get('videos'):
            await query.message.answer_video(cur_atachments['videos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        else:
            await query.message.answer((await state.get_data()).get('text'), reply_markup=keyboard)

        msg_id = await query.message.answer(msgs.all_is_good, reply_markup=await kb.all_is_good_keyboard())
        await set_message_id(msg_id)


# @dp.callback_query_handler(text='all_is_good', state=Broadcast.conf_)
async def conf_(query: CallbackQuery, state: FSMContext):
    await Broadcast.tags.set()
    tags = await Tag.filter(visible=True)
    await query.message.answer(msgs.choose_tags_for_broadcast)
    msg_id = await query.message.answer(msgs.chosen_are_marked,
                                        reply_markup=await kb.choose_broadcast_tag_keyboard1(tags))
    await set_message_id(msg_id)


# @dp.message_handler(content_types=ContentType.PHOTO, state=Broadcast.attachment)
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
    keyboard = await kb.cur_atachments_keyboard(cur_atachments)
    await message.answer_photo(file_id, caption=(await state.get_data()).get('text'), reply_markup=keyboard)
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=await kb.video_handler_keyboard())
    await set_message_id(msg_id)


# @dp.message_handler(content_types=ContentType.VIDEO, state=Broadcast.attachment)
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
    keyboard = await kb.cur_atachments_keyboard(cur_atachments)
    await message.answer_video(file_id, caption=(await state.get_data()).get('text'), reply_markup=keyboard)
    msg_id = await message.answer(msgs.choose_what_to_do, reply_markup=await kb.video_handler_keyboard())
    await set_message_id(msg_id)


# @dp.message_handler(content_types=ContentType.TEXT, state=Broadcast.attachment)
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


# @dp.message_handler(content_types=ContentType.TEXT, state=Broadcast.attachment2)
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
    keyboard = await kb.cur_atachments_keyboard(cur_atachments)
    if cur_atachments.get('photos'):
        await message.answer_photo(cur_atachments['photos'][0], caption=(await state.get_data()).get('text'),
                                   reply_markup=keyboard)
    elif cur_atachments.get('videos'):
        await message.answer_video(cur_atachments['videos'][0], caption=(await state.get_data()).get('text'),
                                   reply_markup=keyboard)
    else:
        await message.answer((await state.get_data()).get('text'), reply_markup=keyboard)
    msg_id = await message.answer(msgs.choose_what_to_do,
                                  reply_markup=await kb.add_attachments_keyboard(cur_atachments))
    await set_message_id(msg_id)


# @dp.callback_query_handler(text_contains='choose_broadcast_tag_', state=Broadcast.tags)
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
    await query.message.edit_reply_markup(await kb.choose_broadcast_tag_keyboard(tags))


# @dp.callback_query_handler(text='tags_chosen', state=Broadcast.tags)
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
        keyboard = await kb.cur_atachments_keyboard(cur_atachments)
        if cur_atachments.get('photos'):
            await query.message.answer_photo(cur_atachments['photos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        elif cur_atachments.get('videos'):
            await query.message.answer_video(cur_atachments['videos'][0], caption=(await state.get_data()).get('text'),
                                             reply_markup=keyboard)
        else:
            await query.message.answer((await state.get_data()).get('text'), reply_markup=keyboard)

        msg_id = await query.message.answer(msgs.all_is_good, reply_markup=await kb.broadcast_confirm_keyboard())
        await set_message_id(msg_id)


# @dp.callback_query_handler(text='broadcast_wrong', state=Broadcast.confirmation)
async def broadcast_wrong(query: CallbackQuery, state: FSMContext):
    if query.message.chat.id not in admins:
        return
    await state.update_data(tags=None)
    await state.update_data(text=None)
    await state.update_data(attachment=None)
    await broadcast_handler(query, state)


# @dp.callback_query_handler(text='broadcast_confirm', state=Broadcast.confirmation)
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
        await query.message.answer(msgs.starting_broadcast, reply_markup=await kb.admin_keyboard())
        await state.finish()


async def create_broadcast_history(tags, text, photo, video, links):
    tags = [f'#{i.name.replace(" ", "_")}' for i in tags]
    tags_text = ' '.join(tags) + ' ⬇️'
    await bot.send_message(config.HISTORY_CHANNEL, tags_text)
    keyboard = await kb.create_broadcast_history_keyboard(links)
    if photo:
        await bot.send_photo(config.HISTORY_CHANNEL, open(photo, 'rb'), caption=text, reply_markup=keyboard)
    elif video:
        await bot.send_video(config.HISTORY_CHANNEL, open(video, 'rb'), caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(config.HISTORY_CHANNEL, text, reply_markup=keyboard)


# @dp.message_handler(text=btns.broadcast_history)
async def broadcast_history(message: types.Message, state: FSMContext, flag=False):
    if message.chat.id not in admins:
        return
    broadcast_history_all = await BroadcastHistory.all().count()
    broadcast_history_photos = await BroadcastHistory.filter(photo__not_isnull=True).count()
    broadcast_history_videos = await BroadcastHistory.filter(video__not_isnull=True).count()
    broadcast_history_links = await BroadcastHistory.filter(link__not_isnull=True).count()
    chat_link = await bot.export_chat_invite_link(config.HISTORY_CHANNEL)
    await message.answer(msgs.broadcast_history.format(broadcast_history_all, broadcast_history_photos,
                                                       broadcast_history_videos,
                                                       broadcast_history_links),
                         reply_markup=await kb.broadcast_history_link_keyboard(chat_link))


# @dp.callback_query_handler(text_contains='broadcast_history_tag_', state=BroadcastHistoryStates.tags)
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
    await query.message.edit_reply_markup(await kb.broadcast_history_tag_keyboard(tags))


# @dp.message_handler(text=btns.next, state=BroadcastHistoryStates.tags)
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

    msg_id = await message.answer(text, reply_markup=await kb.broadcast_history_keyboard(good_history, 0))
    await set_message_id(msg_id)
    # text += msgs.broadcast_history_end
    await message.answer(msgs.broadcast_history_end, reply_markup=await kb.back_keyboard())


# @dp.callback_query_handler(text_contains='broadcast_history_page_', state=BroadcastHistoryStates)
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

    await query.message.edit_text(text, reply_markup=await kb.broadcast_history_keyboard(good_history, page))


# @dp.message_handler(state=BroadcastHistoryStates.wait)
# @dp.message_handler(state=BroadcastHistoryStates.id)
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
