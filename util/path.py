"""
Miscellaneous path utilities.
"""
import os
import pathlib as _pl

def toPosix(path):
    """
    :param path: the path to process
    :return: The path, conformed to POSIX format.
    :rtype: str
    """
    return str(_pl.path(path).as_posix())

def toWin(path):
    """
    :param path: the path to process
    :return: The path, conformed to Windows format.
    :rtype: str
    """
    return str(_pl.PureWindowsPath(_pl.Path(path)))

def toOs(path):
    """
    :param path: the path to process
    :return: The path, conformed to Windows or POSIX format, depending on
        detected platform.
    :rtype: str
    """
    if os.name == 'nt':
        return toWin(path)

    return toPosix(path)