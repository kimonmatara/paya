def findKeyInClassDicts(key, cls, start=0):
    """
    Looks across every dict in the class MRO for the requested key and
    retrieves the fist available value.

    :param str key: the key to look up
    :param type cls: the class to inspect
    :param int start: the start index on the MRO to start scanning from;
        defaults to 0
    :raises KeyError: The key wasn't found in any of the MRO dicts.
    :return: The retrieved value.
    """
    for anc in cls.__mro__[start:]:
        try:
            return anc.__dict__[key]

        except KeyError:
            continue

    raise KeyError(
        "'{}' not found across the mro dicts for {}".format(key, cls)
    )