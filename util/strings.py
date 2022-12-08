"""
Utilities for managing strings.
"""
import string
import math

def pad(number, padding):
    """
    Simple number padder.

    :param int number: the number to pad
    :param int padding: the padding depth
    :return: The padded number.
    :rtype: str
    """
    tail = str(number)
    head = '0' * (padding-len(tail))
    return head+tail

def capitalize(st):
    """
    :shorthand: cap

    :param str st: the string to capitalize
    :return: The capitalized string.
    """
    return st[0].upper()+st[1:]

cap = capitalize

def uncapitalize(st):
    """
    :shorthand: uncap

    :param str st: the string to uncapitalize
    :return: The uncapitalized string.
    """
    return st[0].lower()+st[1:]

uncap = uncapitalize

def int_to_letter(number):
    """
    :param int number: the integer to convert to a letter (1-based)
    :return: A letter representation of the given integer number
        (0-based). Numbers larger than 25 will be indicated using
        doubled letters.
    """
    number -= 1

    if number is 0:
        numWinds = 1
    else:
        numWinds = math.ceil(number / 26)
    return string.ascii_lowercase[number % 26] * numWinds