from collections import UserDict
import os
import json

import pymel.util as _pu
import pymel.core as p
from paya.util import short, LazyModule

r = LazyModule('paya.runtime')

#------------------------------------------------------------|    Constants

libpath = os.path.join(
    os.path.dirname(__file__),
    'controlshapes.json'
)

class NoControlShapesError(RuntimeError):
    """
    No shapes were found under the specified control(s).
    """

class ControlShapesLibrary(UserDict):
    """
    Administers Paya control shapes.
    """

    #------------------------------------------------------|    Init

    __instance__ = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance__ is None:
            cls.__instance__ = object.__new__(cls)

        return cls.__instance__

    def __init__(self):
        self.load()

    #------------------------------------------------------|    I/O

    def load(self):
        """
        Loads the library content fromn ``paya/lib/controlshapes.json``.

        :return: ``self``
        """
        try:
            with open(libpath, 'r') as f:
                data = f.read()

            data = json.loads(data)
            print("Control shapes read from: "+libpath)

        except IOError:
            r.warning("Missing control shapes library: "+libpath)
            data = {}

        self.data = data

        return self

    def dump(self):
        """
        Dumps the library content into ``paya/lib/controlshapes.json``.

        :return: ``self``
        """
        data = json.dumps(self.data)
        with open(libpath, 'w') as f:
            f.write(data)

        print("Control shapes saved into: "+libpath)

        return self

    #------------------------------------------------------|    Appying

    @short(replace='rep')
    def applyToControls(self, name, controls, replace=True):
        """
        Adds shapes to the specified controls from the named library entry.

        :param name: the name of the library entry to retrieve
        :param list controls: the controls to add shapes to
        :param bool replace/rep: replace existing shapes on the controls;
            defaults to True
        :return: The newly-generated control shape nodes.
        :rtype: list of :class:`~paya.runtime.nodes.Shape`
        """
        macros = self[name]
        srcShapes = [
            r.nodes.DependNode.createFromMacro(macro) for macro in macros]

        for srcShape in srcShapes:
            srcShape.addAttr('libCtrlShape', dt='string').set(name)

        srcGp = r.group(empty=True)

        for srcShape in srcShapes:
            parent = srcShape.getParent()
            r.parent(srcShape, srcGp, r=True, shape=True)
            r.delete(parent)

        newShapes = srcGp.copyCtShapesTo(controls, color=False, rep=replace)
        r.delete(srcGp)

        return newShapes

    def addFromControl(self, control, name):
        """
        Captures shape macros from the specified control and adds them under
        a new entry in the library.

        .. warning::

            If the name already exists in the library, it will be overwritten.

        .. note::

            Changes are not saved into ``paya/lib/controlshapes.json`` until
            :meth:`~paya.lib.controls.ControlShapesLibrary.dump` is called.

        :param control: the control to inspect
        :type control: str, :class:`~paya.runtime.nodes.Transform`
        :param str name: the name for the new entry
        :raises NoControlShapesError: no control shapes were found under the
            control
        :return: ``self``
        """
        control = r.PyNode(control)
        shapes = control.getCtShapes()

        if shapes:
            macros = []

            for shape in shapes:
                macro = shape.macro()
                shape.normalizeMacro(macro)
                macros.append(macro)

            self[name] = macros

        else:
            raise NoControlShapesError

        return self

controlShapes = ControlShapesLibrary()