import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import PUBFILEDIR, EXPIREMINS

for f in os.listdir(PUBFILEDIR):
    f = os.path.join(PUBFILEDIR, f)
    if os.stat(f).st_mtime < (time.time() - (60 * EXPIREMINS)):
        if os.path.isfile(f):
            os.remove(f)
