from paya.util import short
import paya.runtime as r

fieldsmap = {
    'x': ['in00','in01','in02'],
    'y': ['in10','in11','in12'],
    'z': ['in20','in21','in22'],
    't': ['in30','in31','in32'],
    'translate': ['in30','in31','in32'],
}


class FourByFourMatrix:

    #-----------------------------------------------------------|    Row management

    @short(normalize='nr')
    def getAxis(self, requestedAxis, normalize=False):
        """
        Retrieves, or initialises, a compound 'proxy' that will govern all
        the row fields for the requested axis.

        :param str requestedAxis: one of 'x', 'y', 'z', '-x', '-y', '-z',
            'translate' or 't'
        :param bool normalize/nr: normalize the extracted vector / point;
            defaults to False
        :return: The compound attribute, or its normalization / negation.
        :rtype: :class:`~paya.plugtypes.vector.Vector`
        """
        requestedAxis = {'t': 'translate'}.get(requestedAxis, requestedAxis)
        absRequestedAxis = requestedAxis.strip('-')
        attrName = '{}Compound'.format(absRequestedAxis)

        if not self.hasAttr(attrName):
            # Build the compound

            self.addAttr(attrName, at='double3', k=True, nc=3)

            defaultValues = {
                'x': [1,0,0],
                'y': [0,1,0],
                'z': [0,0,1],
                'translate': [0,0,0]
            }[absRequestedAxis]

            for axis, defaultValue in zip('XYZ', defaultValues):
                self.addAttr('{}{}'.format(attrName, axis
                    ), k=True, at='double', dv=defaultValue, parent=attrName)


            # Hijack connections

            origPlugs = [self.attr(field
                ) for field in fieldsmap[absRequestedAxis]]

            for origPlug, proxyPlug in zip(origPlugs, self.attr(attrName)):
                inputs = origPlug.inputs(plugs=True)

                if inputs:
                    inputs[0] >> proxyPlug

                else:
                    proxyPlug.set(origPlug.get())

                proxyPlug >> origPlug

        plug = self.attr(attrName)

        if normalize:
            plug = plug.normal()

        if '-' in requestedAxis:
            plug *= -1.0

        return plug

    def getX(self, normalize=False):
        """
        Initialises or retrieves the compound 'proxy' for the X vector. See
        :meth:`getAxis`. Used to implement the **x** property.
        """
        return self.getAxis('x', nr=normalize)

    x = property(fget=getX)

    def getY(self, normalize=False):
        """
        Initialises or retrieves the compound 'proxy' for the Y vector. See
        :meth:`getAxis`. Used to implement the **y** property.
        """
        return self.getAxis('y', nr=normalize)

    y = property(fget=getY)

    def getZ(self, normalize=False):
        """
        Initialises or retrieves the compound 'proxy' for the Z vector. See
        :meth:`getAxis`. Used to implement the **z** property.
        """
        return self.getAxis('z', nr=normalize)

    z = property(fget=getZ)

    def getTranslate(self, normalize=False):
        """
        Initialises or retrieves the compound 'proxy' for the translate row.
        See :meth:`getAxis`. Used to implement the **translate** / **t**
        property.
        """
        return self.getAxis('t', nr=normalize)

    t = translate = property(fget=getTranslate)