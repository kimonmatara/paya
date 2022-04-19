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
     - Call :py:meth:`paya.runtime.Runtime.start` on import.

More options may be added in future releases.
"""
import maya.mel as mel

hasDagLocalMatrix = int(mel.eval('getApplicationVersionAsFloat')) > 2022
patchOnLoad = True # runs PyMEL patching as soon as paya.runtime is loaded