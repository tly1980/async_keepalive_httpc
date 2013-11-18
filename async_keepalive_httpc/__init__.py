import os
import json

VERSION = None

def __load_version():
    current_folder = os.path.abspath(
        os.path.dirname(__file__)
        )

    with open (os.path.join(current_folder, 'VERSION.json'), 'rb') as f:
        v = json.load(f)
        global VERSION
        VERSION = v['main']

__load_version()