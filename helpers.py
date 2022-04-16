import re

import phonenumbers

phone_regex = '^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'


async def safe_for_markdown(text):
    excluded = ['.', ':', '-', '~', '!', '+']
    flag = False
    l = len(text)
    text_new = ''
    for i in range(l):
        if text[i] in excluded and text[i - 1] != '\\':
            text_new += fr'\{text[i]}'
        elif text[i] == '(':
            if text[i - 1] != ']' and text[i - 1] != '\\':
                text_new += fr'\{text[i]}'
                flag = True
            else:
                text_new += text[i]
        elif text[i] == ')':
            if flag and text[i - 1] != '\\':
                text_new += fr'\{text[i]}'
                flag = False
            else:
                text_new += text[i]

        else:
            text_new += text[i]
    if '#' in text_new:
        text_new = text_new.replace('\\\\\\', '\\')

    return text_new


async def is_phone_valid(text):
    text = text.strip()
    try:
        phone = phonenumbers.parse(text)
        if phonenumbers.is_possible_number(phone) and phonenumbers.is_valid_number(phone):
            return text

    except:
        pattern = re.compile(phone_regex)
        phone = pattern.search(text)
        if phone and phone.string == text:
            return text
    return None
