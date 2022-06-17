import re


class NurbsCurveParameter:

    #-----------------------------------------------------|    Conversions

    def __float__(self):
        """
        :return: This parameter as a float.
        :rtype: :class:`float`
        """
        return float(re.match(r"^.*?\[(.*)\]$", str(self)).groups()[0])