from multiprocessing import Process, Queue
from threading import Thread, Lock
from queue import Empty
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
    np_nodes = np.ndarray((0,3),dtype=np.single)
    np_edges = np.ndarray((0,2),dtype=np.intc)
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.nlist = []
        self.nndxs = {}
        self.np_nodes = np.ndarray((0,3),dtype=np.single)
        self.np_edges = np.ndarray((0,2),dtype=np.intc)
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
            self.np_nodes = np.vstack( (self.np_nodes,node.pos) )
        return
    def add_edge(self,edge):
        for n in edge:
            self.add_node(n)
        if edge not in self:
            self.edges[(edge[0].id,edge[1].id)] = edge
            self.np_edges = np.vstack( (self.np_edges,
                                        (self.nndxs[edge[0].id],self.nndxs[edge[1].id])) )
        return
    def set_np_nodes(self,np_nodes):
        self.np_nodes = np_nodes
        return
    def get_np_nodes(self):
        return self.np_nodes
    def get_np_edges(self):
        return self.np_edges

################################################################
    
class glsFDPProcess(Process):
    in_q  = None
    out_q = None
    speed = 0.1
    nice  = 0
    steps = 10
    nodes = None
    edges = None
    done  = False
    def __init__(self, in_q, out_q, speed, steps=10, nice=1):
        Process.__init__(self)
        self.in_q  = in_q
        self.out_q = out_q
        self.nice  = nice
        self.speed = speed
        self.steps = steps
        self.nodes = None
        self.edges = None
        self.done  = False
        return
    def run(self):
        while(True):
            cmd, nodes, edges = self.in_q.get()
            if cmd == "stop":
                break
            if nodes is not None:
                self.nodes = np.array(nodes)
            if edges is not None:
                self.edges = np.array(edges)
            nodes = self.nodes
            edges = self.edges
            start = datetime.datetime.now()
            for step in range(self.steps):
                # See: https://sparrow.dev/pairwise-distance-in-numpy/
                vectors = nodes[:,None,:] - nodes[None,:,:]
                dists = np.linalg.norm(vectors, axis=-1)
                vectors *= 0.1
                dists2 = np.square(dists)[:,:,np.newaxis]
                forces = np.divide(np.transpose(vectors,axes=(1,0,2)),
                                   dists2,
                                   out=np.zeros_like(vectors),
                                   where=dists2!=0)
                aforces = np.zeros_like(nodes)
                af_rows = np.sum(forces,axis=0)
                af_cols = np.sum(forces,axis=1)
                aforces += af_rows - af_cols
                eforces = vectors[edges[:,1], edges[:,0]] * dists[edges[:,1], edges[:,0], np.newaxis]
                #aforces[edges[:,0]] += eforces
                #aforces[edges[:,1]] -= eforces
                for e in range(len(edges)):
                    ai = edges[e][0]
                    bi = edges[e][1]
                    f = eforces[e]
                    aforces[ai] += f
                    aforces[bi] -= f
                nodes += aforces * self.speed
                time = datetime.datetime.now() - start
                time = time.total_seconds()
            self.out_q.put([np.array(nodes),time/self.steps])
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
    first = True
    def __init__(self, graph, speed, nice=1, proc=True):
        Thread.__init__(self)
        self.graph = graph
        self.speed = speed
        self.nice  = nice
        self.done  = False
        self.first = True
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
                if self.first:
                    with self.lock:
                        nodes = self.graph.get_np_nodes()
                        edges = self.graph.get_np_edges()
                else:
                    nodes = None
                    edges = None
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