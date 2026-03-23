import sys
import os
from pathlib import Path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent))
import utils
print(f"Utils file: {utils.__file__}")
from utils import InvalidConfigError
try:
    raise InvalidConfigError("test")
except InvalidConfigError:
    print("Caught InvalidConfigError")
except Exception as e:
    print(f"Caught other exception: {type(e)}")
