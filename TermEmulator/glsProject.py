import os
import sys
from fdpCanvas import fdpNode
from fdpCanvas import fdpGraph

class glsFSObj(fdpNode):
    name = ""
    path = ""
    abspath = ""
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(self.path)
        self.abspath = os.path.abspath(self.path)
        super().__init__(self.abspath)
    
class glsFile(glsFSObj):
    def __init__(self, path):
        super().__init__(path)
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

class glsDir(glsFSObj):
    def __init__(self, path):
        super().__init__(path)
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

class glsRoot(glsFSObj):
    files = []
    dirs = []
    graph = fdpGraph()
    def __init__(self, path="."):
        super().__init__(path)
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

class glsProject:
    roots = []
    def __init__(self, paths=["."]):
        for p in paths:
            self.add_root(p)
    def print(self):
        for r in self.roots:
            for d in r.dirs:
                print(str(d))
            for f in r.files:
                print(str(f))
            for ek in r.graph.edges:
                print(str(ek))
            for n in r.graph.nodes:
                print(str(n))
    def add_root(self,path):
        root = glsRoot(path)
        self.roots.append(root)
    def forces_tick(self):
        for r in self.roots:
            r.graph.compute_forces()
            r.graph.apply_forces()

            
