from functools import wraps
import maya.OpenMaya as om
import maya.cmds as m
from paya.util import short


class NativeUnits:

    __depth__ = 0
    __force__ = False
    __callbacks__ = []
    __track__ = True
    __userLinear__ = None
    __userAngular__ = None

    #---------------------------------------------------|    Init

    @short(force='f')
    def __init__(self, force=False):
        self.force = force

    #---------------------------------------------------|    Context

    def __enter__(self):
        NativeUnits.__depth__ += 1

        if NativeUnits.__depth__ is 1:
            self.captureUserLinear()
            self.captureUserAngular()

            self.applyNativeLinear()
            self.applyNativeAngular()

        self.prev_force = NativeUnits.__force__

        if not NativeUnits.__force__:
            NativeUnits.__force__ = True

        if NativeUnits.__force__ and not NativeUnits.__callbacks__:
            self.addCallbacks()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        NativeUnits.__force__ = self.prev_force

        if (not NativeUnits.__force__) and NativeUnits.__callbacks__:
            self.removeCallbacks()

        NativeUnits.__depth__ -= 1

        if NativeUnits.__depth__ is 0:
            self.applyUserLinear()
            self.applyUserAngular()

            NativeUnits.__userLinear__ = NativeUnits.__userAngular__ = None

        return False

    #---------------------------------------------------|    Setting
    
    @classmethod
    def setLinear(cls, setting):
        cls.__track__ = False
        om.MDistance.setUIUnit(setting)
        cls.__track__ = True

    @classmethod
    def setAngular(cls, setting):
        cls.__track__ = False
        om.MAngle.setUIUnit(setting)
        cls.__track__ = True

    @classmethod
    def getLinear(cls):
        return om.MDistance.uiUnit()

    @classmethod
    def getAngular(cls):
        return om.MAngle.uiUnit()

    @classmethod
    def applyUserLinear(cls):
        if cls.__userLinear__ != cls.getLinear():
            cls.setLinear(cls.__userLinear__)
            m.warning("Paya: Restored user linear unit.")

    @classmethod
    def applyUserAngular(cls):
        if cls.__userAngular__ != cls.getAngular():
            cls.setAngular(cls.__userAngular__)
            m.warning("Paya: Restored user angular unit.")

    @classmethod
    def applyNativeLinear(cls):
        if cls.__userLinear__ != om.MDistance.kCentimeters:
            cls.setLinear(om.MDistance.kCentimeters)
            m.warning("Paya: Switched Maya to centimeters.")

    @classmethod
    def applyNativeAngular(cls):
        if cls.__userAngular__ != om.MAngle.kRadians:
            cls.setAngular(om.MAngle.kRadians)
            m.warning("Paya: Switched Maya to radians.")

    #--------------------------------------------------|    Capture

    @classmethod
    def captureUserLinear(cls):
        cls.__userLinear__ = om.MDistance.uiUnit()

    @classmethod
    def captureUserAngular(cls):
        cls.__userAngular__ = om.MAngle.uiUnit()

    #--------------------------------------------------|    Callbacks

    @classmethod
    def linearUnitChangedCb(cls, *args):
       cls.captureUserLinear()
       cls.applyNativeLinear()

    @classmethod
    def angularUnitChangedCb(cls, *args):
        cls.captureUserAngular()
        cls.applyNativeAngular()

    @classmethod
    def beforeSaveCb(cls, *args):
        cls.applyUserLinear()
        cls.applyUserAngular()

    @classmethod
    def afterSaveCb(cls, *args):
        cls.applyNativeLinear()
        cls.applyNativeAngular()

    #--------------------------------------------------|    Start / stop

    @classmethod
    def addCallbacks(cls):
        cls.__callbacks__ = [
            om.MEventMessage.addEventCallback(
                'linearUnitChanged', cls.linearUnitChangedCb),
            om.MEventMessage.addEventCallback(
                'angularUnitChanged', cls.angularUnitChangedCb),
            om.MSceneMessage.addCallback(
                om.MSceneMessage.kBeforeSave,
                cls.beforeSaveCb
            ),
            om.MSceneMessage.addCallback(
                om.MSceneMessage.kAfterSave,
                cls.afterSaveCb
            )
        ]

    @classmethod
    def removeCallbacks(cls):
        for callback in cls.__callbacks__:
            om.MMessage.removeCallback(callback)

        cls.__callbacks__ = []

def nativeUnits(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with NativeUnits():
            result = f(*args, **kwargs)

        return result

    return wrapper