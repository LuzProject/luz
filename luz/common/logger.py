# module imports
from os import name
from sys import stdout


# fix logging if we are running on Windows
if name == "nt":
    from ctypes import windll

    k = windll.kernel32
    k.SetConsoleMode(k.GetStdHandle(-11), 7)


colors = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "orange": "\033[33m",
    "blue": "\033[34m",
    "purple": "\033[35m",
    "cyan": "\033[36m",
    "lightgrey": "\033[37m",
    "darkgrey": "\033[90m",
    "lightred": "\033[91m",
    "lightgreen": "\033[92m",
    "yellow": "\033[93m",
    "lightblue": "\033[94m",
    "pink": "\033[95m",
    "lightcyan": "\033[96m",
    "reset": "\033[0m",
    "bold": "\033[01m",
    "disable": "\033[02m",
    "underline": "\033[04m",
    "reverse": "\033[07m",
    "strikethrough": "\033[09m",
    "invisible": "\033[08m",
}


def log_stdout(message, lock=None):
    colorway = colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["green"] + "*" + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"]
    if lock is not None:
        with lock:
            stdout.write(f"{colorway}{message}")
            stdout.flush()
    else:
        stdout.write(f"{colorway}{message}")
        stdout.flush()


def remove_log_stdout(message, lock=None):
    colorway = colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["green"] + "*" + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"]
    if lock is not None:
        with lock:
            for _ in range(len(f"{colorway}{message}")):
                stdout.write("\033[D \033[D")
                stdout.flush()
    else:
        for _ in range(len(f"{colorway}{message}")):
            stdout.write("\033[D \033[D")
            stdout.flush()


def log(message, char: str = "INF", lock=None):
    if lock is not None:
        with lock:
            print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["green"] + char + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")
    else:
        print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["green"] + char + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


def debug(message, dbg):
    if dbg:
        print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["yellow"] + "#" + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


def warn(message, char: str = "WRN"):
    print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["yellow"] + char + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


def error(message, char: str="ERR", lock=None):
    if lock is not None:
        with lock:
            print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["red"] + char + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")
    else:
        print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["red"] + char + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


def ask(message, char="ASK"):
    return input(
        colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["orange"] + char + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message} -> "
    )
