from __future__ import print_function
import pprint
import sys
import hashlib

import regex

from emoji_unicode import emoji_unicode

def is_emoji(title):
    re_emoji = regex.findall(r'.\p{Sk}+|\X', title)

    for possible_emoji in re_emoji:
        for char in possible_emoji:
            char_unicode = hex(ord(char))
            eprint(char_unicode)
            if char_unicode not in emoji_unicode:
                return False

    if len(re_emoji) == 0 or len(re_emoji) > 3:
        return False

    return True


def encode_value(token, salt):
    return hashlib.sha512("{0}{1}".format(token, salt).encode('utf-8')).hexdigest()

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def epprint(*args, **kwargs):
    pretty = pprint.pformat(*args)
    print(pretty, file=sys.stderr, **kwargs)
