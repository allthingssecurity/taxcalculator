import os
import sys

# Ensure project root (containing 'app') is importable
ROOT = os.path.abspath(os.getcwd())
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

