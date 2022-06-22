import sys
import os
import json
from collections import UserDict

class Config(UserDict):
    """
    Dict-like object, inserted into :attr:`sys.modules` as a module. Initial
    values are read from ``paya/config.json`` on startup. Edits are only
    valid for the current session. The object can also be used as a context
    manager, with temporary overrides passed-in as keyword arguments:

    .. code-block:: python

        import paya.config as config

        print(config['suffixNodes'])
        # True

        with config(suffixNodes=False):
            print(config['suffixNodes'])
        # False

        print(config['suffixNodes'])
        # False
    """

    class Overrides:
        def __init__(self, inst, **overrides):
            self.inst = inst
            self.overrides = overrides

        def __enter__(self):
            self.prev = {k:self.inst[k] for k in self.overrides}
            self.inst.update(self.overrides)

            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.inst.update(self.prev)

            return False

    def __call__(self, **overrides):
        return self.Overrides(self, **overrides)

path = os.path.join(
    os.path.dirname(__file__),
    'config.json'
)

with open(path, 'r') as f:
    data = f.read()

data = json.loads(data)

sys.modules['paya.config'] = Config(data)