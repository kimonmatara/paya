import os
import sys

def path_to_dotpath(path):
    """
    Given a full path to a module file, this returns the dot-path to be
    used in import statements. The path must be reachable by Python.
    """
    current = path
    elems = list()

    while True:
        if current == path:
            basename = os.path.splitext(
                os.path.basename(current)
            )[0]

            elems.insert(0,basename)
            current = os.path.dirname(current)
            continue

        listing = os.listdir(current)

        if '__init__.py' in listing or '__init__.pyc' in listing:
            elems.insert(0, os.path.basename(current))
            current = os.path.dirname(current)
        else:
            if current not in sys.path:
                raise RuntimeError('paya.util.modules.path_to_dotpath(): '+
                                   "The specified path, '"+path+"' cannot be "+
                                   'reached. Check __init__.py files and sys.path.')
            else: break

    return '.'.join(elems)