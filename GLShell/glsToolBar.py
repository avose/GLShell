import wx

################################################################

class glsToobarItem(wx.Window):
    def __init__(self, parent):
        style = wx.WANTS_CHARS
        super(glsToobarItem, self).__init__(parent,style=style)
        return

################################################################

class glsToolSearch(glsToobarItem):
    def __init__(self, parent, label, callback):
        super(glsToolSearch, self).__init__(parent)
        self.callback = callback
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_row = wx.BoxSizer(wx.HORIZONTAL)
        self.tc_text = wx.TextCtrl(self, wx.ID_ANY, size=(200,-1),
                                   style=wx.TE_PROCESS_ENTER)
        self.tc_text.Bind(wx.EVT_TEXT_ENTER, self.__OnSearch)
        box_row.Add(self.tc_text, 1, wx.EXPAND | wx.LEFT, 5)
        self.bt_search = wx.Button(self, wx.ID_ANY, label)
        self.bt_search.Bind(wx.EVT_BUTTON, self.__OnSearch)
        box_row.Add(self.bt_search, 0, wx.LEFT | wx.RIGHT, 5)
        box_main.Add(box_row, 0, wx.ALL, 0)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def __OnSearch(self, event):
        text = self.tc_text.GetValue()
        self.callback(text)
        return

################################################################

class glsToolSearchFiles(glsToolSearch):
    def __init__(self, parent):
        super(glsToolSearchFiles, self).__init__(parent, "Search Files",
                                                 self.OnSearch)
        return
    def OnSearch(self, text):
        self.Parent.Parent.OnSearchFiles(text)
        return

class glsToolSearchContents(glsToolSearch):
    def __init__(self, parent):
        super(glsToolSearchContents, self).__init__(parent, "Search Contents",
                                                    self.OnSearch)
        return
    def OnSearch(self, text):
        self.Parent.Parent.OnSearchContents(text)
        return

################################################################

class glsToolBarPopupMenu(wx.Menu):
    ID_MANAGE = 1000
    def __init__(self, parent):
        super(glsToolBarPopupMenu, self).__init__()
        item = wx.MenuItem(self, self.ID_NEW_TERM, 'Manage Shortcuts')
        self.Append(item)
        return


################################################################

class glsToolBar(wx.Window):
    def __init__(self, parent, settings):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsToolBar, self).__init__(parent,style=style)
        self.settings = settings
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_tool = wx.BoxSizer(wx.HORIZONTAL)
        self.tools = [ glsToolSearchFiles(self), glsToolSearchContents(self) ]
        for tool in self.tools:
            box_tool.Add(tool, 0, wx.EXPAND)
        box_main.Add(box_tool, 0, wx.ALIGN_RIGHT)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return

################################################################
