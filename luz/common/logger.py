# module imports
from os import name
from sys import stdout


# fix logging if we are running on Windows
if name == 'nt':
	from ctypes import windll
	k = windll.kernel32
	k.SetConsoleMode(k.GetStdHandle(-11), 7)


colors = {
	'black': '\033[30m',
	'red': '\033[31m',
	'green': '\033[32m',
	'orange': '\033[33m',
	'blue': '\033[34m',
	'purple': '\033[35m',
	'cyan': '\033[36m',
	'lightgrey': '\033[37m',
	'darkgrey': '\033[90m',
	'lightred': '\033[91m',
	'lightgreen': '\033[92m',
	'yellow': '\033[93m',
	'lightblue': '\033[94m',
	'pink': '\033[95m',
	'lightcyan': '\033[96m',

	'reset': '\033[0m',
	'bold': '\033[01m',
	'disable': '\033[02m',
	'underline': '\033[04m',
	'reverse': '\033[07m',
	'strikethrough': '\033[09m',
	'invisible': '\033[08m'
}


def log_stdout(tolog: str):
    colorway = colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] + colors['green'] + '*' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset']
    stdout.write(f'{colorway}{tolog}')
    stdout.flush()


def remove_log_stdout(toremove: str):
    colorway = colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] + colors['green'] + '*' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset']
    for _ in range(len(f'{colorway}{toremove}')):
        stdout.write('\033[D \033[D')
        stdout.flush()


def log(message, nln=False):
	n = '\n'
	print(f'{n if nln else ""}' + colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] +
	      colors['green'] + '*' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset'] + f'{message}')


def debug(message, dbg):
	if dbg:
		print(colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] +
		      colors['yellow'] + '#' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset'] + f'{message}')


def warn(message):
	print(colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] +
		colors['yellow'] + '%' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset'] + f'{message}')


def error(message):
	print(colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] +
	      colors['lightred'] + '!' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset'] + f'{message}')


def ask(message):
	return input(colors['bold'] + colors['darkgrey'] + '[' + colors['reset'] + colors['bold'] + colors['orange'] + '?' + colors['bold'] + colors['darkgrey'] + '] ' + colors['reset'] + f'{message} -> ')
