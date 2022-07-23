"""
Internal. Implements the geometry loopbacks.
"""

import inspect
from functools import wraps

from paya.util import short
import paya.runtime as r


class Loopback:
    """
    Used to reappropriate geometry plug methods as shape methods. The plug
    methods are copied over to the shape, and wrapped so that they generate
    shapes instead of output plugs. In some cases the calling shape itself
    will be replaced.

    :Example:

    .. code-block:: python

        class NurbsCurve:

            attach = Loopback()
            detach = Loopback()
    """

    def __set_name__(self, cls, name):
        self.name = name

    def __get__(self, shape, shapeClass):
        if issubclass(shapeClass, r.nodes.Shape):
            plugClass = shapeClass.getPlugClass()

            f = None

            for cls in plugClass.__mro__:
                try:
                    f = cls.__dict__[self.name]

                except KeyError:
                    continue

            if f is None:
                msg = ("Attribute '{}' was not found"+
                       " on the plug class.").format(self.name)

                raise RuntimeError(msg)

            if not inspect.isfunction(f):
                raise RuntimeError(
                    "Retrieved object is not an instance method."
                )

            # Create the wrapper

            @wraps(f)
            def wrapper(self, *args, **kwargs):
                workingPlug = self.getHistoryPlug(create=True)
                result = f(workingPlug, *args, **kwargs)

                multi = isinstance(result, (tuple, list))

                if multi:
                    sourcePlugs = result

                else:
                    sourcePlugs = [result]

                outShapes = []
                heroPlug = sourcePlugs[0]
                pnt = self.getParent()

                # If the output is compatible with self, pipe into
                # self; otherwise create a shape from the hero plug
                # and replace self with it entirely, as Maya's commands
                # do it--this does means the original PyNode instance
                # will be obsolete, and should be replaced with the caught
                # shape return.

                if type(heroPlug) is plugClass:
                    heroPlug >> self.geoInput
                    outShapes.append(self)

                else:
                    r.warning("Shape {} will be replaced.".format(self))
                    origName = self.basename()
                    self.rename('tmp')
                    heroShape = heroPlug.createShape(under=pnt)
                    heroShape.rename(origName)
                    r.delete(self)
                    outShapes.append(heroShape)

                for sourcePlug in sourcePlugs[1:]:
                    # shape = sourcePlug.createShape(under=pnt)
                    shape = sourcePlug.createShape()
                    outShapes.append(shape)

                if multi:
                    return outShapes

                return outShapes[0]

            # Construct a docstring
            methRST = ':meth:`paya.runtime.plugs.{}.{}`'.format(
                plugClass.__name__, self.name
            )

            shortMeth =':meth:`~paya.runtime.plugs.{}.{}`'.format(
                plugClass.__name__, self.name
            )

            doc = \
            """
            .. rubric:: Geometry Loopback
            
            This method is a wrapper for {}.
            Attribute returns are replaced with shapes. These should be
            caught, as some operations may entirely replace the original
            shape instance.
            
            History is always preserved. Use
            :meth:`~paya.runtime.nodes.DeformableShape.deleteHistory` to clear
            where needed.
            
            .. rubric:: Original Documentation
            
            """.format(methRST)

            doc = inspect.cleandoc(doc)
            plugDoc = inspect.getdoc(f)

            if plugDoc:
                doc += "\n\n"+plugDoc

            wrapper.__doc__ = doc

            # If called on an instance, bind to the instance as an
            # instance method

            if shape is not None:
                wrapper = wrapper.__get__(shape, shapeClass)

            return wrapper

        else:
            raise TypeError(
                "Loopbacks can only be added to shape classes."
            )