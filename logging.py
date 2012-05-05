import sys
import os

debug = os.getenv('VERBOSE')
ilevel = 0
continued = False
def log(fmt, *args, more = False):
    global ilevel, continued
    if debug is not None:
        if not continued:
            sys.stderr.write('%s%s' % ('--', '|  ' * ilevel))

        sys.stderr.write(msg % args)

        if more:
            continued = True
        else:
            sys.stderr.write('\n')
            continued = False

def enter(fmt = None, *args):
    global ilevel
    if fmt is not None:
        log(fmt, *args, True)
        log(':')
    ilevel += 1

def leave(val = None):
    global ilevel
    ilevel -= 1
    if val is None:
        log('<')
    else:
        log('< %r' % val)
    return val


