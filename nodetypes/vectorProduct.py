from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r


class VectorProduct:

    #----------------------------------------------------|    Constructor

    @classmethod
    @short(normalize='nr',
           guard='g',
           inlineGate='ig',
           name='n')
    def createAsCross(cls,
                      input1,
                      input2,
                      normalize=False,
                      guard=False,
                      inlineGate=None,
                      name=None):
        """
        Creates and configures a :class:`vectorProduct <VectorProduct>` for
        cross product calculation, with options to prevent errors when the
        vectors are in-line.

        :param input1: the first vector
        :type input1: :class:`tuple`, :class:`list`,
            :class:`str`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param input2: the first vector
        :type input2: :class:`tuple`, :class:`list`,
            :class:`str`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool normalize/nr: normalize the output; defaults to
            ``False``
        :param bool guard/g: switch the node to 'No Operation' when the
            input vectors are aligned in either direction; defaults to
            ``False``
        :param bool inlineGate/ig: if you have a precooked gate for alignment
            (typically the output of a comparison operation), provide it here
            to prevent redundant checks; if provided, will override *guard*
            to ``True``; defaults to ``None``
        :param str name/n: a name for the node; defaults to ``None``
        :return: The configured node.
        :rtype: :class:`VectorProduct`
        """
        node = cls.createNode(name=name if name else cls.makeName())

        input1, input1Dim, input1UnitType, input1IsPlug = \
            _mo.info(input1).values()
        input2, input2Dim, input2UnitType, input2IsPlug = \
            _mo.info(input2).values()

        if inlineGate is not None:
            guard = True

        if guard:
            node.attr('input1').put(input1, p=input1IsPlug)
            node.attr('input2').put(input2, p=input2IsPlug)

            if inlineGate is None:
                dot = input1.dot(input2, nr=True).abs()
                inlineGate = dot.ge(1.0-1e-6)

            inlineGate >> node.addAttr('inline', at='bool', k=True)
            inlineGate = node.attr('inline')

            operationWhenInline = node.addAttr(
                'operationWhenInline', k=True, at='long', dv=0)

            operationWhenNotInline = node.addAttr(
                'operationWhenNotInline', k=True, at='long', dv=2
            )

            resolvedOperation = inlineGate.ifElse(
                operationWhenInline,
                operationWhenNotInline
            )

            resolvedOperation >> node.attr('operation')

        else:
            node.attr('input1').put(input1, p=input1IsPlug)
            node.attr('input2').put(input2, p=input2IsPlug)
            node.attr('operation').set(2)

        node.attr('normalizeOutput').set(normalize)

        return node