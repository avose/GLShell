import os
import sys


class glsFile:
    path = ""

class glsProject:
    files = []
    

class FileWalker:
    path = "."
    def __init__(self, path="."):
        self.path = path
        self.walk()

    def walk(self):
        for root, dirs, files in os.walk(self.path):
            for name in files:
                print(os.path.join(root, name))
            for name in dirs:
                print(os.path.join(root, name))
                
