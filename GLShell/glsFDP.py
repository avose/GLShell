from multiprocessing import Process, Queue
from collections import OrderedDict
from threading import Thread, Lock
from queue import Empty
from time import sleep
import numpy as np
import sys, math
import datetime

################################################################

class fdpNode():
    def __init__(self,id):
        self.id = id
        self.pos = (np.random.random(size=3) - 0.5) * 3
        self.frc = np.array([0,0,0], dtype=float)
        return

class fdpGraph():
    def __init__(self, settings):
        self.settings = settings
        self.nodes = OrderedDict()
        self.edges = OrderedDict()
        self.nndxs = OrderedDict()
        self.nlist = []
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
    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self.edges[key]
        if isinstance(key, fdpNode):
            return self.nodes[key.id]
        return
    def add_node(self, node):
        if node not in self:
            self.nodes[node.id] = node
            self.nndxs[node.id] = len(self.nlist)
            self.nlist.append(node)
            self.np_nodes = np.vstack( (self.np_nodes, node.pos) )
        return
    def add_edge(self, edge):
        if edge in self:
            return
        if isinstance(edge[0], fdpNode):
            edge = (edge[0].id, edge[1])
        if isinstance(edge[1], fdpNode):
            edge = (edge[0], edge[1].id)
        self.edges[(edge[0], edge[1])] = edge
        edge_indices = ( self.nndxs[edge[0]], self.nndxs[edge[1]] )
        self.np_edges = np.vstack( (self.np_edges, edge_indices) )
        return
    def set_np_nodes(self, np_nodes):
        self.np_nodes = np_nodes
        return
    def get_np_nodes(self):
        return self.np_nodes
    def get_np_edges(self):
        return self.np_edges

################################################################
    
class glsFDPProcess(Process):
    def __init__(self, settings, in_q, out_q, speed, steps=10, nice=1):
        Process.__init__(self)
        self.settings = settings
        self.dims = 3 if self.settings.Get('graph_3D') else 2
        self.in_q  = in_q
        self.out_q = out_q
        self.nice  = nice
        self.speed = speed
        self.steps = steps
        self.nodes = None
        self.edges = None
        self.done  = False
        self.converged = False
        return
    def run(self):
        while(True):
            cmd, nodes, edges, dims = self.in_q.get()
            if cmd == "stop":
                break
            if nodes is not None:
                self.nodes = np.array(nodes)
                self.converged = False
            if edges is not None:
                self.edges = np.array(edges)
                self.converged = False
            if self.dims != dims:
                self.converged = False
            nodes = self.nodes
            edges = self.edges
            start = datetime.datetime.now()
            if self.dims == 2 and dims == 3:
                nodes[:,2] = np.random.rand(nodes.shape[0])
            self.dims = dims
            if not self.converged:
                for step in range(self.steps):
                    # See: https://sparrow.dev/pairwise-distance-in-numpy/
                    vectors = nodes[:,None,:] - nodes[None,:,:]
                    dists = np.linalg.norm(vectors, axis=-1)
                    vectors *= 0.1
                    dists0 = np.array(dists)
                    dists0[dists0>30.0] = 30.0
                    dists0[dists0<0.1] = 0.1
                    dists0 = (dists0**3)[:,:,np.newaxis]
                    forces = np.divide(np.transpose(vectors,axes=(1,0,2)),
                                       dists0,
                                       out=np.zeros_like(vectors),
                                       where=dists0!=0)
                    aforces = np.zeros_like(nodes)
                    af_rows = np.sum(forces,axis=0)
                    af_cols = np.sum(forces,axis=1)
                    aforces += af_rows - af_cols
                    dists = dists**3
                    dists[dists>40.0] = 40.0
                    eforces = vectors[edges[:,1], edges[:,0]]
                    eforces *= dists[edges[:,1],edges[:,0], np.newaxis]
                    for e in range(len(edges)):
                        aforces[edges[e,0]] += eforces[e]
                        aforces[edges[e,1]] -= eforces[e]
                    aforces[aforces>10] = 10
                    nodes += aforces * self.speed
                    if dims == 2:
                        nodes[:,2] = 0
                    time = datetime.datetime.now() - start
                    time = time.total_seconds()
                max_force = np.amax(aforces)
                if max_force < 0.01:
                    self.converged = True
            if self.converged:
                self.out_q.put(None)
                sleep(1.0/50.0)
            else:
                self.out_q.put([np.array(nodes), time/self.steps, dims])
                sleep(self.nice/1000.0)
        return

################################################################

class glsFDPThread(Thread):
    def __init__(self, settings, graph, speed, nice=1):
        Thread.__init__(self)
        self.settings = settings
        self.dims = 3 if self.settings.Get('graph_3D') else 2
        self.graph   = graph
        self.speed   = speed
        self.nice    = nice
        self.done    = False
        self.refresh = True
        self.lock    = Lock()
        self.in_q    = Queue()
        self.out_q   = Queue()
        self.time    = 0
        self.proc = glsFDPProcess(self.settings, self.in_q, self.out_q, self.speed)
        self.proc.start()
        return
    def run(self):
        while not self.done:
            with self.lock:
                if self.refresh:
                    nodes = self.graph.get_np_nodes()
                    edges = self.graph.get_np_edges()
                    self.refresh = False
                else:
                    nodes = None
                    edges = None
            dims = 3 if self.settings.Get('graph_3D') else 2
            self.in_q.put(["run", nodes, edges, dims])
            data = False
            while not data:
                try:
                    response = self.out_q.get_nowait()
                    data = True
                except Empty:
                    sleep(self.nice/1000.0)
            if response is not None:
                nodes,time,dims = response
                with self.lock:
                    if not self.refresh:
                        self.graph.set_np_nodes(nodes)
                        self.time = time
                        self.dims = dims
                sleep(self.nice/1000.0)
            else:
                sleep(1/50.0)
        return
    def update(self, graph, locked=False):
        if not locked:
            with self.lock:
                self.graph = graph
                self.refresh = True
        else:
            self.graph = graph
            self.refresh = True
        return
    def get_time(self):
        with self.lock:
            return self.time
    def set_speed(self, speed):
        with self.lock:
            self.speed = speed
        return
    def stop(self):
        self.in_q.put(["stop", None, None, None])
        self.done = True
        return

################################################################
