import asyncio
import os
import dotenv
import pytz
import ast

from gspread_formatting import Color

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)

LOG_FILE = os.environ.get('LOG_FILE')
BOT_TOKEN = os.environ.get('BOT_TOKEN')

restaurant_name = 'Civil'

DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')

CREDENTIALS_SHEETS = os.environ.get('CREDENTIALS_SHEETS')
TABLE_1 = os.environ.get('TABLE_1')
TABLE_2 = os.environ.get('TABLE_2')
TABLE_3 = os.environ.get('TABLE_3')
TABLE_FOLDER = os.environ.get('TABLE_FOLDER')

TABLE_1_ARCHIVE = os.environ.get('TABLE_1_ARCHIVE')
TABLE_2_ARCHIVE = os.environ.get('TABLE_2_ARCHIVE')
TABLE_3_ARCHIVE = os.environ.get('TABLE_3_ARCHIVE')

TABLES_DICT = {1: TABLE_1, 2: TABLE_2, 3: TABLE_3}

ARCHIVE_DICT = {1: TABLE_1_ARCHIVE, 2: TABLE_2_ARCHIVE, 3: TABLE_3_ARCHIVE}

TORTOISE_ORM = {
    'connections': {
        'default': {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": DB_HOST,
                "port": DB_PORT,
                "user": DB_USER,
                "password": DB_PASSWORD,
                "database": DB_NAME,
            }
        }
    },
    "apps": {"models": {"models": ["models", "aerich.models"], "default_connection": "default"}}
}

timezone = pytz.timezone('Europe/Moscow')

#Среднее время визита. Равняется 15 минут * AVERAGE_TIME_VISIT. Например, 8*15 = 2 часа
AVERAGE_TIME_VISIT = int(os.environ.get('AVERAGE_TIME_VISIT'))

#За какое время можно бронировать. Равняется 15 минут * BOOK_IN_ADVANCE. Например, 4*15 = 1 час
BOOK_IN_ADVANCE = int(os.environ.get('BOOK_IN_ADVANCE'))

DAYS_FOR_BOOKING = int(os.environ.get('DAYS_FOR_BOOKING'))

etalon_times = ['09:00', '09:15', '09:30', '09:45', '10:00', '10:15', '10:30', '10:45', '11:00', '11:15', '11:30',
                '11:45', '12:00', '12:15', '12:30', '12:45', '13:00', '13:15', '13:30', '13:45', '14:00', '14:15',
                '14:30', '14:45', '15:00', '15:15', '15:30', '15:45', '16:00', '16:15', '16:30', '16:45', '17:00',
                '17:15', '17:30', '17:45', '18:00', '18:15', '18:30', '18:45', '19:00', '19:15', '19:30', '19:45',
                '20:00', '20:15', '20:30', '20:45', '21:00', '21:15', '21:30', '21:45', '22:00', '22:15', '22:30',
                '22:45', '23:00']

etalon_times_dict = {'09:00': 0, '09:15': 1, '09:30': 2, '09:45': 3, '10:00': 4, '10:15': 5, '10:30': 6, '10:45': 7,
                     '11:00': 8, '11:15': 9, '11:30': 10, '11:45': 11, '12:00': 12, '12:15': 13, '12:30': 14,
                     '12:45': 15, '13:00': 16, '13:15': 17, '13:30': 18, '13:45': 19, '14:00': 20, '14:15': 21,
                     '14:30': 22, '14:45': 23, '15:00': 24, '15:15': 25, '15:30': 26, '15:45': 27, '16:00': 28,
                     '16:15': 29, '16:30': 30, '16:45': 31, '17:00': 32, '17:15': 33, '17:30': 34, '17:45': 35,
                     '18:00': 36, '18:15': 37, '18:30': 38, '18:45': 39, '19:00': 40, '19:15': 41, '19:30': 42,
                     '19:45': 43, '20:00': 44, '20:15': 45, '20:30': 46, '20:45': 47, '21:00': 48, '21:15': 49,
                     '21:30': 50, '21:45': 51, '22:00': 52, '22:15': 53, '22:30': 54, '22:45': 55, '23:00': 56}
#
# TEMPLATE_IMAGE_1 = os.environ.get('TEMPLATE_IMAGE_1')
#
# TEMPLATE_IMAGE_2 = os.environ.get('TEMPLATE_IMAGE_2')

