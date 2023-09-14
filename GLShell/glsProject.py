import re
import os
import sys
import mmap
from glsFDP import fdpNode
from glsFDP import fdpGraph
from glsFDP import glsFDPThread

################################################################

class glsFSObj(fdpNode):
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(self.path)
        self.abspath = os.path.abspath(self.path)
        super().__init__(self.abspath)
        return

################################################################
    
class glsFile(glsFSObj):
    def __init__(self, path):
        super().__init__(path)
        self.search_result = False
        return
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

class glsDir(glsFSObj):
    def __init__(self, path):
        super().__init__(path)
        self.search_result = False
        return
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

################################################################

class glsRoot(glsFSObj):
    def __init__(self, settings, path="."):
        path = os.path.abspath(path)
        super().__init__(path)
        self.settings = settings
        self.files = []
        self.dirs  = []
        self.graph = fdpGraph(self.settings)
        for root, dirs, files in os.walk(self.path):
            root_node = glsDir(root)
            for name in files:
                node = glsFile(os.path.join(root, name))
                self.files.append(node)
                self.graph.add_node(node)
                self.graph.add_edge( (root_node,node) )
            for name in dirs:
                node = glsDir(os.path.join(root, name))
                self.dirs.append(node)
                self.graph.add_node(node)
                self.graph.add_edge( (root_node,node) )
        return
    def search_files(self, text):
        for node in self.graph.nlist:
            if re.match(text, node.name):
                node.search_result = True
            else:
                node.search_result = False
        return
    def search_contents(self, text):
        for node in self.graph.nlist:
            if not isinstance(node, glsFile):
                continue
            with open(node.abspath, 'rb', 0) as f:
                contents = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                if contents.find(bytes(text,"utf-8")) != -1:
                    node.search_result = True
                else:
                    node.search_result = False
        return

################################################################

class glsProject:
    def __init__(self, settings, paths=["."]):
        self.settings = settings
        self.roots = []
        self.threads = []
        for p in paths:
            self.add_root(p)
        return
    def add_root(self, path):
        root = glsRoot(self.settings, path)
        self.roots.append(root)
        thread = glsFDPThread(self.settings, root.graph, speed=0.01)
        self.threads.append(thread)
        thread.start()
        return
    def search_files(self, text):
        for root in self.roots:
            root.search_files(text)
        return
    def search_contents(self, text):
        for root in self.roots:
            root.search_contents(text)
        return

################################################################
