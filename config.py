"""
Manages paya configuration.
"""
import re
import maya.cmds as m
import maya.mel as mel

hasDagLocalMatrix = int(mel.eval('getApplicationVersionAsFloat')) > 2022
patchOnLoad = True # runs PyMEL patching as soon as paya.runtime is loaded
