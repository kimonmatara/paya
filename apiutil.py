import re

def enumIndexToKey(index, enumClass):
    """
    Given an integer enumerator index, returns the matching key.

    :param enumClass: A class with enumerator keys, for example
        :class:`~maya.OpenMaya.MFn`,
        :class:`~maya.OpenMaya.MFnNumericData`,
        :class:`~maya.OpenMaya.MFnData`
        etc.
    :type enumClass: :class:`~maya.OpenMaya.MFn`
    :param int index: the index for which to retrieve a key
    :return: The key.
    :rtype: :class:`str`
    """
    keys = [k for k in enumClass.__dict__.keys(
            ) if re.match(r"^k[A-Z0-9].*$", k)]

    return dict([(enumClass.__dict__[key], key) for key in keys])[index]