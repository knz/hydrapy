import os

if os.getenv('TERM') in ['vt100','xterm','rxvt','screen','ansi']:
    cNORMAL = '\x1b[0m'
    cGREEN = '\x1b[1;32m'
    cBLUE = '\x1b[1;34m'
    cDARK = '\x1b[1;30m'
    cBRIGHT = '\x1b[1;37m'
else:
    cNORMAL = ''
    cGREEN = ''
    cBLUE = ''
    cDARK = ''
    cBRIGHT = ''

__all__ = [
    'cNORMAL',
    'cGREEN',
    'cBLUE',
    'cDARK',
    'cBRIGHT'
]
