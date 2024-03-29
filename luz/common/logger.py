# module imports
from sys import stdout


colors = {
    "red": "\033[31m",
    "green": "\033[32m",
    "orange": "\033[33m",
    "darkgrey": "\033[90m",
    "yellow": "\033[93m",
    "reset": "\033[0m",
    "bold": "\033[01m",
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


def log(message, emoji: str = "💡", msg: str = "LUZ", lock=None):
    char = emoji + " " + msg
    if lock is not None:
        with lock:
            print(colors["bold"] + colors["green"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message}")
    else:
        print(colors["bold"] + colors["green"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message}")


def debug(message, dbg):
    if dbg:
        print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["yellow"] + "#" + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


def warn(message, emoji: str = "⚠️", msg: str = "LUZ", lock=None):
    char = emoji + " " + msg
    if lock is not None:
        with lock:
            print(colors["bold"] + colors["yellow"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message}")
    else:
        print(colors["bold"] + colors["yellow"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message}")


def error(message, emoji: str = "❌", msg: str = "LUZ", lock=None):
    char = emoji + " " + msg
    if lock is not None:
        with lock:
            print(colors["bold"] + colors["red"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message}")
    else:
        print(colors["bold"] + colors["red"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message}")


def ask(message, char="❓"):
    return input(colors["bold"] + colors["orange"] + char + colors["bold"] + colors["darkgrey"] + ": " + colors["reset"] + f"{message} -> ")
