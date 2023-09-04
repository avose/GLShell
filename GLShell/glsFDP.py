from multiprocessing import Process, Queue
from threading import Thread, Lock
from queue import Empty
from copy import deepcopy
from time import sleep
import numpy as np
import sys, math
import datetime

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
    nlist = []
    nndxs = {}
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
            self.nndxs[node.id] = len(self.nlist)
            self.nlist.append(node)
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
        for ai in range(len(self.nodes)):
            for bi in range(ai+1,len(self.nodes)):
                a = self.nlist[ai]
                b = self.nlist[bi]
                v = np.subtract(b.pos,a.pos)
                d = np.linalg.norm(v)
                f = 0.1 * (v / (d*d))
                #f = (v / (d*d))
                #if ai == bi-1:
                #    print("n:",v,d,f)
                a.frc -= f
                b.frc += f
        # Spring force for edges.
        for k0,k1 in self.edges:
            a = self.nodes[k0]
            b = self.nodes[k1]
            v = np.subtract(b.pos,a.pos)
            d = np.linalg.norm(v)
            f = 0.1 * (v * d)
            a.frc += f
            b.frc -= f
            #print("e:",f)
        return
    def apply_forces(self,speed=0.1):
        for n in self.nodes:
            node = self.nodes[n]
            node.pos += speed * node.frc
            node.frc *= 0
        return
    def tick(self,speed=0.1):
        self.compute_forces()
        self.apply_forces(speed)
        return
    def set_np_nodes(self,np_nodes):
        if np_nodes.shape[0] != len(self.nodes):
            raise Exception("Process: Node count missmatch!")
        for i,n in enumerate(self.nodes):
            self.nodes[n].pos = np_nodes[i]
        return np_nodes
    def get_np_nodes(self):
        np_nodes = np.ndarray((len(self.nodes),3),
                              dtype=np.single)
        for i,n in enumerate(self.nlist):
            np_nodes[i] = n.pos
        return np_nodes
    def get_np_edges(self):
        np_edges = np.ndarray((len(self.edges),2),
                              dtype=np.intc)
        for i,e in enumerate(self.edges):
            np_edges[i][0] = self.nndxs[e[0]]
            np_edges[i][1] = self.nndxs[e[1]]
        return np_edges

################################################################
    
class glsFDPProcess(Process):
    in_q  = None
    out_q = None
    speed = 0.1
    nice  = 0
    steps = 10
    def __init__(self, in_q, out_q, speed, steps=10, nice=1):
        Process.__init__(self)
        self.in_q  = in_q
        self.out_q = out_q
        self.nice  = nice
        self.speed = speed
        self.steps = steps
        self.done  = False
        return
    def run(self):
        while(True):
            cmd, nodes, edges = self.in_q.get()
            if cmd == "stop":
                break
            start = datetime.datetime.now()
            for step in range(self.steps):
                # See: https://sparrow.dev/pairwise-distance-in-numpy/
                #vectors = nodes[:,None,:] - nodes[None,:,:]
                #distances = np.linalg.norm(vectors, axis=-1)
                #dist2 = np.square(distances)
                forces = np.zeros_like(nodes)
                for ai in range(nodes.shape[0]):
                    for bi in range(ai+1,nodes.shape[0]):
                        v = np.subtract(nodes[bi],nodes[ai])
                        d = np.linalg.norm(v)
                        f = 0.1 * (v / np.square(d))
                        #v = vectors[ai][bi]
                        #d = np.linalg.norm(v)
                        #f = 0.1 * (v / dist2[ai][bi])
                        forces[ai] -= f
                        forces[bi] += f
                for e in range(len(edges)):
                    ai = edges[e][0]
                    bi = edges[e][1]
                    v = np.subtract(nodes[bi],nodes[ai])
                    d = np.linalg.norm(v)
                    f = 0.1 * (v * d)
                    forces[ai] += f
                    forces[bi] -= f
                nodes += forces * self.speed
                #nodes = np.array(nodes)
                time = datetime.datetime.now() - start
                time = time.total_seconds()
            self.out_q.put([nodes,time/self.steps])
            sleep(self.nice/1000.0)
        return

################################################################

class glsFDPThread(Thread):
    graph = None
    lock  = None
    speed = 0.1
    nice  = 10
    time  = 0
    done  = False
    proc  = False
    in_q  = None
    out_q = None
    def __init__(self, graph, speed, nice=1, proc=True):
        Thread.__init__(self)
        self.graph = graph
        self.speed = speed
        self.nice  = nice
        self.done  = False
        self.lock  = Lock()
        if proc:
            self.in_q  = Queue()
            self.out_q = Queue()
            self.proc = glsFDPProcess(self.in_q, self.out_q, self.speed)
            self.proc.start()
        return
    def run(self):
        while(not self.done):
            if self.proc:
                with self.lock:
                    nodes = self.graph.get_np_nodes()
                    edges = self.graph.get_np_edges()
                self.in_q.put(["run",nodes,edges])
                data = False
                while(not data):
                    try:
                        nodes,time = self.out_q.get_nowait()
                        data = True
                    except Empty:
                        sleep(self.nice/1000.0)
                with self.lock:
                    self.graph.set_np_nodes(nodes)
                    self.time = time
            else:
                with self.lock:
                    start = datetime.datetime.now()
                    self.graph.tick(speed=self.speed)
                    time = datetime.datetime.now() - start
                    self.time = time.total_seconds()
            sleep(self.nice/1000.0)
        return
    def get_time(self):
        with self.lock:
            return self.time
    def set_speed(self,speed):
        with self.lock:
            self.speed = speed
        return
    def get_graph(self):
        with self.lock:
            return self.graph
        return
    def stop(self):
        if self.proc:
            self.in_q.put(["stop",None,None])
        self.done = True
        return
