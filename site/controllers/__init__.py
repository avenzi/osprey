#------------------------------------------
# Loads all the controllers (all files in this module)
#------------------------------------------

import os
import glob
__all__ = [os.path.basename(
    f)[:-3] for f in glob.glob(os.path.dirname(__file__) + "/*.py")]

print("Loaded Controllers")