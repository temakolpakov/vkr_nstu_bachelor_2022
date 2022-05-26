import gspread
import config
from helpers_dir.gspread_format_helper import yellow_color, get_color_with_alpha

from gspread_formatting import *
import models
from loguru import logger


async def colnum_string(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


async def excel_column_number(name):
    """Excel-style column name to number, e.g., A = 1, Z = 26, AA = 27, AAA = 703."""
    n = 0
    for c in name:
        n = n * 26 + 1 + ord(c) - ord('A')
    return n


async def split_ranges(table_range):
    r1, r2 = table_range.split(':')[0], table_range.split(':')[1]
    r1_int = ''.join([i for i in r1 if i.isdigit()])
    r2_int = ''.join([i for i in r2 if i.isdigit()])
    r1_int = int(r1_int)
    r2_int = int(r2_int)
    r1_str = ''.join([i for i in r1 if not i.isdigit()])
    # r2_str = ''.join([i for i in r2 if not i.isdigit()])
    ranges = [i for i in range(r1_int, r2_int + 1)]
    ranges = [r1_str + str(i) for i in ranges]
    return ranges


async def create_wks(restaurant_number, wks_name):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    count_wks = len(sheet.worksheets())
    wks = sheet.worksheet('Шаблон')
    wks_dup = wks.duplicate(insert_sheet_index=count_wks, new_sheet_name=wks_name)
    logger.info(f'Created wks - {wks_name}')
    return wks_dup


async def create_wks_joint(restaurant_number, wks_name, joint_name=False):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    count_wks = len(sheet.worksheets())
    wks_joint = sheet.worksheet('Шаблон (Общие)')
    if not joint_name:
        wks_joint_dup = wks_joint.duplicate(insert_sheet_index=count_wks, new_sheet_name=wks_name + ' (Общие)')
        logger.info(f'Created wks - {wks_name} (Общие)')
    else:
        wks_joint_dup = wks_joint.duplicate(insert_sheet_index=count_wks, new_sheet_name=wks_name)
        logger.info(f'Created wks - {wks_name}')
    return wks_joint_dup


async def check_table_joint(restaurant_number, table_name):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    wks = sheet.worksheet('Шаблон (Общие)')
    if table_name in wks.get_all_values()[0][1:]:
        return True
    return False


# Апдейтер столиков
async def get_tables(restaurant_number):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    wks = sheet.worksheet('Шаблон')
    wks_joint = sheet.worksheet('Шаблон (Общие)')
    all_values = wks.get_all_values()
    all_values_joint = wks_joint.get_all_values()
    tables = all_values[0][1:]
    tables_joint = all_values_joint[0][1:]
    # tables_joint = set(tables_joint)
    tables_res = []
    for j, i in enumerate(tables):
        table_name_full = ' '.join([i.split(' ')[0], i.split(' ')[1]])
        joint = table_name_full in tables_joint
        table_name = i.split(' ')[1]
        chairs = int(i.split(' ')[2][1:-1])
        colnum = await colnum_string(j + 2)
        colnum_joint = None
        if joint:
            first_index = tables_joint.index(table_name_full) + 2
            last_index = len(tables_joint) - 1 - tables_joint[::-1].index(table_name_full) + 2
            colnum_joint = await colnum_string(first_index) + '-' + await colnum_string(last_index)
        tables_res.append([table_name, chairs, joint, colnum, colnum_joint])
    return tables_res


async def get_available_tables(restaurant_number, how_many, date, exact_time):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    worksheets = sheet.worksheets()
    wks, wks_joint = None, None
    for i in worksheets:
        if i.title == date:
            wks = i
        elif i.title == f'{date} (Общие)':
            wks_joint = i
    if not wks:
        wks = await create_wks(restaurant_number, date)
    if not wks_joint:
        wks_joint = await create_wks_joint(restaurant_number, date)

    all_values = wks.get_all_values()
    all_values_joint = wks_joint.get_all_values()
    tables = all_values[0][1:]
    tables_joint = all_values_joint[0][1:]
    fit_tables = [i for i, j in enumerate(tables) if int(j.split(' ')[2][1:-1]) >= how_many and ' '.join(
        [j.split(' ')[0], j.split(' ')[1]]) not in tables_joint]
    ind = config.etalon_times_dict[exact_time] + 2
    tables_timies = []
    lower = ind - config.AVERAGE_TIME_VISIT
    upper = ind + config.AVERAGE_TIME_VISIT
    if lower < 0:
        lower = 1
    if upper > len(all_values):
        upper = len(all_values)
    for i in fit_tables:
        if all_values[ind][i] == '':
            lower_times = all_values[lower:ind]
            upper_times = all_values[ind:upper]
            if (len(upper_times) == 0 or all([j[i] == '' for j in upper_times])):
                tables_timies.append(i)

    logger.info(f'Available tables - {tables_timies}')
    return tables_timies


async def create_order_without_table(restaurant_number, how_many, date, time, name, phone, order_id=None):
    tables = await models.get_available_tables_with_people(restaurant_number, how_many, date, time)
    return await create_order(restaurant_number, how_many, date, time, tables[0], name, phone, order_id)


async def create_order(restaurant_number, how_many, date, time, table, name, phone, order_id=None):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    worksheets = sheet.worksheets()
    wks, wks_joint = None, None
    for i in worksheets:
        if i.title == date:
            wks = i
        elif i.title == f'{date} (Общие)':
            wks_joint = i
    if not wks:
        wks = await create_wks(restaurant_number, date)
    if not wks_joint:
        wks_joint = await create_wks_joint(restaurant_number, date)

    all_values = wks.get_all_values()
    all_values_joint = wks_joint.get_all_values()
    tables_joint = all_values_joint[0][1:]
    if table[1] in [int(i.split()[1]) for i in tables_joint]:
        first_index = tables_joint.index(f'Столик {table[1]}') + 1
        last_index = len(tables_joint) - 1 - tables_joint[::-1].index(f'Столик {table[1]}') + 1
        line_time = config.etalon_times_dict[time]
        ind_free_first = first_index + all_values_joint[line_time + 1][first_index:last_index].index('')
        ind_free_last = ind_free_first + how_many - 1
        s_f = await colnum_string(ind_free_first + 1)
        s_l = await colnum_string(ind_free_last + 1)
        column_range = s_f + str(config.etalon_times_dict[time] + 2) + ':' + s_l + str(
            config.etalon_times_dict[time] + config.AVERAGE_TIME_VISIT + 1)
        filling = [[name] * how_many, [phone] * how_many]
        for i in range(config.AVERAGE_TIME_VISIT - 3):
            filling.append([' '] * how_many)
        filling.append(['ID ' + str(order_id)] * how_many)
        wks_joint.update(column_range,
                         filling)
        logger.info(f'Create order - {column_range}')
        fmt1 = CellFormat(backgroundColor=yellow_color, borders=Borders(bottom=Border('NONE'), top=Border('SOLID'),
                                                                        right=Border('SOLID'),
                                                                        left=Border('SOLID')))
        fmt2 = CellFormat(backgroundColor=yellow_color,
                          borders=Borders(bottom=Border('NONE'), top=Border('NONE'), right=Border('SOLID'),
                                          left=Border('SOLID')))
        fmt3 = CellFormat(backgroundColor=yellow_color, borders=Borders(bottom=Border('SOLID'), top=Border('NONE'),
                                                                        right=Border('SOLID'),
                                                                        left=Border('SOLID')))

        fmt_left_upper = CellFormat(backgroundColor=yellow_color,
                                    borders=Borders(bottom=Border('NONE'),
                                                    top=Border('SOLID'),
                                                    right=Border('NONE'),
                                                    left=Border('SOLID')))
        fmt_right_upper = CellFormat(backgroundColor=yellow_color,
                                     borders=Borders(bottom=Border('NONE'),
                                                     top=Border('SOLID'),
                                                     right=Border('SOLID'),
                                                     left=Border('NONE')))

        fmt_left_lower = CellFormat(backgroundColor=yellow_color,
                                    borders=Borders(bottom=Border('SOLID'),
                                                    top=Border('NONE'),
                                                    right=Border('NONE'),
                                                    left=Border('SOLID')))

        fmt_right_lower = CellFormat(backgroundColor=yellow_color,
                                     borders=Borders(bottom=Border('SOLID'),
                                                     top=Border('NONE'),
                                                     right=Border('SOLID'),
                                                     left=Border('NONE')))

        fmt_left = CellFormat(backgroundColor=yellow_color,
                              borders=Borders(bottom=Border('NONE'),
                                              top=Border('NONE'),
                                              right=Border('NONE'),
                                              left=Border('SOLID')))

        fmt_right = CellFormat(backgroundColor=yellow_color,
                               borders=Borders(bottom=Border('NONE'),
                                               top=Border('NONE'),
                                               right=Border('SOLID'),
                                               left=Border('NONE')))

        fmt_middle = CellFormat(backgroundColor=yellow_color,
                                borders=Borders(bottom=Border('NONE'),
                                                top=Border('NONE'),
                                                right=Border('NONE'),
                                                left=Border('NONE')))

        fmt_upper = CellFormat(backgroundColor=yellow_color,
                               borders=Borders(bottom=Border('NONE'),
                                               top=Border('SOLID'),
                                               right=Border('NONE'),
                                               left=Border('NONE')))

        fmt_lower = CellFormat(backgroundColor=yellow_color,
                               borders=Borders(bottom=Border('SOLID'),
                                               top=Border('NONE'),
                                               right=Border('NONE'),
                                               left=Border('NONE')))
        if how_many == 1:

            ranges = await split_ranges(column_range)
            formatted_ranges = []
            for i in range(len(ranges)):
                if i == 0:
                    formatted_ranges.append([ranges[i], fmt1])
                elif i == len(ranges) - 1:
                    formatted_ranges.append([ranges[i], fmt3])
                else:
                    formatted_ranges.append([ranges[i], fmt2])
        else:
            formatted_ranges = []
            for i in range(config.etalon_times_dict[time] + 2,
                           config.etalon_times_dict[time] + 2 + config.AVERAGE_TIME_VISIT):
                for j in range(ind_free_first + 1, ind_free_last + 2):
                    if i == config.etalon_times_dict[time] + 2 and j == ind_free_first + 1:
                        fmt = fmt_left_upper
                    elif i == config.etalon_times_dict[time] + 2 and j == ind_free_last + 1:
                        fmt = fmt_right_upper
                    elif i == config.etalon_times_dict[
                        time] + 1 + config.AVERAGE_TIME_VISIT and j == ind_free_first + 1:
                        fmt = fmt_left_lower
                    elif i == config.etalon_times_dict[
                        time] + 1 + config.AVERAGE_TIME_VISIT and j == ind_free_last + 1:
                        fmt = fmt_right_lower
                    elif i == config.etalon_times_dict[time] + 2:
                        fmt = fmt_upper
                    elif i == config.etalon_times_dict[
                        time] + 1 + config.AVERAGE_TIME_VISIT:
                        fmt = fmt_lower
                    elif j == ind_free_first + 1:
                        fmt = fmt_left
                    elif j == ind_free_last + 1:
                        fmt = fmt_right
                    else:
                        fmt = fmt_middle
                    formatted_ranges.append([await colnum_string(j) + str(i), fmt])

        format_cell_ranges(wks_joint, formatted_ranges)
        table_obj = await models.Table.get(id=table[0])
        s = table_obj.colnum
        column_range2 = s + str(config.etalon_times_dict[time] + 2) + ':' + s + str(
            config.etalon_times_dict[time] + config.AVERAGE_TIME_VISIT + 1)
        values_now = [all_values[i][await excel_column_number(table_obj.colnum)] for i in
                      range(config.etalon_times_dict[time] + 1,
                            config.etalon_times_dict[
                                time] + config.AVERAGE_TIME_VISIT + 1)]
        for i in range(len(values_now)):
            if values_now[i].isdigit():
                values_now[i] = int(values_now[i]) + how_many
            else:
                values_now[i] = how_many
        values_now = [[i] for i in values_now]
        wks.update(column_range2,
                   values_now)
        fmt4 = CellFormat(backgroundColor=yellow_color,
                          borders=Borders(bottom=Border('SOLID'), top=Border('SOLID'), right=Border('SOLID'),
                                          left=Border('SOLID')))
        ranges = await split_ranges(column_range2)
        formatted_ranges = []
        max_how_many = int(all_values[0][await excel_column_number(table_obj.colnum)].split()[2][1:-1])
        for i in range(len(ranges)):
            fmt_ = CellFormat(backgroundColor=await get_color_with_alpha(values_now[i][0], max_how_many),
                              borders=Borders(bottom=Border('SOLID'), top=Border('SOLID'), right=Border('SOLID'),
                                              left=Border('SOLID')))

            formatted_ranges.append([ranges[i], fmt_])
        format_cell_ranges(wks, formatted_ranges)
        return column_range2, column_range, table
    else:
        table_obj = await models.Table.get(id=table[0])
        s = table_obj.colnum
        column_range = s + str(config.etalon_times_dict[time] + 2) + ':' + s + str(
            config.etalon_times_dict[time] + config.AVERAGE_TIME_VISIT + 1)
        filling = [[name], [phone]]
        for i in range(config.AVERAGE_TIME_VISIT - 3):
            filling.append([' '])
        filling.append(['ID ' + str(order_id)])
        wks.update(column_range,
                   filling)
        logger.info(f'Create order - {column_range}')
        fmt1 = CellFormat(backgroundColor=yellow_color, borders=Borders(bottom=Border('NONE'), top=Border('SOLID'),
                                                                        right=Border('SOLID'),
                                                                        left=Border('SOLID')))
        fmt2 = CellFormat(backgroundColor=yellow_color,
                          borders=Borders(bottom=Border('NONE'), top=Border('NONE'), right=Border('SOLID'),
                                          left=Border('SOLID')))
        fmt3 = CellFormat(backgroundColor=yellow_color, borders=Borders(bottom=Border('SOLID'), top=Border('NONE'),
                                                                        right=Border('SOLID'),
                                                                        left=Border('SOLID')))

        ranges = await split_ranges(column_range)
        formatted_ranges = []
        for i in range(len(ranges)):
            if i == 0:
                formatted_ranges.append([ranges[i], fmt1])
            elif i == len(ranges) - 1:
                formatted_ranges.append([ranges[i], fmt3])
            else:
                formatted_ranges.append([ranges[i], fmt2])

        format_cell_ranges(wks, formatted_ranges)
        return column_range, None, table


async def delete_order(restaurant_number, date, table_range, table_joint_range, order=None):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    worksheets = sheet.worksheets()
    wks, wks_joint = None, None
    for i in worksheets:
        if i.title == date:
            wks = i
        elif i.title == f'{date} (Общие)':
            wks_joint = i
    if not wks or not wks_joint:
        return None
    if not table_joint_range:
        wks.update(table_range, [['']] * config.AVERAGE_TIME_VISIT)
        fmt = CellFormat(backgroundColor=Color(1, 1, 1),
                         borders=Borders(bottom=Border('SOLID', Color(0.85, 0.85, 0.85)),
                                         top=Border('SOLID', Color(0.85, 0.85, 0.85)),
                                         right=Border('SOLID', Color(0.85, 0.85, 0.85)),
                                         left=Border('SOLID', Color(0.85, 0.85, 0.85))))
        logger.info(f'Delete order - {table_range}')
        format_cell_range(wks, table_range, fmt)
        return True
    else:
        wks_joint.update(table_joint_range, [[''] * order.how_many] * config.AVERAGE_TIME_VISIT)

        fmt = CellFormat(backgroundColor=Color(1, 1, 1),
                         borders=Borders(bottom=Border('SOLID', Color(0.85, 0.85, 0.85)),
                                         top=Border('SOLID', Color(0.85, 0.85, 0.85)),
                                         right=Border('SOLID', Color(0.85, 0.85, 0.85)),
                                         left=Border('SOLID', Color(0.85, 0.85, 0.85))))
        logger.info(f'Delete order - {table_range} {table_joint_range}')
        format_cell_range(wks_joint, table_joint_range, fmt)

        values = wks.get(table_range)
        for i in range(len(values)):
            values[i][0] = int(values[i][0]) - order.how_many
            values[i][0] = '' if values[i][0] == 0 else str(values[i][0])
        wks.update(table_range, values)
        ranges = await split_ranges(table_range)
        formatted_ranges = []
        a = ''.join([k for k in table_range.split(':')[0] if not k.isdigit()])
        max_how_many = int(wks.get(a + '1')[0][0].split()[2][1:-1])

        for i in range(len(ranges)):
            fmt_ = CellFormat(backgroundColor=await get_color_with_alpha(values[i][0], max_how_many),
                              borders=Borders(bottom=Border('SOLID'), top=Border('SOLID'), right=Border('SOLID'),
                                              left=Border('SOLID')))

            formatted_ranges.append([ranges[i], fmt_])
        format_cell_ranges(wks, formatted_ranges)

        return True


async def test(restaurant_number, date, table_range):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    worksheets = sheet.worksheets()
    wks, wks_joint = None, None
    for i in worksheets:
        if i.title == date:
            wks = i
        elif i.title == f'{date} (Общие)':
            wks_joint = i
    if not wks or not wks_joint:
        return None
    values = wks.get(table_range)
    print(values)


async def confirm_order_table(restaurant_number, date, table_range):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    worksheets = sheet.worksheets()
    wks = None
    for i in worksheets:
        if i.title == date:
            wks = i
    if not wks:
        return None
    green_color = Color(0.65, 0.81, 0.59)
    fmt1 = CellFormat(backgroundColor=green_color, borders=Borders(bottom=Border('NONE'), top=Border('SOLID'),
                                                                   right=Border('SOLID'),
                                                                   left=Border('SOLID')))
    fmt2 = CellFormat(backgroundColor=green_color,
                      borders=Borders(bottom=Border('NONE'), top=Border('NONE'), right=Border('SOLID'),
                                      left=Border('SOLID')))
    fmt3 = CellFormat(backgroundColor=green_color, borders=Borders(bottom=Border('SOLID'), top=Border('NONE'),
                                                                   right=Border('SOLID'),
                                                                   left=Border('SOLID')))

    ranges = await split_ranges(table_range)
    formatted_ranges = []
    for i in range(len(ranges)):
        if i == 0:
            formatted_ranges.append([ranges[i], fmt1])
        elif i == len(ranges) - 1:
            formatted_ranges.append([ranges[i], fmt3])
        else:
            formatted_ranges.append([ranges[i], fmt2])

    format_cell_ranges(wks, formatted_ranges)
    logger.info(f'Confirm order - {table_range}')
    return True


async def to_archive(restaurant_number, date):
    gc = gspread.service_account(config.CREDENTIALS_SHEETS)
    sheet = gc.open_by_url(config.TABLES_DICT[restaurant_number])
    worksheets = sheet.worksheets()
    wks, wks_joint = None, None
    for i in worksheets:
        if i.title == date:
            wks = i
        elif i.title == f'{date} (Общие)':
            wks_joint = i
    if not wks:
        wks = await create_wks(restaurant_number, date)
    if not wks_joint:
        wks_joint = await create_wks_joint(restaurant_number, date)

    wks.copy_to(config.ARCHIVE_DICT[restaurant_number])
    wks_joint.copy_to(config.ARCHIVE_DICT[restaurant_number])
    sheet.del_worksheet(wks)
    sheet.del_worksheet(wks_joint)
    logger.info(f'To archive - {restaurant_number}, {date}')
