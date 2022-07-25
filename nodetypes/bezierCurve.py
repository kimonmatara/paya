from paya.util import short
import paya.runtime as r


class BezierCurve:

    #----------------------------------------------------------------|    Analysis

    @staticmethod
    def itemsAsAnchorGroups(items):
        """
        :param items: indices, point positions, or whatever else can be mapped
            to CVs; assumes a full CV range
        :type items: list, tuple
        :return: The items organised into a list of dicts, where:

        [
            {'anchor': item, 'out': item}, # first
            {'in': item, 'anchor': item, 'out': item}, # internal
            {'in': item, 'anchor': item} # last
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
                group['anchor'] = items.pop(0)
                group['out'] = items.pop(0)

            elif last:
                group['in'] = items.pop(0)
                group['anchor'] = items.pop(0)

            else:
                group['in'] = items.pop(0)
                group['anchor'] = items.pop(0)
                group['out'] = items.pop(0)

            out.append(group)

        return out

    #----------------------------------------------------------------|    Clusters