# """
# Miscellaneous NURBS-related helpers.
# """
#
# def validateDegree(degree):
#     """
#     Passes the degree through if it's valid, otherwise raises errors.
#
#     :param int degree: the degree to inspect
#     :raises ValueError: the specified degree is not one of
#         1, 2, 3, 6 or 7
#     :raises TypeError: the degree is not an integer
#     :return: The degree.
#     :rtype: int
#     """
#     if not isinstance(degree, int):
#         raise TypeError("Not an integer: {}".format(degree))
#
#     if degree not in (1, 2, 3, 5, 7):
#         raise ValueError("Invalid degree: {}".format(degree))
#
#     return degree
#
def minCVsForDegree(degree):
    """
    :param int degree: the degree
    :return: the minimum number of CVs possible for the specified degree
    """
    degree = validateDegree(degree)
    return degree + 1

def numSpansFromNumCVsAndDegree(numCVs, degree):
    """
    Given a number of CVs and a degree, returns the number of spans.

    :param int numCVs: the number of CVs
    :param int degree: the degree
    :return: The number of spans.
    :rtype: int
    """
    if numCVs < 2:
        raise ValueError("The number of CVs must be greater than 1.")

    return numCVs-validateDegree(degree)