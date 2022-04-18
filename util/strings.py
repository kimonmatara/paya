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

def pad(number, padding):
    """
    Simple number padder.

    :param int number: the number to pad
    :param padding: the padding depth
    :return: The padded number.
    """
    number = str(number)
    ln = len(number)

    return ('0' * (padding-ln)) + number