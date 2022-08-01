from functools import wraps

import maya.cmds as m
import maya.OpenMaya as om
import paya.config as config


linearNames = ['inches', 'feet', 'yards', 'miles',
    'millimeters', 'centimeters', 'kilometers', 'meters']

angleNames = ['invalid', 'radians',
    'degrees', 'angle minutes', 'angle seconds']


class NativeUnits:
    """
    Context manager. Switches Maya to centimeters and radians for the
    enclosing block. New scene, open scene and save scene events are
    dodged with API callbacks created on Paya startup.
    """
    #----------------------------------------|    Instantiation

    __instance__ = None

    def __new__(cls, *args, **kwargs):
        if NativeUnits.__instance__ is None:
            NativeUnits.__instance__ = inst = object.__new__(cls)
            inst._userState = {}

        return NativeUnits.__instance__

    #----------------------------------------|    Event management

    __callbacks__ = []

    def addCallbacks(self):
        """
        Creates API callbacks to manage unit settings around new scene, open
        scene and save scene events.
        """
        NativeUnits.__callbacks__ = [
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterNew, self.afterNewCb),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, self.afterOpenCb),
            om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeSave, self.beforeSaveCb),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterSave, self.afterSaveCb)
        ]

    def removeCallbacks(self):
        """
        Removes callbacks created by :meth:`addCallbacks`.
        """
        for callback in NativeUnits.__callbacks__:
            om.MMessage.removeCallback(callback)

        NativeUnits.__callbacks__ = []

    def afterNewCb(self, *args):
        if NativeUnits.__depth__ > 0:
            self.captureUserUnits()
            self.applyNativeUnits()

    def afterOpenCb(self, *args):
        if NativeUnits.__depth__ > 0:
            self.captureUserUnits()
            self.applyNativeUnits()

    def beforeSaveCb(self, *args):
        if NativeUnits.__depth__ > 0:
            self.restoreUserUnits()

    def afterSaveCb(self, *args):
        if NativeUnits.__depth__ > 0:
            self.applyNativeUnits()

    #----------------------------------------|    Setting management

    def captureUserUnits(self):
        self._userState['angle'] = om.MAngle.uiUnit()
        self._userState['linear'] = om.MDistance.uiUnit()

    def applyNativeUnits(self):
        om.MAngle.setUIUnit(om.MAngle.kRadians)
        om.MDistance.setUIUnit(om.MDistance.kCentimeters)

        if self._userState['angle'] != om.MAngle.kRadians:
            m.warning("Switched Maya to {}.".format(angleNames[om.MAngle.kRadians]))

        if self._userState['linear'] != om.MDistance.kCentimeters:
            m.warning("Switched Maya to {}.".format(linearNames[om.MDistance.kCentimeters]))

    def restoreUserUnits(self):
        om.MAngle.setUIUnit(self._userState['angle'])
        om.MDistance.setUIUnit(self._userState['linear'])

        warned = False

        if self._userState['angle'] != om.MAngle.kRadians:
            m.warning("Switched Maya back to {}.".format(angleNames[self._userState['angle']]))
            warned = True

        if self._userState['linear'] != om.MDistance.kCentimeters:
            m.warning("Switched Maya back to {}.".format(linearNames[self._userState['linear']]))
            warned = True

        if warned:
            msg = ("If you get a lot of unit warnings, edit preferences"+
                   " or apply NativeUnits() at a higher level.")

            print(msg)

    #----------------------------------------|    Enter / Exit

    __depth__ = 0

    def __enter__(self):
        if not config['ignoreUnits']:
            if NativeUnits.__depth__ is 0:
                self.captureUserUnits()
                self.applyNativeUnits()

            NativeUnits.__depth__ += 1

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        if not config['ignoreUnits']:
            NativeUnits.__depth__ -= 1

            if NativeUnits.__depth__ is 0:
                self.restoreUserUnits()

        return False

    #----------------------------------------|    Repr

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)

def nativeUnits(f):
    """
    Decorator version of :class:`NativeUnits`.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        with NativeUnits():
            result = f(*args, **kwargs)

        return result

    return wrapper