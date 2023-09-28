import wx

from glsGraphPanel import glsGraphPanel
from glsSearch import  glsSearchResultListPopupMenu
from glsSearch import glsSearchResultPanel
from glsSearch import glsSearch
from glsIcons import glsIcons

################################################################

class glsDataPanel(wx.Window):
    ID_OPEN_DIR   = 1000
    ID_SEARCH     = 1001
    ID_SEL_ALL    = 1002
    ID_SEL_NONE   = 1003
    ID_SEL_IVRT   = 1004
    ID_SHOW_FILES = 1005
    ID_SHOW_DIRS  = 1006
    def __init__(self, parent, settings, terms_panel):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsDataPanel, self).__init__(parent, style=style)
        self.settings = settings
        self.terms_panel = terms_panel
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_TOOL, self.OnOpenDir, id=self.ID_OPEN_DIR)
        self.Bind(wx.EVT_TOOL, self.OnSearch, id=self.ID_SEARCH)
        self.Bind(wx.EVT_TOOL, self.OnSelAll, id=self.ID_SEL_ALL)
        self.Bind(wx.EVT_TOOL, self.OnSelNone, id=self.ID_SEL_NONE)
        self.Bind(wx.EVT_TOOL, self.OnSelIvrt, id=self.ID_SEL_IVRT)
        self.Bind(wx.EVT_TOOL, self.OnShowFiles, id=self.ID_SHOW_FILES)
        self.Bind(wx.EVT_TOOL, self.OnShowDirs, id=self.ID_SHOW_DIRS)
        self.icons = glsIcons()
        box_main = wx.BoxSizer(wx.VERTICAL)
        toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
        toolbar.AddTool(self.ID_OPEN_DIR, "Open Directory",
                        self.icons.Get('chart_organisation_add'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Open Directory', "Open Directory", None)
        toolbar.AddTool(self.ID_SEARCH, "Search",
                        self.icons.Get('magnifier'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Search', "Search", None)
        toolbar.AddTool(self.ID_SEL_ALL, "Select All",
                        self.icons.Get('chart_line_add'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Select All', "Select All", None)
        toolbar.AddTool(self.ID_SEL_IVRT, "Select Inverse",
                        self.icons.Get('chart_line'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Select Inverse', "Select Inverse", None)
        toolbar.AddTool(self.ID_SEL_NONE, "Select None",
                        self.icons.Get('chart_line_delete'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Select None', "Select None", None)
        toolbar.AddTool(self.ID_SHOW_FILES, "Show Files",
                        self.icons.Get('script'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Show Files', "Show Files", None)
        toolbar.AddTool(self.ID_SHOW_DIRS, "Hide Files",
                        self.icons.Get('folder'), wx.NullBitmap,
                        wx.ITEM_NORMAL, 'Hide Files', "Hide Files", None)
        self.toolbar = toolbar
        self.toolbar.Realize()
        box_main.Add(self.toolbar, 0, wx.EXPAND)
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(self.icons.Get('chart_organisation'))
        self.image_list.Add(self.icons.Get('magnifier'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = []
        self.tabs_closing = []
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnOpenDir(self, event):
        print('open dir')
        return
    def OnSearch(self, event):
        print('search')
        return
    def OnSelAll(self, event):
        print('selall')
        return
    def OnSelNone(self, event):
        print('selnone')
        return
    def OnSelIvrt(self, event):
        print('selivrt')
        return
    def OnShowFiles(self, event):
        print('showfiles')
        return
    def OnShowDirs(self, event):
        print('showdirs')
        return
    def AddDirTree(self, dirtree):
        graph_panel = glsGraphPanel(self.notebook, dirtree, self.settings,
                                    self.OnCloseTab)
        self.tabs.append(graph_panel)
        self.notebook.AddPage(graph_panel, " Graph '%s'"%(dirtree.name))
        self.notebook.SetPageImage(len(self.tabs)-1, 0)
        self.notebook.SetSelection(len(self.tabs)-1)
        graph_panel.StartGraph()
        return
    def GetDirTrees(self):
        return [ tab for tab in self.tabs if isinstance(tab, glsGraphPanel) ]
    def AddSearch(self, search):
        result_panel = glsSearchResultPanel(self.notebook, search, self.OnResultOpen,
                                            self.OnCloseTab)
        self.tabs.append(result_panel)
        if search.search_type == search.TYPE_FILES:
            type_text = "Files"
        elif search.search_type == search.TYPE_CONTENTS:
            type_text = "Contents"
        self.notebook.AddPage(result_panel, " Search %s '%s'"%(type_text, search.text))
        self.notebook.SetPageImage(len(self.tabs)-1, 1)
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
        return
    def OnCloseTab(self, tab):
        if tab not in self.tabs_closing:
            self.tabs_closing.append(tab)
        wx.CallLater(10, self.CloseTabs)
        return
    def OnClose(self, event=None):
        for tab in self.tabs:
            tab.OnClose()
        if event is not None:
            event.Skip()
        return

################################################################
