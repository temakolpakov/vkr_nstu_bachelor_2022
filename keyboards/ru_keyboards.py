import calendar
import datetime

from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton
import buttons.ru_buttons as btns
from models import TagSubscription

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


async def settings_yes_no_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes_interrupt, callback_data='yes_interrupt'),
                 InlineKeyboardButton(btns.no_interrupt, callback_data='no_interrupt'))
    return keyboard


async def settings_menu_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.change_name, callback_data='change_name'))
    keyboard.add(InlineKeyboardButton(btns.change_phone, callback_data='change_phone'))
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


async def edit_restaurants_keyboard(restaurant_number):
    keyboard = InlineKeyboardMarkup()
    if restaurant_number == 1:
        keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.address1, callback_data='restaurant_1'))
        keyboard.add(InlineKeyboardButton(btns.address2, callback_data='restaurant_2'))
        keyboard.add(InlineKeyboardButton(btns.address3, callback_data='restaurant_3'))
    elif restaurant_number == 2:
        keyboard.add(
            InlineKeyboardButton(btns.address1, callback_data='restaurant_1'))
        keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.address2, callback_data='restaurant_2'))
        keyboard.add(InlineKeyboardButton(btns.address3, callback_data='restaurant_3'))
    elif restaurant_number == 3:
        keyboard.add(
            InlineKeyboardButton(btns.address1, callback_data='restaurant_1'))
        keyboard.add(InlineKeyboardButton(btns.address2, callback_data='restaurant_2'))
        keyboard.add(
            InlineKeyboardButton(btns.check_mark + btns.address3, callback_data='restaurant_3'))
    return keyboard


async def date_booking_keyboard(today_cut, tomorrow_cut, today, tomorrow, day_after_tomorrow_cut,
                                day_after_tomorrow):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.today.format(today_cut), callback_data=f'date_booking_{today}'))
    keyboard.add(InlineKeyboardButton(btns.tomorrow.format(tomorrow_cut), callback_data=f'date_booking_{tomorrow}'))
    keyboard.add(InlineKeyboardButton(btns.day_after_tomorrow.format(day_after_tomorrow_cut),
                                      callback_data=f'date_booking_{day_after_tomorrow}'))
    keyboard.add(InlineKeyboardButton(btns.later, callback_data=f'date_booking_later'))
    return keyboard


async def edit_chosen_how_many_keyboard(how_many):
    keyboard = InlineKeyboardMarkup()
    btns_rows = []
    for i in range(1, 7):
        if i == how_many:
            btns_rows.append(InlineKeyboardButton(btns.check_mark + str(i), callback_data=f'how_many_{i}'))
        else:
            btns_rows.append(InlineKeyboardButton(str(i), callback_data=f'how_many_{i}'))

    keyboard.row(*btns_rows[:3])
    keyboard.row(*btns_rows[3:])
    if how_many == 7:
        keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton(btns.check_mark + '7', callback_data='how_many_7'),
                     InlineKeyboardButton(' ', callback_data=' '))
    else:
        keyboard.row(InlineKeyboardButton(' ', callback_data=' '),
                     InlineKeyboardButton('7', callback_data='how_many_7'),
                     InlineKeyboardButton(' ', callback_data=' '))
    keyboard.add(InlineKeyboardButton(btns.bigger_number, callback_data='bigger_number'))
    return keyboard


async def back_to_menu2_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.back_to_menu2, callback_data='back_to_menu2'))
    return keyboard


async def change_tags_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.choose_all, callback_data='choose_all_tags'),
                 InlineKeyboardButton(btns.choose_no_one, callback_data='choose_no_one_tags'))
    keyboard.add(InlineKeyboardButton(btns.choose_what_to_on, callback_data='choose_what_to_on_tags'))
    return keyboard


async def choose_what_to_on_tags_keyboard(tags, user):
    keyboard = InlineKeyboardMarkup()
    for i in tags:
        rel = await TagSubscription.get_or_none(user=user, tag=i)
        if rel:
            keyboard.add(
                InlineKeyboardButton(btns.check_mark + i.name, callback_data=f'choose_what_to_on_tags_{i.id}'))
        else:
            keyboard.add(InlineKeyboardButton(i.name, callback_data=f'choose_what_to_on_tags_{i.id}'))
    return keyboard


async def confirm_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.confirm_choise))
    return keyboard


async def remind_keyboard(remind_btns):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(remind_btns[0][1], callback_data=f'remind_{remind_btns[0][0]}'),
                 InlineKeyboardButton(remind_btns[1][1], callback_data=f'remind_{remind_btns[1][0]}'))
    keyboard.add(InlineKeyboardButton(remind_btns[2][1], callback_data=f'remind_{remind_btns[2][0]}'),
                 InlineKeyboardButton(remind_btns[3][1], callback_data=f'remind_{remind_btns[3][0]}'))
    keyboard.add(InlineKeyboardButton(remind_btns[4][1], callback_data=f'remind_{remind_btns[4][0]}'))
    return keyboard


async def presence_yes_keyboard(order):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(btns.check_mark + btns.presence_yes, callback_data=f'presence_yes_{order.id}'))
    keyboard.add(InlineKeyboardButton(btns.presence_no, callback_data=f'presence_maybe_{order.id}'))
    return keyboard


async def precense_no_keyboard(order):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(btns.presence_yes, callback_data=f'presence_yes_{order.id}'))
    keyboard.add(
        InlineKeyboardButton(btns.check_mark + btns.presence_no, callback_data=f'presence_maybe_{order.id}'))
    return keyboard


async def precense_2_keyboard(order_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.presence_no2, callback_data=f'presence_no_{order_id}'))
    keyboard.add(InlineKeyboardButton(btns.presence_yes2, callback_data=f'presence_yes_{order_id}'))
    return keyboard


async def presence_no_2_keyboard(order_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(btns.check_mark + btns.presence_no2, callback_data=f'presence_no_{order_id}'))

    keyboard.add(InlineKeyboardButton(btns.presence_yes2, callback_data=f'presence_yes_{order_id}'))
    return keyboard


async def brodcast_links_keyboard(links):
    keyboard = InlineKeyboardMarkup()
    for k in links:
        keyboard.add(InlineKeyboardButton(links[k][0], url=links[k][1]))
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


async def confirm_table_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes, callback_data='confirm_table'),
                 InlineKeyboardButton(btns.no, callback_data='confirmnot_table'))
    return keyboard


async def confirm_booking_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.confirm, callback_data='confirm'),
                 InlineKeyboardButton(btns.wrong, callback_data='new_booking'))
    return keyboard


async def final_confirm_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(btns.yes2, callback_data='final_confirm'),
                 InlineKeyboardButton(btns.no2, callback_data='wrong_final_confirm'))
    return keyboard


async def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.new_booking))
    keyboard.add(KeyboardButton(btns.settings_menu))
    return keyboard


async def back_to_settings_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.back_to_settings))
    return keyboard


async def booking_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.back))
    keyboard.add(KeyboardButton(btns.menu))
    return keyboard

async def back_and_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.give_contact, request_contact=True))
    keyboard.add(KeyboardButton(btns.back))
    keyboard.add(KeyboardButton(btns.menu))
    return keyboard

async def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(btns.back))
    return keyboard