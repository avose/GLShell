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
        self.Bind(wx.EVT_FSWATCHER, self.OnFSChange)
        self.watcher_events = { wx.FSW_EVENT_CREATE, wx.FSW_EVENT_DELETE,
                                wx.FSW_EVENT_RENAME }
        self.watcher = wx.FileSystemWatcher()
        self.watcher.SetOwner(self)
        self.AddDir(self.path)
        self.thread.start()
        return
    def AddDir(self, path):        
        path = os.path.abspath(path)
        self.watcher.AddTree(os.path.join(path, ""))
        with self.thread.lock:
            for root, dirs, files in os.walk(self.path):
                root_node = glsDir(root)
                if root_node not in self.graph:
                    self.graph.add_node(root_node)
                for name in files:
                    node = glsFile(os.path.join(root, name))
                    self.graph.add_node(node)
                    self.graph.add_edge( (root_node, node) )
                for name in dirs:
                    node = glsDir(os.path.join(root, name))
                    self.graph.add_node(node)
                    self.graph.add_edge( (root_node, node) )
        self.thread.update()
        return
    def AddFile(self, path):
        path = os.path.abspath(path)
        with self.thread.lock:
            if path in self.graph:
                return
            parent = os.path.dirname(path)
            self.graph.add_node(glsFile(path))
            self.graph.add_edge( (parent, path) )
        self.thread.update()
        return
    def AddPath(self, path):
        path = os.path.abspath(path)
        if os.path.isdir(path):
            self.AddDir(path)
        elif os.path.isfile(path):
            self.AddFile(path)
        return
    def DeletePath(self, path):
        path = os.path.abspath(path)
        with self.thread.lock:
            self.graph.remove_node(path)
        self.thread.update()
        return
    def OnFSChange(self, event):
        change_type = event.GetChangeType()
        if change_type not in self.watcher_events:
            return
        if change_type == wx.FSW_EVENT_CREATE:
            self.AddPath(event.GetPath())
        elif change_type == wx.FSW_EVENT_DELETE:
            self.DeletePath(event.GetPath())
        elif change_type == wx.FSW_EVENT_RENAME:
            self.DeletePath(event.GetPath())
            self.AddPath(event.GetNewPath())
        return

################################################################
