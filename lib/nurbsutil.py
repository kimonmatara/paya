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