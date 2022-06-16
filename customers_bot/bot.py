from aiogram import Dispatcher, types

from aiogram.utils import executor, exceptions

from aiogram.dispatcher import FSMContext

import booking
from buttons import ru_buttons as btns
import asyncio
from models import *
from messages import ru_messages as msgs
from helpers_dir.google_sheet_functions import *
import datetime

import uuid
from bot_setup import bot, dp
from states import *
from keyboards import ru_keyboards as kb
import back
import settings_handlers


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


async def disableinfo(message: types.Message, state: FSMContext):
    chat_ = await AdminChat.get_or_none(chat_id=message.chat.id)
    if chat_:
        await chat_.delete()
        await message.answer(msgs.deleted_from_base)
    else:
        await message.answer(msgs.not_in_base)


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


async def back_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_message_handler(back.back_to_main, text=btns.back, state=Booking.restaurant)
    dispatcher.register_message_handler(back.back_to_restaurants, text=btns.back, state=Booking.how_many)
    dispatcher.register_message_handler(back.back_to_how_many, text=btns.back, state=Booking.date_booking)
    dispatcher.register_message_handler(back.back_to_date_booking, text=btns.back, state=Booking.approximate_time)
    dispatcher.register_message_handler(back.back_to_approximate_time, text=btns.back, state=Booking.exact_time)
    dispatcher.register_message_handler(back.back_to_exact_time, text=btns.back, state=Booking.table)
    dispatcher.register_message_handler(back.back_to_tables2, text=btns.back, state=Booking.confirm_table)
    dispatcher.register_message_handler(back.back_to_tables, text=btns.back, state=Booking.confirmation)
    dispatcher.register_message_handler(back.back_to_confirmation, text=btns.back, state=Booking.name)
    dispatcher.register_message_handler(back.back_to_name, text=btns.back, state=Booking.phone)
    dispatcher.register_message_handler(back.back_to_confirmation2, text=btns.back, state=Booking.final)
    dispatcher.register_message_handler(back.back_to_confirmation3, text=btns.back, state=Booking.remind)
    dispatcher.register_message_handler(back.back_to_change_contact, text=btns.back,
                                        state=[Changing.name, Changing.phone])
    dispatcher.register_message_handler(back.back_to_tags2, text=[btns.back, btns.confirm_choise],
                                        state=[ChangeTags.tag])
    dispatcher.register_message_handler(back.back_to_main_settings, text=btns.back,
                                        state=[Settings.change_tag, Settings.change_contact])
    dispatcher.register_message_handler(back.back_to_menu, text=btns.back)
    dispatcher.register_message_handler(back.settings_, text=btns.back_to_menu, state=[Changing, None])
    dispatcher.register_message_handler(back.settings2_, text=btns.back_to_settings, state=[Changing, None])