PATH_TO_SAVE = os.environ.get('PATH_TO_SAVE')
#
# table_cords_1 = {1: ['rectangle', (83, 428), (152, 570), 0.2],
#                  2: ['rectangle', (83, 570), (152, 717), 0.2],
#                  3: ['rectangle', (206, 187), (320, 306), 0],
#                  4: ['rectangle', (360, 187), (475, 306), 0],
#                  5: ['rectangle', (507, 187), (620, 306), 0],
#                  6: ['rectangle', (653, 187), (768, 306), 0],
#                  7: ['rectangle', (807, 187), (920, 306), 0],
#                  8: ['rectangle', (993, 187), (1243, 306), 0.4],
#                  9: ['rectangle', (1302, 187), (1553, 306), 0.4],
#                  10: ['rectangle', (508, 615), (620, 735), 0],
#                  11: ['rectangle', (654, 615), (767, 735), 0],
#                  12: ['rectangle', (809, 615), (921, 735), 0],
#                  13: ['rectangle', (1075, 615), (1300, 735), 0.4],
#                  14: ['rectangle', (1375, 615), (1600, 735), 0.4],
#                  25: ['rectangle', (290, 500), (440, 790), 0.2]}
#
# table_cords_2 = {15: ['rectangle', (367, 252), (472, 565), 0.1],
#                  16: ['rectangle', (647, 192), (757, 308), 0],
#                  17: ['rectangle', (902, 192), (1012, 308), 0],
#                  18: ['rectangle', (617, 569), (857, 682), 0.4],
#                  19: ['rectangle', (902, 569), (1146, 682), 0.4],
#                  20: ['rectangle', (1177, 569), (1419, 682), 0.4],
#                  21: ['rectangle', (1260, 220), (1369, 336), 0],
#                  22: ['rectangle', (1260, 362), (1369, 475), 0]}

admins = ['',
          78640232,
          988365161,
          151497226
          ]

BOT_TOKEN_ADMIN = os.environ.get('BOT_TOKEN_ADMIN')

broadcaster_queue = asyncio.Queue()

BOT_NAME = os.environ.get('BOT_NAME')

HISTORY_CHANNEL = os.environ.get('HISTORY_CHANNEL')

DELETE_NOT_CONFIRMED = False

PHONES = ast.literal_eval(os.environ.get('PHONES'))

PASSWORD_1 = os.environ.get('PASSWORD_1')

PASSWORD_2 = os.environ.get('PASSWORD_2')

PASSWORD_3 = os.environ.get('PASSWORD_3')

RESTAURANT_PASSWORDS = {1: PASSWORD_1,
                        2: PASSWORD_2,
                        3: PASSWORD_3}

# Формат - {Столик: [id фона, id цифры, id рамки, [id стула, id стула]}
volynskyi_first_floor = {1: ['path30', 'path32', 'path34', ['path28', 'path36', 'path38']],
                         3: ['path42', 'path44', 'path46', ['path40', 'path48', 'path50']],
                         5: ['path10', 'path12', 'path14', ['path6', 'path8']],
                         6: ['path20', 'path22', 'path24', ['path16', 'path18']],
                         7: ['path114', 'path116', 'path118',
                             ['path106', 'path102', 'path110', 'path112', 'path104', 'path108']],
                         8: ['path80', 'path82', 'path84', ['path76', 'path78', 'path86', 'path88']],
                         10: ['path92', 'path94', 'path96', ['path90', 'path98']],
                         11: ['path56', 'path58', 'path60', ['path54', 'path62']],
                         122: ['path66', 'path68', 'path70', ['path64', 'path72']],
                         12: ['path128', 'path130', 'path132', ['path126', 'path124', 'path122']]
                         }

volynskyi_second_floor_1 = {18: ['rect64', 'path66', 'rect68', ['path70', 'path72']],
                            19: ['path24', 'path26', 'path28', ['path22', 'path30']],
                            20: ['path34', 'path36', 'path38', ['path32', 'path40']],
                            21: ['path44', 'path46', 'path48', ['path42', 'path50']],
                            22: ['path54', 'path56', 'path58', ['path52', 'path60']],
                            23: ['path178', 'path180', 'path182', ['path176']],
                            24: ['path186', 'path188', 'path190', ['path184']],
                            25: ['path194', 'path196', 'path198', ['path192']],
                            26: ['path122', 'path124', 'path126', ['path120', 'path128']],
                            27: ['path134', 'path136', 'path138', ['path130', 'path132', 'path140']],
                            29: ['path144', 'path146', 'path148', ['path142', 'path150']],
                            30: ['path156', 'path158', 'path160', ['path152', 'path154', 'path162']],
                            32: ['path166', 'path168', 'path170', ['path164', 'path172']],
                            33: ['path88', 'path90', 'path92',
                                 ['path76', 'path78', 'path80', 'path82', 'path84', 'path86']],
                            34: ['path104', 'path106', 'path108',
                                 ['path96', 'path98', 'path100', 'path102', 'path110', 'path112', 'path114',
                                  'path116']]}

