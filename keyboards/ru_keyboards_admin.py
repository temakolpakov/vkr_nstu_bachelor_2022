import calendar
import datetime

from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton
import buttons.ru_buttons as btns
from models import TagSubscription, Tag

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
                        day2 = btns.check_mark + f'{day}'
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
                        day2 = btns.check_mark + f'{day}'
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


async def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.new_booking))
    return keyboard


async def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.back))
    return keyboard

async def booking_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.back))
    keyboard.add(KeyboardButton(btns.menu))
    return keyboard

async def restaurants_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.address1, callback_data='restaurant_1'))
    keyboard.add(InlineKeyboardButton(btns.address2, callback_data='restaurant_2'))
    keyboard.add(InlineKeyboardButton(btns.address3, callback_data='restaurant_3'))
    return keyboard


async def how_many_keyboard():
    keyboard = InlineKeyboardMarkup()
    btns_rows = [InlineKeyboardButton(str(i), callback_data=f'how_many_{i}') for i in range(1, 7)]
    keyboard.row(*btns_rows[:3])
    keyboard.row(*btns_rows[3:])
    keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                 InlineKeyboardButton('7', callback_data='how_many_7'),
                 InlineKeyboardButton(' ', callback_data=' '))
    keyboard.add(InlineKeyboardButton(btns.bigger_number, callback_data='bigger_number'))
    return keyboard


async def edit_restaurants_keyboard(restaurant_number):
    edit_keyboard = InlineKeyboardMarkup()
    if restaurant_number == 1:
        edit_keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.address1, callback_data='restaurant_1'))
        edit_keyboard.add(InlineKeyboardButton(btns.address2, callback_data='restaurant_2'))
        edit_keyboard.add(InlineKeyboardButton(btns.address3, callback_data='restaurant_3'))
    elif restaurant_number == 2:
        edit_keyboard.add(
            InlineKeyboardButton(btns.address1, callback_data='restaurant_1'))
        edit_keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.address2, callback_data='restaurant_2'))
        edit_keyboard.add(InlineKeyboardButton(btns.address3, callback_data='restaurant_3'))
    elif restaurant_number == 3:
        edit_keyboard.add(
            InlineKeyboardButton(btns.address1, callback_data='restaurant_1'))
        edit_keyboard.add(InlineKeyboardButton(btns.address2, callback_data='restaurant_2'))
        edit_keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.address3, callback_data='restaurant_3'))
    return edit_keyboard


async def edit_how_many_keyboard(how_many):
    edit_keyboard = InlineKeyboardMarkup()
    btns_rows = []
    for i in range(1, 7):
        if i == how_many:
            btns_rows.append(InlineKeyboardButton(btns.check_mark + str(i), callback_data=f'how_many_{i}'))
        else:
            btns_rows.append(InlineKeyboardButton(str(i), callback_data=f'how_many_{i}'))

    edit_keyboard.row(*btns_rows[:3])
    edit_keyboard.row(*btns_rows[3:])
    if how_many == 7:
        edit_keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                          InlineKeyboardButton(btns.check_mark + '7', callback_data='how_many_7'),
                          InlineKeyboardButton(' ', callback_data=' '))
    else:
        edit_keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                          InlineKeyboardButton('7', callback_data='how_many_7'),
                          InlineKeyboardButton(' ', callback_data=' '))
    edit_keyboard.add(InlineKeyboardButton(btns.bigger_number, callback_data='bigger_number'))
    return edit_keyboard


async def date_booking_keyboard(today_cut, tomorrow_cut, today, tomorrow, day_after_tomorrow_cut,
                                day_after_tomorrow):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.today.format(today_cut), callback_data=f'date_booking_{today}'))
    keyboard.add(InlineKeyboardButton(btns.tomorrow.format(tomorrow_cut), callback_data=f'date_booking_{tomorrow}'))
    keyboard.add(InlineKeyboardButton(btns.day_after_tomorrow.format(day_after_tomorrow_cut),
                                      callback_data=f'date_booking_{day_after_tomorrow}'))
    keyboard.add(InlineKeyboardButton(btns.later, callback_data=f'date_booking_later'))
    return keyboard


async def bigger_number_how_many_keyboard():
    keyboard = InlineKeyboardMarkup()
    btns_rows = []
    for i in range(1, 7):
        btns_rows.append(InlineKeyboardButton(str(i), callback_data=f'how_many_{i}'))
    keyboard.row(*btns_rows[:3])
    keyboard.row(*btns_rows[3:])
    keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                 InlineKeyboardButton('7', callback_data='how_many_7'),
                 InlineKeyboardButton(' ', callback_data=' '))
    keyboard.add(InlineKeyboardButton(btns.check_mark + btns.bigger_number, callback_data='bigger_number'))
    return keyboard


