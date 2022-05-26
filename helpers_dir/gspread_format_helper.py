from gspread_formatting import Color

yellow_color = Color(0.98, 0.82, 0.32)

async def get_color_with_alpha(how_many, max_how_many):
    if how_many == '':
        how_many = 0
    if type(how_many) == str:
        how_many = int(how_many)
    yellow_color = Color(0.98, 0.82, 0.32)
    a = 1 - how_many/max_how_many
    red = yellow_color.red
    green = yellow_color.green + a - yellow_color.green*a
    blue = yellow_color.blue + a - yellow_color.blue*a
    new_color = Color(red, green, blue)

    return new_color
