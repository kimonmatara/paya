import paya.runtime as r

def getKnotList(numCVs, degree):
    """
    Given a number of CVs and a degree, returns a knot list.

    :param int numCVs: the number of CVs
    :param int degree: the degree; one of 1, 2, 3, 5 or 7
    :return: The knot list.
    :rtype: [int]
    """
    numbers = list(range(numCVs-(degree-1)))
    head = [numbers[0]] * degree
    tail = [numbers[-1]] * degree
    return head + numbers[1:-1] + tail

def conformUParamArg(uParam):
    """
    If *uParam* is a component, returns its float form; otherwise returns
    an attribute instance.

    :param uParam: the U curve parameter argument to conform
    :type uParam: float, str,
        :class:`~paya.runtime.comps.NurbsCurveParameter`,
        :class:`~paya.runtime.plugs.Math1D`
    :return: The conformed parameter.
    """
    if isinstance(uParam, (float, r.Attribute)):
        return uParam

    if isinstance(uParam, r.Component):
        return float(uParam)

    if isinstance(uParam, str):
        if '.u[' in uParam:
            return r.Component(uParam)

        return r.Attribute(uParam)

    raise TypeError("Can't conform U parameter: {}".format(uParam))

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