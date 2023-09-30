import wx

from glsPlaceHolder import glsPlaceHolder
from glsGraphPanel import glsGraphPanel
from glsSearch import  glsSearchResultListPopupMenu
from glsSearch import glsSearchResultPanel
from glsSearch import glsSearch
from glsIcons import glsIcons

################################################################

class glsDataPanel(wx.Window):
    ID_RESCAN     = 1000
    ID_OPEN_DIR   = 1001
    ID_SEARCH     = 1002
    ID_SEARCH_OPT = 1003
    ID_SEL_ALL    = 1004
    ID_SEL_NONE   = 1005
    ID_SEL_IVRT   = 1006
    ID_SHOW_FILES = 1007
    ID_SHOW_DIRS  = 1008
    ID_EXIT       = 1009
    ICON_GRAPH     = 0
    ICON_SEARCH    = 1
    ICON_PLACEHLDR = 2
    def __init__(self, parent, settings, terms_panel):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsDataPanel, self).__init__(parent, style=style)
        self.settings = settings
        self.terms_panel = terms_panel
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.icons = glsIcons()
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
        tools = [ (self.ID_EXIT, "Close Tab", 'cross', self.OnToolCloseTab),
                  (self.ID_RESCAN, "Rescan Directory Tree", 'arrow_refresh', self.OnToolRescan),
                  (self.ID_OPEN_DIR, "Open Directory", 'chart_organisation_add', self.OnToolOpenDir),
                  (self.ID_SEARCH, "Search", 'magnifier', self.OnToolSearch),
                  (self.ID_SEARCH_OPT, "Custom Search", 'magnifier_zoom_in', self.OnToolSearchCustom),
                  (self.ID_SEL_ALL, "Select All", 'chart_line_add', self.OnToolSelAll),
                  (self.ID_SEL_IVRT, "Select Inverse", 'chart_line', self.OnToolSelIvrt),
                  (self.ID_SEL_NONE, "Select None", 'chart_line_delete', self.OnToolSelNone),
                  (self.ID_SHOW_FILES, "Show Files", 'page', self.OnToolShowFiles),
                  (self.ID_SHOW_DIRS, "Hide Files", 'folder', self.OnToolShowDirs) ]
        for tool in tools:
            tid, text, icon, callback = tool
            self.toolbar.AddTool(tid, text, self.icons.Get(icon), wx.NullBitmap,
                                 wx.ITEM_NORMAL, text, text, None)
            self.Bind(wx.EVT_TOOL, callback, id=tid)
        self.toolbar.Realize()
        box_main.Add(self.toolbar, 0, wx.EXPAND)
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(self.icons.Get('chart_organisation'))
        self.image_list.Add(self.icons.Get('magnifier'))
        self.image_list.Add(self.icons.Get('error'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = []
        self.tabs_closing = []
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnToolRescan(self, event):
        print('rescan')
        return
    def OnToolOpenDir(self, event):
        print('open dir')
        return
    def OnToolSearch(self, event):
        print('search')
        return
    def OnToolSearchCustom(self, event):
        print('search custom')
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
        print('close tab')
        return
    def AddDirTree(self, dirtree):
        self.RemovePlaceHolder()
        graph_panel = glsGraphPanel(self.notebook, dirtree, self.settings,
                                    self.OnCloseTab)
        self.tabs.append(graph_panel)
        self.notebook.AddPage(graph_panel, " Graph '%s'"%(dirtree.name))
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_GRAPH)
        self.notebook.SetSelection(len(self.tabs)-1)
        graph_panel.StartGraph()
        return
    def GetDirTrees(self):
        return [ tab for tab in self.tabs if isinstance(tab, glsGraphPanel) ]
    def AddSearch(self, search):
        self.RemovePlaceHolder()
        result_panel = glsSearchResultPanel(self.notebook, search, self.OnResultOpen,
                                            self.OnCloseTab)
        self.tabs.append(result_panel)
        if search.search_type == search.TYPE_FILES:
            type_text = "Files"
        elif search.search_type == search.TYPE_CONTENTS:
            type_text = "Contents"
        self.notebook.AddPage(result_panel, " Search %s '%s'"%(type_text, search.text))
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_SEARCH)
        self.notebook.SetSelection(len(self.tabs)-1)
        return
    def SearchFiles(self, text):
        self.AddSearch(glsSearch(self.GetDirTrees(), text, glsSearch.TYPE_FILES))
        return
    def SearchContents(self, text):
        self.AddSearch(glsSearch(self.GetDirTrees(), text, glsSearch.TYPE_CONTENTS))
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
        if tab not in self.tabs_closing:
            self.tabs_closing.append(tab)
        wx.CallLater(10, self.CloseTabs)
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
        return
    def OnClose(self, event=None):
        for tab in self.tabs:
            tab.OnClose()
        if event is not None:
            event.Skip()
        return

################################################################
