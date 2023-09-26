import os
import sys
import wx

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
        self.selected = False
        return
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

class glsDir(glsFSObj):
    def __init__(self, path):
        super().__init__(path)
        self.search_result = False
        self.selected = False
        return
    def __str__(self):
        return self.path + "@" + str(self.pos) + "+" + str(self.frc)

################################################################

class glsDirTree(glsFSObj, wx.EvtHandler):
    def __init__(self, path, settings):
        wx.EvtHandler.__init__(self)
        path = os.path.abspath(path)
        glsFSObj.__init__(self, path)
        self.settings = settings
        self.graph = fdpGraph(self.settings)
        self.thread = glsFDPThread(self.settings, self.graph, speed=0.01)
        self.rescan = False
        self.Bind(wx.EVT_FSWATCHER, self.OnFSChange)
        self.watcher_events = ( wx.FSW_EVENT_CREATE, wx.FSW_EVENT_DELETE,
                                wx.FSW_EVENT_RENAME )
        self.watcher = wx.FileSystemWatcher()
        self.watcher.SetOwner(self)
        self.ScanDir(self.path)
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
        new_graph = fdpGraph(self.settings)
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

################################################################
