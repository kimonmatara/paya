Paya: PyMEL for Riggers
=======================

Paya lets you write radically condensed rigging code for Autodesk Maya. Unlike other libraries, it does not re-wrap
``maya.cmds`` or the `OpenMaya <https://help.autodesk.com/view/MAYAUL/2023/ENU/?guid=Maya_SDK_Maya_Python_API_html>`_
API. Instead, it adds functionality to
`PyMEL <https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__PyMel_index_html>`_ objects at runtime for a fully
integrated experience.

Included is a deep, and intuitive, implementation for maths rigging using Python operators .
This eliminates boilerplate for node hookups and lets you freely mix values and attributes in the same expression.

Customisation is easy, and goes far beyond PyMEL's
`virtual classes <https://github.com/LumaPictures/pymel/blob/master/examples/customClasses.py>`_ system to add support
for attribute (including subtype), component and data types with true inheritance for the first time.

New in Version 0.3
------------------

*   Over 100 new methods , from scalar looping and DG logic gates to vector, quaternion and matrix
    operations.
*   A one-stop method for constructing static and dynamic matrices: ``createMatrix``
*   Attribute subtypes have been reworked for better handling of angle channels

Full documentation, with examples, can be found `here <https://kimonmatara.github.io/paya/>`_.