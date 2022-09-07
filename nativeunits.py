import maya.OpenMaya as om
import maya.cmds as m

class NativeUnits:
    """
    Imposes native units, but restores them around scene-save operations so
    that user settings are saved to file.
    """
    callbacks = []
    userLinear = None
    userAngular = None
    track = True

    #--------------------------------------------------|    Set

    @classmethod
    def setLinear(cls, setting):
        cls.track = False
        om.MDistance.setUIUnit(setting)
        cls.track = True

    @classmethod
    def setAngular(cls, setting):
        cls.track = False
        om.MAngle.setUIUnit(setting)
        cls.track = True

    @classmethod
    def getLinear(cls):
        return om.MDistance.uiUnit()

    @classmethod
    def getAngular(cls):
        return om.MAngle.uiUnit()

    @classmethod
    def applyUserLinear(cls):
        if cls.userLinear != cls.getLinear():
            cls.setLinear(cls.userLinear)
            m.warning("Paya: Restored user linear unit.")

    @classmethod
    def applyUserAngular(cls):
        if cls.userAngular != cls.getAngular():
            cls.setAngular(cls.userAngular)
            m.warning("Paya: Restored user angular unit.")

    @classmethod
    def applyNativeLinear(cls):
        if cls.userLinear != om.MDistance.kCentimeters:
            cls.setLinear(om.MDistance.kCentimeters)
            m.warning("Paya: Switched Maya to centimeters.")

    @classmethod
    def applyNativeAngular(cls):
        if cls.userAngular != om.MAngle.kRadians:
            cls.setAngular(om.MAngle.kRadians)
            m.warning("Paya: Switched Maya to radians.")

    #--------------------------------------------------|    Capture

    @classmethod
    def captureUserLinear(cls):
        cls.userLinear = om.MDistance.uiUnit()

    @classmethod
    def captureUserAngular(cls):
        cls.userAngular = om.MAngle.uiUnit()

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
    def start(cls):
        if not cls.callbacks:
            cls.captureUserLinear()
            cls.applyNativeLinear()
            
            cls.captureUserAngular()
            cls.applyNativeAngular()
            
            cls.callbacks = [
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
    def stop(cls):
        if cls.callbacks:
            for callback in cls.callbacks:
                om.MMessage.removeCallback(callback)

            cls.callbacks = []

            om.MDistance.setUIUnit(cls.userLinear)
            om.MAngle.setUIUnit(cls.userAngular)
            cls.userLinear = cls.userAngular = None
            
            