volynskyi_second_floor_2 = {38: ['path8', 'path10', 'path12', ['path6', 'path14', 'path16']],
                            40: ['path38', 'path40', 'path42', ['path36', 'path44']],
                            41: ['path48', 'path50', 'path52', ['path46', 'path54']],
                            42: ['path58', 'path60', 'path62', ['path56', 'path64']],
                            43: ['path68', 'path70', 'path72', ['path66', 'path74']],
                            44: ['path80', 'path82', 'path84', ['path78', 'path86']],
                            46: ['path26', 'path28', 'path30', ['path20', 'path22', 'path24', 'path32']]}

bolshoy_prospekt = {1: ['path182', 'path184', 'path186', ['path180', 'path178', 'path190', 'path188']],
                    2: ['path54', 'path56', 'path58', ['path52', 'path60', 'path62']],
                    3: ['path42', 'path44', 'path46', ['path40', 'path50', 'path48']],
                    4: ['path30', 'path32', 'path34', ['path28', 'path38', 'path36']],
                    5: ['path94', 'path96', 'path98', ['path92', 'path100']],
                    6: ['path104', 'path106', 'path108', ['path102', 'path110']],
                    7: ['path116', 'path118', 'path120', ['path114', 'path122']],
                    8: ['path126', 'path128', 'path130', ['path124', 'path132']],
                    9: ['path136', 'path138', 'path140', ['path134', 'path142']],
                    10: ['path14', 'path16', 'path18', ['path12', 'path10', 'path8', 'path24', 'path22', 'path20']],
                    11: ['path148', 'path150', 'path152', ['path146', 'path154']],
                    12: ['path158', 'path160', 'path162', ['path156', 'path164']],
                    13: ['path168', 'path170', 'path172', ['path166', 'path174']],
                    14: ['path82', 'path84', 'path86', ['path80', 'path78', 'path88']],
                    15: ['path68', 'path70', 'path72', ['path66', 'path76', 'path74']]}

sovetskaya_1 = {1: ['path92', 'path94', 'path96', ['path98', 'path100']],
                3: ['path10', 'path12', 'path14', ['path8', 'path16']],
                4: ['path20', 'path22', 'path24', ['path18', 'path26']],
                5: ['path30', 'path32', 'path34', ['path28', 'path36']],
                6: ['path40', 'path42', 'path44', ['path38', 'path46']],
                7: ['path50', 'path52', 'path54', ['path48', 'path56']],
                8: ['path108', 'path110', 'path112', ['path104', 'path106', 'path114', 'path116']],
                9: ['path122', 'path124', 'path126', ['path118', 'path120', 'path128', 'path130']],
                10: ['path62', 'path64', 'path66', ['path60', 'path68']],
                11: ['path72', 'path74', 'path76', ['path70', 'path78']],
                12: ['path82', 'path84', 'path86', ['path80', 'path88']],
                13: ['path140', 'path142', 'path144',
                     ['path134', 'path136', 'path138', 'path146', 'path148', 'path150']],
                14: ['path158', 'path160', 'path162',
                     ['path152', 'path154', 'path156', 'path164', 'path166', 'path168']]}

sovetskaya_2 = {15: ['path96', 'path98', 'path100',
                     ['path94', 'path92', 'path90', 'path88', 'path102', 'path104', 'path106', 'path108']],
                16: ['path10', 'path12', 'path14', ['path8', 'path16']],
                17: ['path20', 'path22', 'path24', ['path18', 'path26']],
                18: ['path44', 'path46', 'path48', ['path40', 'path42', 'path50']],
                19: ['path56', 'path58', 'path60', ['path52', 'path54', 'path62']],
                20: ['path68', 'path70', 'path72', ['path64', 'path66', 'path74']],
                21: ['path30', 'path32', 'path34', ['path28', 'path36']]}

['path', 'path', 'path', ['path']]

volynskyi_first_floor_svg = os.environ.get('volynskyi_first_floor_svg')
volynskyi_second_floor_1_svg = os.environ.get('volynskyi_second_floor_1_svg')
volynskyi_second_floor_2_svg = os.environ.get('volynskyi_second_floor_2_svg')

bolshoy_prospekt_svg = os.environ.get('bolshoy_prospekt_svg')

sovetskaya_1_svg = os.environ.get('sovetskaya_1_svg')

sovetskaya_2_svg = os.environ.get('sovetskaya_2_svg')

TEMPLATES_RESTAURANTS_SVG_IDS = {1: [[sovetskaya_1_svg, sovetskaya_1], [sovetskaya_2_svg, sovetskaya_2]],
                                 2: [[bolshoy_prospekt_svg, bolshoy_prospekt]],
                                 3: [[volynskyi_first_floor_svg, volynskyi_first_floor],
                                     [volynskyi_second_floor_1_svg, volynskyi_second_floor_1],
                                     [volynskyi_second_floor_2_svg, volynskyi_second_floor_2]]}