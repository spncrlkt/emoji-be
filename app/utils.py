from __future__ import print_function
import pprint
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def epprint(*args, **kwargs):
    pretty = pprint.pformat(*args)
    print(pretty, file=sys.stderr, **kwargs)
