import wx

from glsGraphPanel import glsGraphPanel

################################################################

class glsSearch():
    TYPE_FILES = 1
    TYPE_CONTENTS = 2
    def __init__(self, projects, text, search_type):
        self.projects = projects
        self.text = text
        self.search_type = search_type
        return
    def Start(self, result_callback):
        for project in self.projects:
            if self.search_type == self.TYPE_FILES:
                project.project.search_files(self.text)
            elif self.search_type == self.TYPE_CONTENTS:
                project.project.search_contents(self.text)
        return

################################################################

class glsSearchResultList(wx.VListBox):
    def __init__(self, parent):
        super(glsSearchResultList, self).__init__(parent)
        return
    def OnMeasureItem(self, index):
        return 30
    def OnDrawItem(self, dc, rect, index):
        dc.Clear()
        brush = wx.Brush((index,0,255/(index+1)))
        dc.SetBrush(brush)
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        return
    def OnDrawBackground(self, dc, rect, index):
        return
    def OnDrawSeparator(self, dc, rect, index):
        return

################################################################

class glsSearchResultPanel(wx.Window):
    def __init__(self, parent, search):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsSearchResultPanel, self).__init__(parent, style=style)
        self.search = search
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.vlb_results = glsSearchResultList(self)
        self.vlb_results.SetMinSize((200,200))
        box_main.Add(self.vlb_results, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.search.Start(self.OnSearchResult)
        self.vlb_results.SetItemCount(100)
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
