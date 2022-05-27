import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aiogram import Dispatcher
from aiogram.types import ContentType
from aiogram.utils import executor
# from aiogram.contrib.middlewares.logging import LoggingMiddleware

from models import *
from states_admin import *
from bot_admin_setup import dp
from buttons import ru_buttons as btns
from admin_bot import admin_funcs, back_admin, booking_admin


async def back_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_message_handler(back_admin.back_to_admin_menu, text=btns.back, state=Broadcast.text)
    dispatcher.register_message_handler(back_admin.back_to_broadcast_text, text=btns.back, state=Broadcast.next_step)
    dispatcher.register_message_handler(back_admin.back_to_broadcast_next_step, text=btns.back,
                                        state=Broadcast.attachment)
    dispatcher.register_message_handler(back_admin.back_to_broadcast_atach, text=btns.back, state=Broadcast.attachment2)
    dispatcher.register_message_handler(back_admin.back_to_broadcast_next_step2, text=btns.back,
                                        state=[Broadcast.conf_, Broadcast.tags])
    dispatcher.register_message_handler(back_admin.back_to_tags_menu, text=btns.back, state=[AddTag.name, DelTag.name])
    dispatcher.register_message_handler(back_admin.back_to_del_tags, text=btns.back, state=DelTag.confirmation)
    dispatcher.register_message_handler(back_admin.back_to_start, text=btns.back, state=BroadcastHistoryStates.tags)
    dispatcher.register_message_handler(back_admin.back_to_broadcast_history, text=btns.back,
                                        state=[BroadcastHistoryStates.id, BroadcastHistoryStates.wait])
    dispatcher.register_message_handler(back_admin.back_to_main, text=btns.back, state=Booking.restaurant)
    dispatcher.register_message_handler(back_admin.back_to_restaurants, text=btns.back, state=Booking.how_many)
    dispatcher.register_message_handler(back_admin.back_to_how_many, text=btns.back, state=Booking.date_booking)
    dispatcher.register_message_handler(back_admin.back_to_date_booking, text=btns.back, state=Booking.approximate_time)
    dispatcher.register_message_handler(back_admin.back_to_approximate_time, text=btns.back, state=Booking.exact_time)
    dispatcher.register_message_handler(back_admin.back_to_exact_time, text=btns.back, state=Booking.table)
    dispatcher.register_message_handler(back_admin.back_to_tables, text=btns.back, state=Booking.confirmation)
    dispatcher.register_message_handler(back_admin.back_to_confirmation, text=btns.back, state=Booking.name)
    dispatcher.register_message_handler(back_admin.back_to_name, text=btns.back, state=Booking.phone)
    dispatcher.register_message_handler(back_admin.back_to_confirmation2, text=btns.back, state=Booking.final)
    dispatcher.register_message_handler(back_admin.back_to_confirmation3, text=btns.back, state=Booking.remind)
    dispatcher.register_message_handler(back_admin.back_to_admin_menu2, text=btns.back)


