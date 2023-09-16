import re
import mmap
import wx
from threading import Thread, Lock
from multiprocessing import Process, Queue

from glsProject import glsFile
from glsGraphPanel import glsGraphPanel

################################################################

class glsSearchProcess(Process):
    def __init__(self, search, out_q):
        Process.__init__(self)
        self.search = search
        self.out_q = out_q
        self.done  = False
        return
    def run(self):
        for result in self.GetResults():
            if self.done:
                self.out_q.put(None)
                break
            self.out_q.put(result)
        self.out_q.put(None)
        return
    def GetResults(self):
        if self.search.search_type == self.search.TYPE_FILES:
            for pndx,project in enumerate(self.search.projects):
                for result in self.SearchFiles(project):
                    yield (pndx, result)
        elif self.search.search_type == self.search.TYPE_CONTENTS:
            for pndx,project in enumerate(self.search.projects):
                for result in self.SearchContents(project):
                    yield (pndx, result)
        return
    def SearchFiles(self, project):
        if self.search.text is None or self.search.text == "":
            return
        for nndx,node in enumerate(project.project.root.graph.nlist):
            if re.match(self.search.text, node.name):
                yield (nndx, node.name)
        return
    def SearchContents(self, project):
        if self.search.text is None or self.search.text == "":
            return
        for nndx,node in enumerate(project.project.root.graph.nlist):
            if not isinstance(node, glsFile):
                continue
            try:
                with open(node.abspath, 'rb', 0) as f:
                    contents = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                    if contents.find(bytes(self.search.text,"utf-8")) != -1:
                        yield (nndx, node.name)
            except:
                continue
        return

################################################################

class glsSearchThread(Thread):
    def __init__(self, search, callback):
        Thread.__init__(self)
        self.search = search
        self.callback = callback
        self.in_q = Queue()
        self.done = False
        self.proc = glsSearchProcess(self.search, self.in_q)
        self.proc.start()
        self.start()
        return
    def run(self):
        while not self.done:
            result = self.in_q.get()
            if result is None:
                self.done = True
                break
            self.search.AddResult(result)
            self.callback(result)
        return
    def stop(self):
        self.done = True
        return

################################################################

class glsSearch():
    TYPE_FILES = 1
    TYPE_CONTENTS = 2
    def __init__(self, projects, text, search_type):
        self.projects = projects
        self.text = text
        self.search_type = search_type
        self.results = []
        return
    def AddResult(self, result):
        self.results.append(result)
        return

################################################################

class glsSearchResultList(wx.VListBox):
    def __init__(self, parent, search):
        style = wx.LB_NEEDED_SB | wx.LB_MULTIPLE
        super(glsSearchResultList, self).__init__(parent, style=style)
        self.search = search
        self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        self.thread = glsSearchThread(search, self.OnSearchResult)
        return
    def OnMeasureItem(self, index):
        return 30
    def OnDrawItem(self, dc, rect, index):
        dc.Clear()
        pen = wx.Pen((0,0,255))
        dc.SetPen(pen)
        brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        dc.SetTextForeground((192,192,192))
        dc.SetFont(self.font)
        cw,ch = dc.GetTextExtent("X")
        text = str(self.search.results[index])
        dc.DrawText(text, rect[0], rect[1])
        return
    def OnDrawBackground(self, dc, rect, index):
        dc.Clear()
        pen = wx.Pen((0,0,255))
        dc.SetPen(pen)
        brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        return
    def OnDrawSeparator(self, dc, rect, index):
        return
    def OnSearchResult(self, result):
        self.SetItemCount(len(self.search.results))
        return

################################################################

class glsSearchResultPanel(wx.Window):
    def __init__(self, parent, search):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsSearchResultPanel, self).__init__(parent, style=style)
        self.search = search
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.vlb_results = glsSearchResultList(self, search)
        self.vlb_results.SetMinSize((200,200))
        box_main.Add(self.vlb_results, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnSearchResult(self):
        return

################################################################

class glsDataPanel(wx.Window):
    def __init__(self, parent, settings):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsDataPanel, self).__init__(parent, style=style)
        self.settings = settings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self)
        self.tabs = []
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def AddProject(self, project):
        graph_panel = glsGraphPanel(self.notebook, project, self.settings)
        self.tabs.append(graph_panel)
        self.notebook.AddPage(graph_panel, "Graph '%s'"%(project.name))
        graph_panel.StartGraph()
        return
    def GetProjects(self):
        return [ tab for tab in self.tabs if isinstance(tab, glsGraphPanel) ]
    def AddSearch(self, search):
        result_panel = glsSearchResultPanel(self.notebook, search)
        self.tabs.append(result_panel)
        self.notebook.AddPage(result_panel, "Search '%s'"%(search.text))
        return
    def SearchFiles(self, text):
        self.AddSearch(glsSearch(self.GetProjects(), text, glsSearch.TYPE_FILES))
        return
    def SearchContents(self, text):
        self.AddSearch(glsSearch(self.GetProjects(), text, glsSearch.TYPE_CONTENTS))
        return
    def OnClose(self, event):
        for tab in self.tabs:
            if isinstance(tab, glsGraphPanel):
                tab.OnClose(event)
        event.Skip()
        return

################################################################
