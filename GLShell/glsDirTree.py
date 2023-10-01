import os
import sys
import wx
import numpy as np

from glsLog import glsLog
from glsFDP import fdpNode
from glsFDP import fdpGraph
from glsFDP import glsFDPThread

################################################################

class glsFSObj(fdpNode):
    def __init__(self, path, kind):
        self.path = path
        self.name = os.path.basename(self.path)
        self.abspath = os.path.abspath(self.path)
        super().__init__(self.abspath, kind)
        return

################################################################
    
class glsFile(glsFSObj):
    def __init__(self, path):
        super().__init__(path, glsDirTree.KIND_FILE)
        self.search_result = False
        self.selected = False
        return
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

class glsDir(glsFSObj):
    def __init__(self, path):
        super().__init__(path, glsDirTree.KIND_DIR)
        self.search_result = False
        self.selected = False
        return
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

################################################################

class glsDirTree(wx.EvtHandler):
    KIND_NONE   = 0
    KIND_DIR    = 1
    KIND_FILE   = 2
    KIND_SELECT = 3
    KIND_RESULT = 4
    KINDS       = 5
    def __init__(self, path, settings):
        wx.EvtHandler.__init__(self)
        path = os.path.abspath(os.path.expanduser(path))
        self.path = path
        self.name = os.path.basename(self.path)
        self.abspath = os.path.abspath(self.path)
        glsLog.add("Directory Tree: "+self.abspath)
        self.settings = settings
        self.graph = fdpGraph(self.settings, self.KINDS)
        self.thread = glsFDPThread(self.settings, self.graph, speed=0.01)
        self.rescan = False
        self.Bind(wx.EVT_FSWATCHER, self.OnFSChange)
        self.watcher_events = ( wx.FSW_EVENT_CREATE, wx.FSW_EVENT_DELETE,
                                wx.FSW_EVENT_RENAME )
        self.watcher = wx.FileSystemWatcher()
        self.watcher.SetOwner(self)
        self.ScanDir(self.path)
        glsLog.add("Directory Tree: %d directories"%
                   len(self.graph.np_nkinds[self.KIND_DIR]))
        glsLog.add("Directory Tree: %d files"%
                   len(self.graph.np_nkinds[self.KIND_FILE]))
        self.thread.start()
        return
    def ScanDir(self, path):
        path = os.path.abspath(path)
        if os.path.exists(path):
            try:
                self.watcher.AddTree(os.path.join(path, ""))
            except:
                pass
        else:
            return
        nodes = []
        edges = []
        for root, dirs, files in os.walk(self.path):
            root = os.path.abspath(root)
            nodes.append(glsDir(root))
            for name in files:
                node = glsFile(os.path.join(root, name))
                nodes.append(node)
                edges.append((root, node))
            for name in dirs:
                node = glsDir(os.path.join(root, name))
                nodes.append(node)
                edges.append((root, node))
        new_graph = fdpGraph(self.settings, self.KINDS)
        for node in nodes:
            new_graph.add_node(node)
        for edge in edges:
            new_graph.add_edge(edge)
        with self.thread.lock:
            for n in self.graph.nodes.keys():
                if n in new_graph.nndxs:
                    old_pos = self.graph.np_nodes[self.graph.nndxs[n]]
                    new_graph.nodes[n].pos = old_pos
                    new_graph.np_nodes[new_graph.nndxs[n]] = old_pos
            self.thread.update(new_graph, locked=True)
            self.graph = new_graph
        self.rescan = False
        return
    def OnFSChange(self, event):
        change_type = event.GetChangeType()
        if change_type in self.watcher_events:
            if not self.rescan:
                self.rescan = True
                wx.CallLater(10, self.ScanDir, self.path)
            return
        return
    def SelectAdd(self, selected):
        if selected is None or len(selected) == 0:
            return
        with self.thread.lock:
            graph = self.thread.graph
            kinds = graph.np_nkinds[glsDirTree.KIND_SELECT]
            selected = np.reshape(np.array(selected, dtype=np.intc), (len(selected),1))
            kinds = np.vstack( (kinds, selected) )
            kinds = np.unique(kinds)
            kinds = np.reshape(kinds, (len(kinds), 1))
            graph.np_nkinds[glsDirTree.KIND_SELECT] = kinds
        return
    def SelectToggle(self, selected):
        if selected is None or len(selected) == 0:
            return
        with self.thread.lock:
            graph = self.thread.graph
            kinds = graph.np_nkinds[glsDirTree.KIND_SELECT]
            for s in selected:
                ndx = np.where(kinds == s)[0]
                if len(ndx):
                    kinds = np.delete(kinds, ndx)
                else:
                    kinds = np.vstack( (kinds, s) )
            kinds = np.unique(kinds)
            kinds = np.reshape(kinds, (len(kinds), 1))
            graph.np_nkinds[glsDirTree.KIND_SELECT] = kinds
        return
    def SelectAll(self):
        with self.thread.lock:
            graph = self.thread.graph
            kinds = np.array(range(len(self.graph.nlist)), dtype=np.intc)
            kinds = np.reshape(kinds, (len(kinds), 1))
            graph.np_nkinds[glsDirTree.KIND_SELECT] = kinds
        return
    def SelectNone(self):
        with self.thread.lock:
            graph = self.thread.graph
            graph.np_nkinds[glsDirTree.KIND_SELECT] = np.ndarray((0, 1), dtype=np.intc)
        return
    def SelectInverse(self):
        with self.thread.lock:
            graph = self.thread.graph
            kinds = graph.np_nkinds[glsDirTree.KIND_SELECT]
            every = np.array(range(len(self.graph.nlist)), dtype=np.intc)
            kinds = np.delete(every, kinds)
            kinds = np.reshape(kinds, (len(kinds), 1))
            graph.np_nkinds[glsDirTree.KIND_SELECT] = kinds
    def SetKinds(self, kinds):
        self.thread.set_kinds(kinds)
        return

################################################################
