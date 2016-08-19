from __future__ import print_function
import pprint
import sys
import hashlib

import emoji

def is_emoji(title):
    emojis = []
    if len(title) < 10:
        for char in title:
            if char in emoji.UNICODE_EMOJI:
                emojis.append(char)
    else:
        return False

    if len(emojis) == 0 or len(emojis) > 3:
        return False

    return True


def encode_value(token, salt):
    return hashlib.sha512("{0}{1}".format(token, salt).encode('utf-8')).hexdigest()

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def epprint(*args, **kwargs):
    pretty = pprint.pformat(*args)
    print(pretty, file=sys.stderr, **kwargs)
