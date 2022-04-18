import os

rootdir = os.path.dirname(__file__)


def find(lookup, matchCase=True):
    """
    :param str lookup: the string to look for
    :param: bool matchCase: take case into account; defaults to True
    :return: A list of all .py files under 'paya' that contain the string.
        Filenames that start with '.' or '_' are ignored.
    :rtype: list
    """
    out = []

    if not matchCase:
        lookup = lookup.lower()

    print("Looking for '{}' under {}...\n".format(lookup, rootdir))

    for root, dirs, files in os.walk(rootdir):
        for fil in files:
            head, tail = os.path.splitext(fil)

            if head:
                if head[0] in ('.', '_'):
                    continue

                if tail == '.py':
                    fullpath = os.path.join(root, fil)

                    with open(fullpath, 'r') as f:
                        data = f.read()

                    if not matchCase:
                        data = data.lower()

                    if lookup in data:
                        print(fullpath)
                        out.append(fullpath)

    print("\nFinished looking.")

    return out