async def back_to_menu2_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.back_to_menu2, callback_data='back_to_menu2'))
    return keyboard


async def chosen_date_booking_keyboard(date_booking, today, tomorrow, day_after_tomorrow):
    keyboard = InlineKeyboardMarkup()
    if date_booking == today:
        keyboard.add(InlineKeyboardButton(btns.check_mark + btns.today.format(today),
                                          callback_data=f'date_booking_{today}'))
    else:
        keyboard.add(InlineKeyboardButton(btns.today.format(today), callback_data=f'date_booking_{today}'))
    if date_booking == tomorrow:
        keyboard.add(InlineKeyboardButton(btns.check_mark + btns.tomorrow.format(tomorrow),
                                          callback_data=f'date_booking_{tomorrow}'))
    else:
        keyboard.add(
            InlineKeyboardButton(btns.tomorrow.format(tomorrow), callback_data=f'date_booking_{tomorrow}'))
    if date_booking == day_after_tomorrow:
        keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.day_after_tomorrow.format(day_after_tomorrow),
                                 callback_data=f'date_booking_{day_after_tomorrow}'))
    else:
        keyboard.add(InlineKeyboardButton(btns.day_after_tomorrow.format(day_after_tomorrow),
                                          callback_data=f'date_booking_{day_after_tomorrow}'))
    keyboard.add(InlineKeyboardButton(btns.later, callback_data=f'date_booking_later'))
    return keyboard


async def approximate_time_keyboard(approximate_times):
    keyboard = InlineKeyboardMarkup()
    first_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1]}') for i in approximate_times[:3]]
    second_row = [InlineKeyboardButton(i[0], callback_data=f'approximate_time_{i[1]}') for i in approximate_times[3:]]
    keyboard.row(*first_row)
    keyboard.row(*second_row)
    return keyboard


async def exact_time_keyboard(time_00, time_15, time_30, time_45):
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
    return keyboard

async def choose_table_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes2, callback_data='choose_table_yes'),
                 InlineKeyboardButton(btns.no2, callback_data='choose_table_no'))
    return keyboard


async def choose_table_yes_keyboard(colored_images):
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton('Зал 2 ' + btns.page_next, callback_data='tableimage_1'))
    return keyboard


async def tableimage_keyboard(colored_images, image_number):
    keyboard = InlineKeyboardMarkup()
    if len(colored_images) > 1:
        if image_number == len(colored_images) - 1:
            keyboard.add(InlineKeyboardButton(btns.page_back + f' Зал {image_number}',
                                              callback_data=f'tableimage_{image_number - 1}'),
                         InlineKeyboardButton(' ', callback_data=' '))
        elif image_number == 0:
            keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                         InlineKeyboardButton(f'Зал {image_number + 2} ' + btns.page_next,
                                              callback_data=f'tableimage_{image_number + 1}'))
        else:
            keyboard.add(InlineKeyboardButton(btns.page_back + f' Зал {image_number}',
                                              callback_data=f'tableimage_{image_number - 1}'),
                         InlineKeyboardButton(f'Зал {image_number + 2} ' + btns.page_next,
                                              callback_data=f'tableimage_{image_number + 1}'))
    return keyboard



async def confirm_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.confirm, callback_data='confirm'),
                 InlineKeyboardButton(btns.wrong, callback_data='new_booking'))
    return keyboard

async def final_confirm_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes2, callback_data='final_confirm'),
                 InlineKeyboardButton(btns.no2, callback_data='wrong_final_confirm'))
    return keyboard

async def remind_keyboard(remind_btns):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(remind_btns[0][1], callback_data=f'remind_{remind_btns[0][0]}'),
                 InlineKeyboardButton(remind_btns[1][1], callback_data=f'remind_{remind_btns[1][0]}'))
    keyboard.add(InlineKeyboardButton(remind_btns[2][1], callback_data=f'remind_{remind_btns[2][0]}'),
                 InlineKeyboardButton(remind_btns[3][1], callback_data=f'remind_{remind_btns[3][0]}'))
    keyboard.add(InlineKeyboardButton(remind_btns[4][1], callback_data=f'remind_{remind_btns[4][0]}'))
    return keyboard


async def del_booking_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes, callback_data='del_booking_yes'),
                 InlineKeyboardButton(btns.no, callback_data='del_booking_no'))
    return keyboard

async def interrupt_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes_interrupt, callback_data='yes_interrupt'),
                 InlineKeyboardButton(btns.no_interrupt, callback_data='no_interrupt'))
    return keyboard


