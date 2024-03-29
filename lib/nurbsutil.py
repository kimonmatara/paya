import paya.runtime as r

def getKnotList(numCVs, degree, bezier=False):
    """
    Given a number of CVs and a degree, returns a knot list.

    :param int numCVs: the number of CVs
    :param int degree: the degree; one of 1, 2, 3, 5 or 7
    :return: The knot list.
    :rtype: [int]
    """
    if bezier:
        if legalNumCVsForBezier(numCVs) and degree is 3:
            numAnchors = int((numCVs + 2) / 3)
            out = []

            for i in range(numAnchors):
                out += [i] * 3

            return out

        raise RuntimeError(
            "Invalid number of CVs for bezier, or degree is not 3."
        )

    else:
        numbers = list(range(numCVs-(degree-1)))
        head = [numbers[0]] * degree
        tail = [numbers[-1]] * degree
        return head + numbers[1:-1] + tail

def itemsAsBezierAnchors(items):
    """
    :param items: indices, point positions, or whatever else can be mapped
        to CVs; assumes a full CV range
    :type items: list, tuple
    :return: The items organised into a list of dicts, where:

    .. code-block:: python

        [
            {'root': item, 'out': item}, # first
            {'in': item, 'root': item, 'out': item}, # internal
            {'in': item, 'root': item} # last
        ]

    :rtype: [dict]
    """
    items = list(items)
    numCVs = len(items)
    numAnchors = (numCVs + 2) / 3

    if numAnchors.is_integer():
        numAnchors = int(numAnchors)

    else:
        raise ValueError("Invalid number of CVs for a bezier curve.")

    out = []

    for i in range(numAnchors):
        if i is 0:
            first, last = True, False

        elif i is numAnchors-1:
            first, last = False, True

        else:
            first = last = False

        group = {}

        if first:
            group['root'] = items.pop(0)
            group['out'] = items.pop(0)

        elif last:
            group['in'] = items.pop(0)
            group['root'] = items.pop(0)

        else:
            group['in'] = items.pop(0)
            group['root'] = items.pop(0)
            group['out'] = items.pop(0)

        out.append(group)

    return out

def legalNumCVsForBezier(numCVs):
    """
    :param int numCVs: the number of CVs
    :return: ``True`` if the specified number of CVs is legal for a
        bezier curve, otherwise False.
    """
    numAnchors = (numCVs + 2) / 3
    return numAnchors.is_integer()