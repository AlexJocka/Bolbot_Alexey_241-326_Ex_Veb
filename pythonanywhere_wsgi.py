import sys

path = '/home/YOUR_USERNAME/lab7/app'
if path not in sys.path:
    sys.path.insert(0, path)

from app import application
