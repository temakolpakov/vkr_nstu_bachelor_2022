import time

import cv2
import os
# from config import TEMPLATE_IMAGE_1, TEMPLATE_IMAGE_2, PATH_TO_SAVE
import config
# from config import table_cords_1, table_cords_2
import lxml.etree as ET
import cairosvg
from models import FileIDs

color_free = '#0015ce'
fill_opacity = '0.1'
fill_opacity_chair = '0.15'
stroke_free_chair = '#0015ce'

color_busy = '#DEE0ED'
color_busy_number = '#A7A5CA'
color_busy_border = '#B6B5D3'
stroke_busy_chair = '#B6B5D3'
color_busy_chair = '#DEE0ED'


def rounded_rectangle(src, top_left, bottom_right, radius=1, color=255, thickness=1, line_type=cv2.LINE_AA):

    #  corners:
    #  p1 - p2
    #  |     |
    #  p4 - p3

    p1 = top_left
    p2 = (bottom_right[1], top_left[1])
    p3 = (bottom_right[1], bottom_right[0])
    p4 = (top_left[0], bottom_right[0])

    height = abs(bottom_right[0] - top_left[1])

    if radius > 1:
        radius = 1

    corner_radius = int(radius * (height/2))

    if thickness < 0:

        #big rect
        top_left_main_rect = (int(p1[0] + corner_radius), int(p1[1]))
        bottom_right_main_rect = (int(p3[0] - corner_radius), int(p3[1]))

        top_left_rect_left = (p1[0], p1[1] + corner_radius)
        bottom_right_rect_left = (p4[0] + corner_radius, p4[1] - corner_radius)

        top_left_rect_right = (p2[0] - corner_radius, p2[1] + corner_radius)
        bottom_right_rect_right = (p3[0], p3[1] - corner_radius)

        all_rects = [
        [top_left_main_rect, bottom_right_main_rect],
        [top_left_rect_left, bottom_right_rect_left],
        [top_left_rect_right, bottom_right_rect_right]]

        [cv2.rectangle(src, rect[0], rect[1], color, thickness) for rect in all_rects]

    # draw straight lines
    cv2.line(src, (p1[0] + corner_radius, p1[1]), (p2[0] - corner_radius, p2[1]), color, abs(thickness), line_type)
    cv2.line(src, (p2[0], p2[1] + corner_radius), (p3[0], p3[1] - corner_radius), color, abs(thickness), line_type)
    cv2.line(src, (p3[0] - corner_radius, p4[1]), (p4[0] + corner_radius, p3[1]), color, abs(thickness), line_type)
    cv2.line(src, (p4[0], p4[1] - corner_radius), (p1[0], p1[1] + corner_radius), color, abs(thickness), line_type)

    # draw arcs
    cv2.ellipse(src, (p1[0] + corner_radius, p1[1] + corner_radius), (corner_radius, corner_radius), 180.0, 0, 90, color ,thickness, line_type)
    cv2.ellipse(src, (p2[0] - corner_radius, p2[1] + corner_radius), (corner_radius, corner_radius), 270.0, 0, 90, color , thickness, line_type)
    cv2.ellipse(src, (p3[0] - corner_radius, p3[1] - corner_radius), (corner_radius, corner_radius), 0.0, 0, 90,   color , thickness, line_type)
    cv2.ellipse(src, (p4[0] + corner_radius, p4[1] - corner_radius), (corner_radius, corner_radius), 90.0, 0, 90,  color , thickness, line_type)

    return src

#
# def get_colored_image(templates, path_to_save, tables):
#     tables1 = sorted([i for i in tables if i in table_cords_1.keys()])
#     tables2 = sorted([i for i in tables if i in table_cords_2.keys()])
#     if len(tables1) == 0:
#         name1 = 'none1'
#     else:
#         name1 = '_'.join(str(i) for i in tables1)
#     if len(tables2) == 0:
#         name2 = 'none2'
#     else:
#         name2 = '_'.join(str(i) for i in tables2)
#     path_1 = path_to_save + name1 +'.png'
#     path_2 = path_to_save + name2+'.png'
#
#     if os.path.isfile(path_1) and os.path.isfile(path_2):
#         return path_1, path_2
#
#     im = cv2.imread(templates[0])
#     im2 = cv2.imread(templates[1])
#
#     overlay = im.copy()
#     overlay2 = im2.copy()
#
#     green = (182, 226, 188, 10)
#     alpha = 0.4
#
#     for i in tables:
#         if i in table_cords_1.keys():
#             t = 1
#             table_cords = table_cords_1
#             ov = overlay
#         else:
#             t = 2
#             table_cords = table_cords_2
#             ov = overlay2
#
#         if table_cords[i][0] == 'circle':
#             cv2.circle(ov, table_cords[i][1], 55, green, cv2.FILLED)
#         elif table_cords[i][0] == 'rectangle':
#             pass
#             if t == 1:
#                 overlay = rounded_rectangle(ov, table_cords[i][1], table_cords[i][2][::-1], color=green, radius=table_cords[i][3], thickness=cv2.FILLED)
#             else:
#                 overlay2 = rounded_rectangle(ov, table_cords[i][1], table_cords[i][2][::-1], color=green, radius=table_cords[i][3], thickness=cv2.FILLED)
#         elif table_cords[i][0] == 'ellipse':
#             cv2.ellipse(ov, table_cords[i][1], table_cords[i][2], 0, 0, 360, green, cv2.FILLED)
#     image_new = cv2.addWeighted(overlay, alpha, im, 1 - alpha, 0)
#     image_new2 = cv2.addWeighted(overlay2, alpha, im2, 1 - alpha, 0)
#
#     cv2.imwrite(path_1, image_new)
#     cv2.imwrite(path_2, image_new2)
#     return path_1, path_2


