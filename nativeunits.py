import re
from functools import wraps
import maya.OpenMaya as om
import maya.cmds as m

#----------------------------------------------------------------|
#----------------------------------------------------------------|    UTIL
#----------------------------------------------------------------|

linearNames = {}
angularNames = {}

for mapping, cls in zip(
        (linearNames, angularNames),
        (om.MDistance, om.MAngle)
):
    for k, v in cls.__dict__.items():
        if k.startswith('k'):
            key = re.match(r"^k(.*)$", k).groups()[0]
            key = key[0].lower()+key[1:]
            mapping[v] = key

#----------------------------------------------------------------|
#----------------------------------------------------------------|    CONTEXT MANAGER
#----------------------------------------------------------------|

class NativeUnits:
    """
    Context manager. Sets Maya to native units (centimeters and radians)
    across the block. This is enforced with callbacks for incidental
    Maya events that might change the setting (e.g. opening scenes), but
    not for explicit calls to :func:`~maya.cmds.currentUnit` or
    :meth:`~maya.OpenMaya.MDistance.setUIUnit`.

    This context manager is engaged automatically when :mod:`paya.runtime`
    is entered as a context block.
    """
    __user_linear__ = None
    __user_angular__ = None
    __track_changes__ = True
    __depth__ = 0

    #------------------------------------------------------|    Enter / Exit

    def __enter__(self):
        NativeUnits.__depth__ += 1

        if NativeUnits.__depth__ is 1:
            NativeUnits.__user_linear__ = om.MDistance.uiUnit()
            NativeUnits.__user_angular__ = om.MAngle.uiUnit()

            om.MDistance.setUIUnit(om.MDistance.kCentimeters)
            om.MAngle.setUIUnit(om.MAngle.kRadians)

            self._startCallbacks()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        NativeUnits.__depth__ -= 1

        if NativeUnits.__depth__ is 0:
            self._stopCallbacks()
            om.MDistance.setUIUnit(self.__user_linear__)
            om.MAngle.setUIUnit(self.__user_angular__)

    #------------------------------------------------------|    Callbacks

    @classmethod
    def _startCallbacks(cls):
        NativeUnits.__callbacks__ = [
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen,
                                         NativeUnits.afterOpenCb),
            om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeSave,
                                         NativeUnits.beforeSaveCb),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterSave,
                                         NativeUnits.afterSaveCb),
            om.MEventMessage.addEventCallback('linearUnitChanged',
                                              cls.linearUnitChangedCb),
            om.MEventMessage.addEventCallback('angularUnitChanged',
                                              cls.angularUnitChangedCb)
            ]

    @classmethod
    def _stopCallbacks(cls):
        for callback in NativeUnits.__callbacks__:
            om.MMessage.removeCallback(callback)

        cls.__callbacks__ = []

    @classmethod
    def afterOpenCb(cls, *args):
        cls.__user_linear__ = om.MDistance.uiUnit()
        cls.__user_angular__ = om.MAngle.uiUnit()

        with NoChangeTracking():
            om.MDistance.setUIUnit(om.MDistance.kCentimeters)
            om.MAngle.setUIUnit(om.MAngle.kRadians)

    @classmethod
    def beforeSaveCb(cls, *args):
        with NoChangeTracking():
            om.MDistance.setUIUnit(NativeUnits.__user_linear__)
            om.MAngle.setUIUnit(NativeUnits.__user_angular__)

    @classmethod
    def afterSaveCb(cls, *args):
        with NoChangeTracking():
            om.MDistance.setUIUnit(om.MDistance.kCentimeters)
            om.MAngle.setUIUnit(om.MAngle.kRadians)

    @classmethod
    def linearUnitChangedCb(cls, *args):
        if NativeUnits.__track_changes__:
            NativeUnits.__user_linear__ = om.MDistance.uiUnit()

    @classmethod
    def angularUnitChangedCb(cls, *args):
        if NativeUnits.__track_changes__:
            NativeUnits.__user_angular__ = om.MAngle.uiUnit()


class NoChangeTracking:
    __depth__ = 0

    def __enter__(self):
        NoChangeTracking.__depth__ += 1

        if NoChangeTracking.__depth__ is 1:
            NativeUnits.__track__ = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        NoChangeTracking.__depth__ -= 1

        if NoChangeTracking.__depth__ is 0:
            NativeUnits.__track__ = True

def nativeUnits(f):
    """
    Decorator version of :class:`NativeUnits`.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        with NativeUnits():
            return f(*args, **kwargs)

    return wrapper