async def booking_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_message_handler(booking.start, commands='start', state=['*', None])
    dispatcher.register_callback_query_handler(booking.chosen_restaurant, text_contains=['restaurant_'],
                                               state=Booking.restaurant)
    dispatcher.register_callback_query_handler(booking.chosen_how_many, text_contains=['how_many_'],
                                               state=Booking.how_many)
    dispatcher.register_callback_query_handler(booking.bigger_number, text='bigger_number', state=Booking.how_many)
    dispatcher.register_callback_query_handler(booking.back_to_menu2, text='back_to_menu2', state=Booking.how_many)
    dispatcher.register_callback_query_handler(booking.chosen_date_booking, text_contains=['date_booking_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking.date_booking_later, text='date_booking_later',
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking.chosen_approximate_time, text_contains=['approximate_time_'],
                                               state=Booking.approximate_time)
    dispatcher.register_callback_query_handler(booking.chosen_exact_time, text_contains=['exact_time_'],
                                               state=Booking.exact_time)
    dispatcher.register_callback_query_handler(booking.choose_table_yes, text=['choose_table_yes'], state=Booking.table)
    dispatcher.register_callback_query_handler(booking.choose_table_no, text=['choose_table_no'], state=Booking.table)
    dispatcher.register_callback_query_handler(booking.tableimage_, text_contains=['tableimage_'], state=Booking.table)
    dispatcher.register_message_handler(booking.chosen_tables, state=Booking.table)
    dispatcher.register_callback_query_handler(booking.confirm_table, text='confirm_table', state=Booking.confirm_table)
    dispatcher.register_callback_query_handler(booking.confirmnot_table, text='confirmnot_table',
                                               state=Booking.confirm_table)
    dispatcher.register_callback_query_handler(booking.confirm, text='confirm', state=Booking.confirmation)
    dispatcher.register_callback_query_handler(booking.register, text='register', state=Booking.name)
    dispatcher.register_message_handler(booking.name_handler, lambda text: text not in btns.reply_keyboard_buttons,
                                        state=Booking.name)
    dispatcher.register_message_handler(booking.contact_handler, content_types=types.ContentType.CONTACT,
                                        state=Booking.name)
    dispatcher.register_message_handler(booking.phone_handler, lambda text: text not in btns.reply_keyboard_buttons,
                                        state=Booking.phone)
    dispatcher.register_callback_query_handler(booking.final_confirm, text='final_confirm', state=Booking.final)
    dispatcher.register_callback_query_handler(booking.remind_handler, text_contains=['remind_'], state=Booking.remind)
    dispatcher.register_callback_query_handler(booking.wrong_final_confirm, text='wrong_final_confirm',
                                               state=Booking.final)
    dispatcher.register_callback_query_handler(booking.prev_year, text_contains=['PREV-YEAR_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking.next_year, text_contains=['NEXT-YEAR_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking.prev_month, text_contains=['PREV-MONTH_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking.next_month, text_contains=['NEXT-MONTH_'],
                                               state=Booking.date_booking)
    dispatcher.register_message_handler(booking.settings_yes_no, text=btns.menu, state=Booking)
    dispatcher.register_callback_query_handler(booking.no_interrupt, text='no_interrupt', state=Booking)
    dispatcher.register_callback_query_handler(booking.yes_interrupt, text='yes_interrupt', state=Booking)
    dispatcher.register_message_handler(booking.booking_handler, text=[btns.booking, btns.new_booking],
                                        state=['*', None])
    dispatcher.register_callback_query_handler(booking.new_booking_handler, text='new_booking', state=[None, '*'])
    dispatcher.register_callback_query_handler(booking.presence_yes_callback, text='presence_yes_', state=[None, '*'])
    dispatcher.register_callback_query_handler(booking.presence_maybe_callback, text='presence_maybe_',
                                               state=[None, '*'])
    dispatcher.register_callback_query_handler(booking.presence_no_callback, text='presence_no', state=[None, '*'])


async def settings_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_callback_query_handler(settings_handlers.settings_callback, text='settings', state='*')
    dispatcher.register_message_handler(settings_handlers.settings, text=btns.menu, state='*')
    dispatcher.register_message_handler(settings_handlers.settings_menu, text=btns.settings_menu, state=["*", None])
    dispatcher.register_callback_query_handler(settings_handlers.change_contact, text='change_contact')
    dispatcher.register_callback_query_handler(settings_handlers.change_tag, text='change_tags')
    dispatcher.register_callback_query_handler(settings_handlers.choose_all_tags, text='choose_all_tags',
                                               state=Settings.change_tag)
    dispatcher.register_callback_query_handler(settings_handlers.choose_no_one_tags, text='choose_no_one_tags',
                                               state=Settings.change_tag)
    dispatcher.register_callback_query_handler(settings_handlers.choose_what_to_on_tags, text='choose_what_to_on_tags',
                                               state=Settings.change_tag)
    dispatcher.register_callback_query_handler(settings_handlers.choose_what_to_on_tags_handler,
                                               text_contains='choose_what_to_on_tags_', state=ChangeTags.tag)
    dispatcher.register_callback_query_handler(settings_handlers.back_to_tags, text='back_to_tags',
                                               state=ChangeTags.tag)
    dispatcher.register_callback_query_handler(settings_handlers.change_name, text='change_name',
                                               state=Settings.change_contact)
    dispatcher.register_callback_query_handler(settings_handlers.change_phone, text='change_phone',
                                               state=Settings.change_contact)
    dispatcher.register_message_handler(settings_handlers.change_name_, text=btns.change_name)
    dispatcher.register_message_handler(settings_handlers.change_phone_, text=btns.change_phone)
    dispatcher.register_message_handler(settings_handlers.changing_name,
                                        lambda text: text not in btns.reply_keyboard_buttons, state=Changing.name)
    dispatcher.register_message_handler(settings_handlers.changing_phone,
                                        lambda text: text not in btns.reply_keyboard_buttons, state=Changing.phone)


async def other_funcs_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_message_handler(enableinfo, commands=['enableinfo'], chat_type=['supergroup', 'group'])
    dispatcher.register_message_handler(disableinfo, commands=['disableinfo'], chat_type=['supergroup', 'group'])
    dispatcher.register_message_handler(getcode, commands=['get'])


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
        logger.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        logger.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        logger.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await broadcast_sender(user_id, text,
                                      reply_markup=reply_markup, markdown=markdown, photo=photo,
                                      video=video)  # Recursive call
    except exceptions.UserDeactivated:
        logger.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.MigrateToChat as e:
        logger.exception(f"Target [ID:{user_id}]: failed")
        logger.error(text)
        adm_chat = await AdminChat.get_or_none(chat_id=user_id)
        if adm_chat:
            adm_chat.chat_id = e.migrate_to_chat_id
            await adm_chat.save()
        return await broadcast_sender(adm_chat.chat_id, text,
                                      reply_markup=reply_markup, markdown=markdown, photo=photo,
                                      video=video)
    except exceptions.TelegramAPIError:
        logger.exception(f"Target [ID:{user_id}]: failed")
        logger.error(text)

    else:
        logger.info(f"Target [ID:{user_id}]: success")
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
        # now = now.replace(day=31, hour=12, minute=15)
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
            text = msgs.reminder.format(msgs.restaurants[(await order.restaurant).id],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        for order in orders_6:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[(await order.restaurant).id],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        for order in orders_12:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[(await order.restaurant).id],
                                        order.date, order.time, config.PHONES[order.restaurant])
            await broadcast_sender(user.chat_id, text)
            order.reminded = True
            await order.save()
        for order in orders_24:
            user = await order.user
            text = msgs.reminder.format(msgs.restaurants[(await order.restaurant).id],
                                        order.date, order.time, config.PHONES[(await order.restaurant).id])
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
                keyboard = await kb.brodcast_links_keyboard(links)
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


async def setup_handlers(dispatcher):
    await back_handlers_setup(dispatcher)
    await settings_handlers_setup(dispatcher)
    await other_funcs_handlers_setup(dispatcher)
    await booking_handlers_setup(dispatcher)



async def on_startup(*args):
    await init()
    await setup_handlers(dp)
    asyncio.create_task(updater_restaurants())
    asyncio.create_task(updater_tables())
    asyncio.create_task(reminder())
    asyncio.create_task(archivator())
    asyncio.create_task(broadcaster())
    asyncio.create_task(deleter_orders())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