async def get_colored_image(restaurant_number, tables, path_to_save, admin=False):
    a = time.time()

    tables.sort()
    template_svg_ids = config.TEMPLATES_RESTAURANTS_SVG_IDS[restaurant_number]
    path_restaurant = str(restaurant_number)+'-'

    results = []

    c = 1
    for svg, ids in template_svg_ids:
        tables_busy = {i: ids[i] for i in ids if i not in tables}
        ids_busy_1 = [tables_busy[i][0] for i in tables_busy]
        ids_busy_2 = [tables_busy[i][1] for i in tables_busy]
        ids_busy_3 = [tables_busy[i][2] for i in tables_busy]
        ids_busy_4 = [tables_busy[i][3] for i in tables_busy]
        ids_busy_4 = sum(ids_busy_4, [])

        ids_free_1 = [ids[i][0] for i in ids if i in tables]
        ids_free_2 = [ids[i][1] for i in ids if i in tables]
        ids_free_3 = [ids[i][2] for i in ids if i in tables]
        ids_free_4 = [ids[i][3] for i in ids if i in tables]
        ids_free_4 = sum(ids_free_4, [])

        if len([i for i in ids.keys() if i in tables])==0:
            raw_path = path_restaurant + 'none' + str(c)
            path = path_to_save + path_restaurant + 'none' + str(c)
        else:
            raw_path = path_restaurant + '_'.join([str(i) for i in ids.keys() if i in tables])
            path = path_to_save + path_restaurant + '_'.join([str(i) for i in ids.keys() if i in tables])
        c += 1
        file_id = await FileIDs.get_or_none(path=raw_path)
        if file_id and not admin:
            results.append([file_id.file_id, raw_path, 'file_id'])
            continue
        path_png = path+'.png'
        if os.path.isfile(path_png):
            results.append([path_png, raw_path, 'path'])
            continue

        svg_parse = ET.parse(svg)
        g = svg_parse.findall('{http://www.w3.org/2000/svg}g')[0]
        for i in g.findall('{http://www.w3.org/2000/svg}path'):
            attributes = i.attrib
            id_attr = attributes.get('id')
            if id_attr in ids_free_1:
                i.attrib['fill'] = color_free
                i.attrib['fill-opacity'] = fill_opacity

            elif id_attr in ids_free_2:
                i.attrib['fill'] = color_free
            elif id_attr in ids_free_3:
                i.attrib['fill'] = color_free
            elif id_attr in ids_free_4:
                i.attrib['fill'] = color_free
                i.attrib['fill-opacity'] = fill_opacity_chair
                i.attrib['stroke'] = stroke_free_chair
            elif id_attr in ids_busy_1:
                try:
                    i.attrib.pop('fill-opacity')
                except:
                    pass
                i.attrib['fill'] = color_busy
            elif id_attr in ids_busy_2:
                i.attrib['fill'] = color_busy_number
            elif id_attr in ids_busy_3:
                i.attrib['fill'] = color_busy_border
            elif id_attr in ids_busy_4:
                try:
                    i.attrib.pop('fill-opacity')
                except:
                    pass
                i.attrib['fill'] = color_busy_chair
                i.attrib['stroke'] = stroke_busy_chair
        for i in g.findall('{http://www.w3.org/2000/svg}rect'):
            attributes = i.attrib
            id_attr = attributes.get('id')
            if id_attr in ids_free_1:
                i.attrib['fill'] = color_free
                i.attrib['fill-opacity'] = fill_opacity

            elif id_attr in ids_free_2:
                i.attrib['fill'] = color_free
            elif id_attr in ids_free_3:
                i.attrib['fill'] = color_free
                i.attrib['fill-opacity'] = fill_opacity
            elif id_attr in ids_free_4:
                i.attrib['fill'] = color_free
                i.attrib['fill-opacity'] = fill_opacity_chair
                i.attrib['stroke'] = stroke_free_chair
            elif id_attr in ids_busy_1:
                i.attrib['fill'] = color_busy_border
                i.attrib['fill-opacity'] = fill_opacity_chair
            elif id_attr in ids_busy_2:
                i.attrib['fill'] = color_busy_number
            elif id_attr in ids_busy_3:
                i.attrib['fill'] = color_busy
                i.attrib['stroke'] = stroke_busy_chair
                i.attrib['fill-opacity'] = fill_opacity
            elif id_attr in ids_busy_4:
                try:
                    i.attrib.pop('fill-opacity')
                except:
                    pass
                i.attrib['fill'] = color_busy_chair
                i.attrib['stroke'] = stroke_busy_chair
        new_file = open(path + '.svg', 'wb').write(
            ET.tostring(svg_parse))
        svg_code = open(path + '.svg', 'r').read()
        cairosvg.svg2png(svg_code, write_to=path_png)
        results.append([path_png, raw_path, 'path'])
    # print(time.time()-a)

    return results

