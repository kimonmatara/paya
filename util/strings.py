"""
Utilities for managing strings.
"""

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