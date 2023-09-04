from itertools import product
import numpy as np
import sys, math

class fdpNode():
    pos = np.array([0,0,0], dtype=float)
    frc = np.array([0,0,0], dtype=float)
    id  = ""
    def __init__(self,id):
        self.pos = np.random.random(size=3)
        self.frc = np.array([0,0,0], dtype=float)
        self.pos[2] = 0.0
        self.id = id
        return

class fdpGraph():
    nodes = {}
    edges = {}
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        return
    def __contains__(self, key):
        if isinstance(key, tuple):
            tup = key
            if isinstance(key[0], fdpNode):
                tup = (tup[0].id,tup[1])
            if isinstance(key[1], fdpNode):
                tup = (tup[0],tup[1].id)
            return tup in self.edges
        elif isinstance(key, fdpNode):
            return key.id in self.nodes
        elif isinstance(key, str):
            return key in self.nodes
        return
    def add_node(self,node):
        if node not in self:
            self.nodes[node.id] = node
        return
    def add_edge(self,edge):
        for n in edge:
            self.add_node(n)
        if edge not in self:
            self.edges[(edge[0].id,edge[1].id)] = edge
        return
    def compute_forces(self):
        for k in self.nodes:
            n = self.nodes[k]
            n.pos[2] = 0
        # Anti-gravity force between node pairs.
        for k0,k1 in product(self.nodes,self.nodes):
            if k0 == k1:
                continue
            a = self.nodes[k0]
            b = self.nodes[k1]
            v = np.subtract(b.pos,a.pos)
            d = np.linalg.norm(v)
            f = 0.1 * (v / (d*d))
            a.frc -= f
            b.frc += f
        # Spring force for edges (non-linear).
        for k0,k1 in self.edges:
            a = self.nodes[k0]
            b = self.nodes[k1]
            v = np.subtract(b.pos,a.pos)
            d = np.linalg.norm(v)
            f = 0.1 * (v * d)
            a.frc += f
            b.frc -= f
        return
    def apply_forces(self,speed=1.0):
        for n in self.nodes:
            node = self.nodes[n]
            node.pos += speed * node.frc
            node.frc *= 0
        return
    def tick(self,speed=1.0):
        self.compute_forces()
        self.apply_forces(speed)
        return
