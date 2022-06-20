"""
Provides relevant environment information.
"""
import maya.mel as mel

hasDagLocalMatrix = int(mel.eval('getApplicationVersionAsFloat')) > 2022