async def booking_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_message_handler(booking_admin.start, commands='start', state='*')
    dispatcher.register_message_handler(booking_admin.new_booking, text=btns.new_booking, state='*')
    dispatcher.register_callback_query_handler(booking_admin.chosen_restaurant, text_contains=['restaurant_'],
                                               state=Booking.restaurant)
    dispatcher.register_callback_query_handler(booking_admin.chosen_how_many, text_contains=['how_many_'],
                                               state=Booking.how_many)
    dispatcher.register_callback_query_handler(booking_admin.bigger_number, text='bigger_number',
                                               state=Booking.how_many)
    dispatcher.register_callback_query_handler(booking_admin.back_to_menu2, text='back_to_menu2',
                                               state=Booking.how_many)
    dispatcher.register_callback_query_handler(booking_admin.chosen_date_booking, text_contains=['date_booking_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking_admin.date_booking_later, text='date_booking_later',
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking_admin.chosen_approximate_time,
                                               text_contains=['approximate_time_'], state=Booking.approximate_time)
    dispatcher.register_callback_query_handler(booking_admin.chosen_exact_time, text_contains=['exact_time_'],
                                               state=Booking.exact_time)
    dispatcher.register_callback_query_handler(booking_admin.choose_table_yes, text=['choose_table_yes'],
                                               state=Booking.table)
    dispatcher.register_callback_query_handler(booking_admin.choose_table_no, text=['choose_table_no'],
                                               state=Booking.table)
    dispatcher.register_callback_query_handler(booking_admin.tableimage_, text_contains=['tableimage_'],
                                               state=Booking.table)
    dispatcher.register_message_handler(booking_admin.chosen_tables, state=Booking.table)
    dispatcher.register_callback_query_handler(booking_admin.confirm, text='confirm', state=Booking.confirmation)
    dispatcher.register_callback_query_handler(booking_admin.register, text='register', state=Booking.name)
    dispatcher.register_message_handler(booking_admin.name_handler,
                                        lambda text: text not in btns.reply_keyboard_buttons, state=Booking.name)
    dispatcher.register_message_handler(booking_admin.phone_handler,
                                        lambda text: text not in btns.reply_keyboard_buttons, state=Booking.phone)
    dispatcher.register_callback_query_handler(booking_admin.final_confirm, text='final_confirm', state=Booking.final)
    dispatcher.register_callback_query_handler(booking_admin.remind_handler, text_contains=['remind_'],
                                               state=Booking.remind)
    dispatcher.register_callback_query_handler(booking_admin.wrong_final_confirm, text='wrong_final_confirm',
                                               state=Booking.final)
    dispatcher.register_message_handler(booking_admin.settings_yes_no, text=btns.menu, state=Booking)
    dispatcher.register_callback_query_handler(booking_admin.yes_interrupt, text='yes_interrupt', state=Booking)
    dispatcher.register_callback_query_handler(booking_admin.no_interrupt, text='no_interrupt', state=Booking)
    dispatcher.register_callback_query_handler(booking_admin.prev_year, text_contains=['PREV-YEAR_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking_admin.next_year, text_contains=['NEXT-YEAR_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking_admin.prev_month, text_contains=['PREV-MONTH_'],
                                               state=Booking.date_booking)
    dispatcher.register_callback_query_handler(booking_admin.next_month, text_contains=['NEXT-MONTH_'],
                                               state=Booking.date_booking)


async def admin_funcs_handlers_setup(dispatcher: Dispatcher):
    dispatcher.register_message_handler(admin_funcs.del_handler, commands=['del'])
    dispatcher.register_callback_query_handler(admin_funcs.del_booking_handler, text_contains='del_booking_',
                                               state=DelBooking.confirmation)
    dispatcher.register_callback_query_handler(admin_funcs.restore_order, text_contains='restore_order_')
    dispatcher.register_message_handler(admin_funcs.settings, text=btns.menu, state='*')
    dispatcher.register_message_handler(admin_funcs.admin_menu, text=btns.admin_menu)
    dispatcher.register_callback_query_handler(admin_funcs.admin_tags, text='admin_tags',
                                               state=[AddTag.name, DelTag.name, None])
    dispatcher.register_message_handler(admin_funcs.admin_tags, text=btns.tags)
    dispatcher.register_callback_query_handler(admin_funcs.update_visible, text_contains='update_visible_')
    dispatcher.register_callback_query_handler(admin_funcs.add_tag, text='add_tag')
    dispatcher.register_message_handler(admin_funcs.add_tag_handler, state=AddTag.name)
    dispatcher.register_callback_query_handler(admin_funcs.del_tag, text='del_tag')
    dispatcher.register_callback_query_handler(admin_funcs.del_tag_handler, text_contains='del_tag_', state=DelTag.name)
    dispatcher.register_callback_query_handler(admin_funcs.del_tagconfirm, text_contains='del_tagconfirm_',
                                               state=DelTag.confirmation)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_handler, text='broadcast')
    dispatcher.register_message_handler(admin_funcs.broadcast_menu, text=btns.broadcast)
    dispatcher.register_message_handler(admin_funcs.broadcast_text_handler, state=Broadcast.text)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_next_step_handler, state=Broadcast.next_step)
    dispatcher.register_callback_query_handler(admin_funcs.conf_, text='all_is_good', state=Broadcast.conf_)
    dispatcher.register_message_handler(admin_funcs.photo_handler, content_types=ContentType.PHOTO,
                                        state=Broadcast.attachment)
    dispatcher.register_message_handler(admin_funcs.video_handler, content_types=ContentType.VIDEO,
                                        state=Broadcast.attachment)
    dispatcher.register_message_handler(admin_funcs.link_handler, content_types=ContentType.TEXT,
                                        state=Broadcast.attachment)
    dispatcher.register_message_handler(admin_funcs.link2_handler, content_types=ContentType.TEXT,
                                        state=Broadcast.attachment2)
    dispatcher.register_callback_query_handler(admin_funcs.choose_broadcast_tag_handler,
                                               text_contains='choose_broadcast_tag_', state=Broadcast.tags)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_next, text='tags_chosen', state=Broadcast.tags)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_wrong, text='broadcast_wrong',
                                               state=Broadcast.confirmation)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_confirm, text='broadcast_confirm',
                                               state=Broadcast.confirmation)
    dispatcher.register_message_handler(admin_funcs.broadcast_history, text=btns.broadcast_history)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_history_tag,
                                               text_contains='broadcast_history_tag_',
                                               state=BroadcastHistoryStates.tags)
    dispatcher.register_message_handler(admin_funcs.broadcast_next3, text=btns.next, state=BroadcastHistoryStates.tags)
    dispatcher.register_callback_query_handler(admin_funcs.broadcast_history_page,
                                               text_contains='broadcast_history_page_', state=BroadcastHistoryStates)
    dispatcher.register_message_handler(admin_funcs.broadcast_history_id,
                                        state=[BroadcastHistoryStates.wait, BroadcastHistoryStates.id])


async def setup_handlers(dispatcher):
    await back_handlers_setup(dispatcher)
    await admin_funcs_handlers_setup(dispatcher)
    await booking_handlers_setup(dispatcher)


async def on_startup(*args):
    await init()
    await setup_handlers(dp)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
