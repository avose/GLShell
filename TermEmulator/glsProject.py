import os
import sys
from fdpCanvas import fdpNode

class FileWalker:
    path = ""
    files = []
    dirs = []
    def __init__(self, path="."):
        self.path = path
        self.walk()

    def walk(self):
        for root, dirs, files in os.walk(self.path):
            for name in files:
                self.files.append(os.path.join(root, name))
            for name in dirs:
                self.dirs.append(os.path.join(root, name))
                
class glsFile(fdpNode):
    path = ""
    def __init__(self, path):
        super().__init__()
        self.path=path
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

class glsDir(fdpNode):
    path = ""
    def __init__(self, path):
        super().__init__()
        self.path=path
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)
        
class glsProject:
    path = ""
    files = []
    dirs = []
    walker = None
    def __init__(self, path="."):
        self.path = path
        self.walker = FileWalker(self.path)
        self.walker.walk()
        files = [ glsFile(p) for p in self.walker.files ]
        dirs = [ glsDir(p) for p in self.walker.dirs ]
        flist = [ str(f) for f in files ]
        print("Files: %s"%(flist))
        print("Dirs: %s"%(dirs))
