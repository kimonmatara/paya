"""
Defines package-level configuration flags. Currently, these are:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Flag
     - Default Value
     - Description
   * - ``patchOnLoad``
     - ``True``
     - Call :py:meth:`~paya.runtime.Runtime.start` the first time :mod:`paya.runtime` is imported.
   * - ``autoSuffix``
     - ``True``
     - Apply :ref:`node suffixes <Automatic Suffixes>` automatically.

More options may be added in future Paya releases.
"""
import maya.mel as mel

# General inspections

hasDagLocalMatrix = int(mel.eval('getApplicationVersionAsFloat')) > 2022

# Importing behaviour

patchOnLoad = True # runs PyMEL patching as soon as paya.runtime is loaded

# Name management

autoSuffix = True

# Default skeleton building

defaultDownAxis = 'y'
defaultUpAxis = 'x'