async def restore_order_keyboard(order):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.restore_order, callback_data=f'restore_order_{order.id}'))
    return keyboard


async def cur_atachments_keyboard(cur_atachments):
    keyboard = InlineKeyboardMarkup()
    if cur_atachments.get('links'):
        for i in cur_atachments['links']:
            keyboard.add(InlineKeyboardButton(i[0], url=i[1]))
    return keyboard


async def add_attachments_keyboard(cur_atachments):
    keyboard = InlineKeyboardMarkup()
    if not cur_atachments.get('photos') and not cur_atachments.get('videos'):
        keyboard.add(InlineKeyboardButton(btns.add_photo, callback_data='add_photo'))
        keyboard.add(InlineKeyboardButton(btns.add_video, callback_data='add_video'))
    keyboard.add(InlineKeyboardButton(btns.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(btns.all_ready, callback_data='all_ready'))
    return keyboard


async def video_handler_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.add_link, callback_data='add_link'))
    keyboard.add(InlineKeyboardButton(btns.all_ready, callback_data='all_ready'))
    return keyboard


async def admin_menu_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.broadcast, callback_data='broadcast'),
                 InlineKeyboardButton(btns.tags, callback_data='admin_tags'))
    return keyboard


async def admin_tags_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.add_tag, callback_data='add_tag'))
    keyboard.add(InlineKeyboardButton(btns.del_tag, callback_data='del_tag'))
    return keyboard


async def update_visible_keyboard(tags):
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        check = ''
        if i.visible:
            check = btns.check_mark
        keyboard.add(InlineKeyboardButton(check + ' ' + i.name, callback_data=f'update_visible_{i.id}'))
    keyboard.add(InlineKeyboardButton(btns.add_tag, callback_data='add_tag'),
                 InlineKeyboardButton(btns.del_tag, callback_data='del_tag'))
    return keyboard


async def del_tag_keyboard(tags):
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        keyboard.add(InlineKeyboardButton(i.name, callback_data=f'del_tag_{i.id}'))
    return keyboard


async def del_tagconfirm_keyboard(to_delete):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.confirm, callback_data=f'del_tagconfirm_{to_delete}'))
    return keyboard


async def all_is_good_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.all_is_good, callback_data='all_is_good'))
    return keyboard


async def choose_broadcast_tag_keyboard1(tags):
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_broadcast_tag_{i.id}'))
    return keyboard


async def choose_broadcast_tag_keyboard(tags):
    keyboard = InlineKeyboardMarkup()
    tags_all = await Tag.filter(visible=True)
    for i in tags_all:
        if i.id in tags:
            keyboard.add(
                InlineKeyboardButton(btns.check_mark + i.name, callback_data=f'choose_broadcast_tag_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_broadcast_tag_{i.id}'))
    if len(tags):
        keyboard.add(InlineKeyboardButton(btns.next, callback_data='tags_chosen'))
    return keyboard


async def broadcast_confirm_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes, callback_data='broadcast_confirm'),
                 InlineKeyboardButton(btns.no, callback_data='broadcast_wrong'))
    return keyboard


async def create_broadcast_history_keyboard(links):
    keyboard = InlineKeyboardMarkup()
    for i in links:
        keyboard.add(InlineKeyboardButton(links[i][0], url=links[i][1]))
    return keyboard


async def broadcast_history_link_keyboard(chat_link):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.chat_link, url=chat_link))
    return keyboard


async def broadcast_history_keyboard(good_history, page):
    keyboard = InlineKeyboardMarkup()
    if len(good_history[page * 5:page * 5 + 5]) == 5:
        if page != 0:
            keyboard.add(InlineKeyboardButton(btns.page_back, callback_data=f'broadcast_history_page_{page - 1}'),
                         InlineKeyboardButton(btns.page_next, callback_data=f'broadcast_history_page_{page + 1}'))
        else:
            keyboard.add(InlineKeyboardButton(' ', callback_data=' '),
                         InlineKeyboardButton(btns.page_next, callback_data=f'broadcast_history_page_{page + 1}'))
    else:
        keyboard.add(InlineKeyboardButton(btns.page_back, callback_data=f'broadcast_history_page_{page - 1}'),
                     InlineKeyboardButton(' ', callback_data=' '))
    return keyboard


async def broadcast_history_tag_keyboard(tags):
    keyboard = InlineKeyboardMarkup()
    tags_all = await Tag.filter(visible=True)
    for i in tags_all:
        if i.id in tags:
            keyboard.add(
                InlineKeyboardButton(btns.check_mark + i.name, callback_data=f'broadcast_history_tag_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'broadcast_history_tag_{i.id}'))
    return keyboard