def test(restaurant_number, tables):
    a = time.time()

    tables_busy = {i:config.addres3_first_floor[i] for i in config.addres3_first_floor if i not in tables}

    ids_free_1 = [config.addres3_first_floor[i][0] for i in config.addres3_first_floor if i in tables]
    ids_free_2 = [config.addres3_first_floor[i][1] for i in config.addres3_first_floor if i in tables]
    ids_free_3 = [config.addres3_first_floor[i][2] for i in config.addres3_first_floor if i in tables]
    ids_free_4 = [config.addres3_first_floor[i][3] for i in config.addres3_first_floor if i in tables]
    ids_free_4 = sum(ids_free_4, [])

    ids_busy_1 = [tables_busy[i][0] for i in tables_busy]
    ids_busy_2 = [tables_busy[i][1] for i in tables_busy]
    ids_busy_3 = [tables_busy[i][2] for i in tables_busy]
    ids_busy_4 = [tables_busy[i][3] for i in tables_busy]
    ids_busy_4 = sum(ids_busy_4, [])

    svg = ET.parse('/Users/artemkolpakov/PycharmProjects/4u-service_restaurants/templates/address3_second_floor_2.svg')
    g = svg.findall('{http://www.w3.org/2000/svg}g')[0]


    for i in g.findall('{http://www.w3.org/2000/svg}path'):
        attributes = i.attrib
        id_attr = attributes.get('id')
        if id_attr in ids_free_1:
            i.attrib['fill'] = color_free
            i.attrib['fill-opacity'] = fill_opacity
        elif id_attr in ids_free_2:
            i.attrib['fill'] = color_free
        elif id_attr in ids_free_3:
            i.attrib['fill'] = color_free
        elif id_attr in ids_free_4:
            i.attrib['fill'] = color_free
            i.attrib['fill-opacity'] = fill_opacity_chair
            i.attrib['stroke'] = stroke_free_chair
        elif id_attr in ids_busy_1:
            try:
                i.attrib.pop('fill-opacity')
            except:
                pass
            i.attrib['fill'] = color_busy
        elif id_attr in ids_busy_2:
            i.attrib['fill'] = color_busy_number
        elif id_attr in ids_busy_3:
            i.attrib['fill'] = color_busy_border
        elif id_attr in ids_busy_4:
            try:
                i.attrib.pop('fill-opacity')
            except:
                pass
            i.attrib['fill'] = color_busy_chair
            i.attrib['stroke'] = stroke_busy_chair

    new_file = open('/Users/artemkolpakov/PycharmProjects/4u-service_restaurants/test3.svg', 'wb').write(ET.tostring(svg))
    print(time.time()-a)

    # paths, attributes = svgpathtools.svg2paths('/Users/artemkolpakov/PycharmProjects/4u-service_restaurants/Frame 47_3.svg')
    # print(paths)
    # print(attributes)

    # svg_code = open('/Users/artemkolpakov/PycharmProjects/4u-service_restaurants/test2.svg', 'r').read()
    # cairosvg.svg2png(svg_code, write_to='/Users/artemkolpakov/PycharmProjects/4u-service_restaurants/test2.png')

# get_colored_image(3, [34], '/Users/artemkolpakov/PycharmProjects/4u-service_restaurants/img/')
# print(get_colored_image((TEMPLATE_IMAGE_1, TEMPLATE_IMAGE_2), PATH_TO_SAVE, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 25, 15, 16, 17, 18, 19, 20, 21, 22]))
