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
    def __init__(self, nid, kind):
        self.nid = nid
        self.pos = (np.random.random(size=3) - 0.5) * 3
        self.kind = kind
        self.edges = {}
        return

class fdpGraph():
    def __init__(self, settings, kinds):
        self.settings = settings
        self.kinds = kinds
        self.kind_none = 0
        self.edges = OrderedDict()
        self.nodes = OrderedDict()
        self.endxs = OrderedDict()
        self.nndxs = OrderedDict()
        self.elist = []
        self.nlist = []
        self.np_edges = np.ndarray((0,2),dtype=np.intc)
        self.np_nodes = np.ndarray((0,3),dtype=np.single)
        self.np_ekinds = []
        self.np_nkinds = []
        for k in range(self.kinds):
            self.np_ekinds.append(np.ndarray((0, 2), dtype=np.intc))
            self.np_nkinds.append(np.ndarray((0, 1), dtype=np.intc))
        return
    def __contains__(self, key):
        if isinstance(key, tuple):
            tup = key
            if isinstance(key[0], fdpNode):
                tup = (tup[0].nid,tup[1])
            if isinstance(key[1], fdpNode):
                tup = (tup[0],tup[1].nid)
            return tup in self.edges
        elif isinstance(key, fdpNode):
            return key.nid in self.nodes
        elif isinstance(key, str):
            return key in self.nodes
        return
    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self.edges[key]
        if isinstance(key, fdpNode):
            return self.nodes[key.nid]
        return
    def add_node(self, node):
        if node not in self:
            ndx = len(self.nlist)
            self.nodes[node.nid] = node
            self.nndxs[node.nid] = ndx
            self.nlist.append(node)
            self.np_nodes = np.vstack( (self.np_nodes, node.pos) )
            self.np_nkinds[node.kind] = np.vstack( (self.np_nkinds[node.kind], ndx) )
        return
    def add_edge(self, edge):
        if edge in self:
            return
        if isinstance(edge[0], fdpNode):
            edge = (edge[0].nid, edge[1])
        if isinstance(edge[1], fdpNode):
            edge = (edge[0], edge[1].nid)
        ndx = len(self.elist)
        self.edges[edge] = edge
        self.endxs[edge] = ndx
        self.elist.append(edge)
        for nid in edge:
            self.nodes[nid].edges[edge] = edge
        edge_indices = ( self.nndxs[edge[0]], self.nndxs[edge[1]] )
        self.np_edges = np.vstack( (self.np_edges, edge_indices) )
        kind = self.nlist[edge_indices[0]].kind
        if kind != self.nlist[edge_indices[1]].kind:
            kind = self.kind_none
        self.np_ekinds[kind] = np.vstack( (self.np_ekinds[kind], edge_indices) )
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
    def forces_nodes(self, nodes, dists, vectors):
        dists = np.array(dists)
        dists[dists > 30.0] = 30.0
        dists[dists < 0.1] = 0.1
        dists = (dists**3)[:,:,np.newaxis]
        forces = np.divide(np.transpose(vectors, axes=(1,0,2)),
                           dists,
                           out=np.zeros_like(vectors),
                           where=dists!=0)
        forces_rows = np.sum(forces, axis=0)
        forces_cols = np.sum(forces, axis=1)
        return forces_rows - forces_cols
    def forces_edges(self, edges, dists, vectors, node_count):
        dists = dists**3
        dists[dists > 40.0] = 40.0
        eforces = vectors[edges[:,1], edges[:,0]]
        eforces *= dists[edges[:,1], edges[:,0], np.newaxis]
        forces = np.zeros( (node_count, 3) )
        for e in range(len(edges)):
            forces[edges[e,0]] += eforces[e]
            forces[edges[e,1]] -= eforces[e]
        return forces
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
                    nforces = self.forces_nodes(nodes, dists, vectors)
                    eforces = self.forces_edges(edges, dists, vectors, nodes.shape[0])
                    forces = nforces + eforces
                    forces[forces > 10] = 10
                    nodes += forces * self.speed
                    if dims == 2:
                        nodes[:,2] = 0
                    time = datetime.datetime.now() - start
                    time = time.total_seconds()
                max_force = np.amax(forces)
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
        self.kinds   = list(range(self.graph.kinds))
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
                    kinds = self.kinds
                    self.refresh = False
                else:
                    nodes = None
                    edges = None
                    kinds = None
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
    def set_kinds(self, kinds):
        with self.lock:
            self.kinds = kinds
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
