Paya: PyMEL Unleashed
=====================

Paya is an object-oriented toolkit for Maya riggers and TDs. Unlike other systems, it does not re-wrap ``maya.cmds``
or the ``OpenMaya`` API. Instead, it adds new methods directly to
`PyMEL <https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__PyMel_index_html>`_ objects at runtime. This helps you
write code with less boilerplate.

Customisation is easy, and goes far beyond PyMEL's
`virtual classes <https://github.com/LumaPictures/pymel/blob/master/examples/customClasses.py>`_ system to add support
for attribute (including subtype), component and data types with true inheritance for the first time.

.. admonition:: New in Version 0.2

    * :doc:`Maths rigging using Python operators <maths_rigging>`
    * :doc:`Smart node naming <naming_nodes>`
    * :doc:`And more! <whats_new>`

Example #1: Operators
---------------------

Here's a world-space orient constraint with offset preservation, Paya-style:

.. code-block:: python

    master = p.PyNode('locator1')
    slave = p.PyNode('pCube1')

    masterMatrix = slave.getMatrix().inverse() \
        * slave.getMatrix(worldSpace=True) \
        * master.worldMatrix.pick(rotate=True).asOffset()

    masterMatrix >> slave.offsetParentMatrix
    slave.inheritsTransform.set(False)

And here's the equivalent in 'vanilla' PyMEL:

.. code-block:: python

    master = p.PyNode('locator1')
    slave = p.PyNode('pCube1')

    picker = p.createNode('pickMatrix')
    master.worldMatrix >> picker.inputMatrix
    picker.useTranslate.set(False)
    picker.useScale.set(False)
    picker.useShear.set(False)

    multer1 = p.createNode('multMatrix')
    picker.outputMatrix >> multer1.matrixIn[0]
    multer1.matrixIn[1].set(master.worldMatrix.get().inverse())

    initPose = slave.getMatrix(worldSpace=True)

    multer2 = p.createNode('multMatrix')
    multer2.matrixIn[0].set(slave.getMatrix().inverse() * initPose)
    multer1.matrixSum >> multer2.matrixIn[1]

    multer2.matrixSum >> slave.offsetParentMatrix
    slave.inheritsTransform.set(False)

Example #2: Adding a Method to Components
-----------------------------------------

Wouldn't it be nice to have a `getWorldPosition` method on all point-like components, instead of
:func:`~pymel.core.modeling.pointPosition`? Start a file at ``paya/comptypes/discreteComponent.py``, and
add the following lines:

.. code-block:: python

    import pymel.core as p

    class DiscreteComponent:

        def getWorldPosition(self):
            return p.pointPosition(self, world=True)

That's it (no, really). And here's how to use it:

.. code-block:: python

    import pymel.core as p
    import paya.runtime

    curve = p.PyNode('curve1')
    curve.cv[0].getWorldPosition()
    # [0.0, 1.0, 2.0]

Here's how to do it in 'vanilla' PyMEL:

.. code-block:: python

    raise NotImplementedError(
        "You can't. PyMEL's virtual classes do not support components.
    )

.. toctree::
    :hidden:

    What's New <whats_new>
    Requirements & Installation <req_and_inst>

.. toctree::
    :caption: Functionality
    :hidden:

    Importing and Patch Management <importing_and_patch_management>
    Using the Runtime Interface <using_the_runtime_interface>
    Naming Nodes <naming_nodes>
    Maths Rigging <maths_rigging>
    Discovering Functionality <discovering_func>

.. toctree::
    :caption: Customisation
    :hidden:

    Tutorial #1: Custom Methods <method_tutorial>
    Tutorial #2: Custom Constructors <cust_cstr_tutorial>
    Tutorial #3: Custom Operators <op_overl_tutorial>
    Package Configuration <package_config>
    sugar

.. toctree::
    :caption: Appendices
    :hidden:

    Module Documentation <paya>
    implementation
    author