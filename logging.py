import sys
import os

from colors import *

debug = os.getenv('VERBOSE')
ilevel = 0
continued = False
def log(fmt, *args, **kwargs):
    global ilevel, continued
    if debug:
        if not continued:
            sys.stderr.write('%s%s' % ('--', '|  ' * ilevel))

        sys.stderr.write(fmt % args)

        if kwargs.get('more', False):
            continued = True
        else:
            sys.stderr.write('\n')
            continued = False

def enter(fmt = None, *args):
    global ilevel
    if fmt is not None:
        log(fmt, *args, more = True)
        log(':')
    ilevel += 1

def leave(val = None):
    global ilevel
    ilevel -= 1
    if val is None:
        log('<< ')
    else:
        log('<< %r', val)
    return val

def xrepr(obj):
    if type(obj) == type(xrepr): # is it a function?
        return '<function %s>' % obj.__name__
    return repr(obj)


def informp(*stparams):
    def decorator(func):
        def wrapper(*args, **kwargs):
            
            txt = func.__name__
            
            if len(stparams) > 0:
                txt += '[%s]' % ', '.join((xrepr(x) for x in stparams))
                
            argrep = [xrepr(x) for x in args] + [('%s = %r' % x) for x in kwargs.items()]
            txt += '(%s)' % ', '.join(argrep)

            enter(txt)

            r = func(*args, **kwargs)

            return leave(r)

        wrapper.__name__ = func.__name__
        if debug:
            return wrapper
        else:
            return func
    return decorator

def inform(func):
    return informp()(func)

def informobjp(*stparams, **topkwargs):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            
            txt = '%s%s@%x%s.%s' % (self.__class__.__name__,
                                    cDARK, id(self), cNORMAL,
                                    func.__name__)
            
            if len(stparams) > 0:
                txt += '[%s]' % ', '.join((xrepr(x) for x in stparams))
                
            argrep = [xrepr(x) for x in args] + [('%s = %r' % x) for x in kwargs.items()]
            txt += '(%s)' % ', '.join(argrep)

            enter(txt)

            if topkwargs.get('updater',False) and (func.__name__ != "__init__"):
                # no state prior to init
                log("%sobject before:%s %s", cRED, cNORMAL, self) 

            r = func(self, *args, **kwargs)

            if topkwargs.get('updater',False):
                log("%sobject after: %s %s", cRED, cNORMAL, self) 

            return leave(r)

        wrapper.__name__ = func.__name__
        if debug:
            return wrapper
        else:
            return func
    return decorator

def informobj(func):
    return informobjp()(func)

if __name__ == "__main__":
    debug = True
    log("hello", more=True)
    log(" world")
    log(" %s %s", 'q', 'r')
    debug = False
    log("should not see")

__all__ = [
    'log',
    'enter',
    'leave',
    'inform',
    'informp',
    'informobj',
    'informobjp'
]
