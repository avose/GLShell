import wx

from glsPlaceHolder import glsPlaceHolder
from glsGraphPanel import glsGraphPanel
from glsSearch import  glsSearchResultListPopupMenu
from glsSearch import glsSearchResultPanel
from glsSearch import glsSearch
from glsEvents import glsEvents
from glsIcons import glsIcons

################################################################

class glsDataPanel(wx.Window):
    ID_START      = 1000
    ID_STOP       = 1001
    ID_RESCAN     = 1002
    ID_OPEN_DIR   = 1003
    ID_SEARCH     = 1004
    ID_SEARCH_OPT = 1005
    ID_SEL_ALL    = 1006
    ID_SEL_NONE   = 1007
    ID_SEL_IVRT   = 1008
    ID_SHOW_FILES = 1009
    ID_SHOW_DIRS  = 1010
    ID_EXIT       = 1011
    ICON_GRAPH     = 0
    ICON_SEARCH    = 1
    ICON_PLACEHLDR = 2
    def __init__(self, parent, terms_panel):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsDataPanel, self).__init__(parent, style=style)
        self.terms_panel = terms_panel
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnChangeTab)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
        tools = [ (self.ID_EXIT, "Close Tab", 'cross', self.OnToolCloseTab),
                  (self.ID_OPEN_DIR, "Open Directory", 'chart_organisation_add', self.OnToolOpenDir),
                  (self.ID_START, "Resume Layout", 'control_play_blue', self.OnToolStart),
                  (self.ID_STOP, "Pause Layout", 'control_pause_blue', self.OnToolStop),
                  (self.ID_SEARCH, "Search", 'magnifier', self.OnToolSearch),
                  (self.ID_SEARCH_OPT, "Custom Search", 'magnifier_zoom_in', self.OnToolSearchCustom),
                  (self.ID_RESCAN, "Rescan", 'arrow_refresh', self.OnToolRescan),
                  (self.ID_SEL_ALL, "Select All", 'chart_line_add', self.OnToolSelAll),
                  (self.ID_SEL_IVRT, "Select Inverse", 'chart_line', self.OnToolSelIvrt),
                  (self.ID_SEL_NONE, "Select None", 'chart_line_delete', self.OnToolSelNone),
                  (self.ID_SHOW_FILES, "Show Files", 'page', self.OnToolShowFiles),
                  (self.ID_SHOW_DIRS, "Hide Files", 'folder', self.OnToolShowDirs) ]
        for tool in tools:
            tid, text, icon, callback = tool
            self.toolbar.AddTool(tid, text, glsIcons.Get(icon), wx.NullBitmap,
                                 wx.ITEM_NORMAL, text, text, None)
            self.Bind(wx.EVT_TOOL, callback, id=tid)
        self.toolbar.Realize()
        box_main.Add(self.toolbar, 0, wx.EXPAND)
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(glsIcons.Get('chart_organisation'))
        self.image_list.Add(glsIcons.Get('magnifier'))
        self.image_list.Add(glsIcons.Get('error'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = []
        self.tabs_closing = []
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        wx.CallAfter(self.AddPlaceHolder)
        self.Show(True)
        return
    def AddDirTree(self, dirtree):
        self.RemovePlaceHolder()
        graph_panel = glsGraphPanel(self.notebook, dirtree, self.OnCloseTab)
        self.tabs.append(graph_panel)
        self.notebook.AddPage(graph_panel, " Graph '%s'"%(dirtree.name))
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_GRAPH)
        self.notebook.SetSelection(len(self.tabs)-1)
        graph_panel.StartGraph()
        self.EnableTools()
        return
    def GetDirTrees(self):
        return [ tab.dirtree for tab in self.tabs if isinstance(tab, glsGraphPanel) ]
    def AddSearch(self, search):
        self.RemovePlaceHolder()
        result_panel = glsSearchResultPanel(self.notebook, search, self.OnResultOpen,
                                            self.OnCloseTab)
        self.tabs.append(result_panel)
        label = " Search"
        if search.has_cont and search.has_name:
            label += " '%s' in"%search.cont_text
            label += " '%s'"%search.name_text
        elif search.has_name:
            label += " '%s'"%search.name_text
        else:
            label += " '%s'"%search.cont_text
        self.notebook.AddPage(result_panel, label)
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_SEARCH)
        self.notebook.SetSelection(len(self.tabs)-1)
        self.EnableTools()
        return
    def Search(self, opts):
        search = glsSearch(self.GetDirTrees(),
                           opts['name'], opts['name_regex'],
                           opts['contents'], opts['contents_regex'],
                           opts['files'], opts['dirs'])
        self.AddSearch(search)
        return
    def OnResultOpen(self, action_id, path, line=None):
        if action_id == glsSearchResultListPopupMenu.ID_OPEN_NEW:
            self.terms_panel.EditorStart(path)
            if line is not None:
                self.terms_panel.EditorLineSet(line)
        if action_id == glsSearchResultListPopupMenu.ID_OPEN:
            self.terms_panel.EditorFileOpen(path)
            if line is not None:
                self.terms_panel.EditorLineSet(line)
        return
    def CloseTabs(self):
        for closing in self.tabs_closing:
            for i,t in enumerate(self.tabs):
                if t == closing:
                    self.notebook.DeletePage(i)
                    self.notebook.SendSizeEvent()
                    self.tabs.remove(closing)
            self.tabs_closing.remove(closing)
        self.AddPlaceHolder()
        return
    def OnCloseTab(self, tab):
        if tab is not None and tab not in self.tabs_closing:
            self.tabs_closing.append(tab)
            wx.CallAfter(self.CloseTabs)
        return
    def RemovePlaceHolder(self):
        if len(self.tabs) != 1 or not isinstance(self.tabs[0], glsPlaceHolder):
            return
        self.notebook.DeletePage(0)
        self.notebook.SendSizeEvent()
        self.tabs.remove(self.tabs[0])
        return
    def AddPlaceHolder(self):
        if len(self.tabs):
            return
        placeholder = glsPlaceHolder(self.notebook, "All Data Tabs Are Closed")
        self.tabs.append(placeholder)
        self.notebook.AddPage(placeholder, " No Data")
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_PLACEHLDR)
        self.notebook.SetSelection(len(self.tabs)-1)
        self.EnableTools()
        return
    def GetCurrentTab(self):
        if len(self.tabs):
            tab = self.tabs[self.notebook.GetSelection()]
            if not isinstance(tab, glsPlaceHolder):
                return tab
        return None
    def EnableTools(self):
        return
        tab = self.GetCurrentTab()
        tools_graph = [ glsDataPanel.ID_RESCAN,
                        glsDataPanel.ID_SEL_ALL,
                        glsDataPanel.ID_SEL_NONE,
                        glsDataPanel.ID_SEL_IVRT,
                        glsDataPanel.ID_SHOW_FILES,
                        glsDataPanel.ID_SHOW_DIRS ]
        tools_always = [ glsDataPanel.ID_OPEN_DIR,
                         glsDataPanel.ID_SEARCH,
                         glsDataPanel.ID_SEARCH_OPT ]
        tools_results = []
        if tab is None:
            self.toolbar.EnableTool(glsDataPanel.ID_EXIT, False)
            graph = False
            result = False
        else:
            self.toolbar.EnableTool(glsDataPanel.ID_EXIT, True)
        if isinstance(tab, glsSearchResultPanel):
            graph = False
            result = True
        elif isinstance(tab, glsGraphPanel):
            graph = True
            result = False
        for tool in tools_results:
            self.toolbar.EnableTool(tool, result)
        for tool in tools_graph:
            self.toolbar.EnableTool(tool, graph)
        for tool in tools_always:
            self.toolbar.EnableTool(tool, True)
        return
    def OnChangeTab(self, event):
        self.EnableTools()
        return
    def OnToolStart(self, event):
        tab = self.GetCurrentTab()
        if isinstance(tab, glsGraphPanel):
            tab.Resume()
        return
    def OnToolStop(self, event):
        tab = self.GetCurrentTab()
        if isinstance(tab, glsGraphPanel):
            tab.Pause()
        return
    def OnToolRescan(self, event):
        print('rescan')
        return
    def OnToolOpenDir(self, event):
        evt = glsEvents.OpenDir(id=wx.ID_ANY, path=None)
        wx.PostEvent(self.Parent, evt)
        return
    def OnToolSearch(self, event):
        evt = glsEvents.Search(id=wx.ID_ANY, name=None, content=None)
        wx.PostEvent(self.Parent, evt)
        return
    def OnToolSearchCustom(self, event):
        evt = glsEvents.Search(id=wx.ID_ANY, name=None, content=None)
        wx.PostEvent(self.Parent, evt)
        return
    def OnToolSelAll(self, event):
        print('selall')
        return
    def OnToolSelNone(self, event):
        print('selnone')
        return
    def OnToolSelIvrt(self, event):
        print('selivrt')
        return
    def OnToolShowFiles(self, event):
        print('showfiles')
        return
    def OnToolShowDirs(self, event):
        print('showdirs')
        return
    def OnToolCloseTab(self, event):
        self.OnCloseTab(self.GetCurrentTab())
        return
    def OnClose(self, event=None):
        for tab in self.tabs:
            tab.OnClose()
        if event is not None:
            event.Skip()
        return

################################################################
