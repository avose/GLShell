import wx

from glsIcons import glsIcons

################################################################

class glsToobarItem(wx.Window):
    def __init__(self, parent):
        style = wx.WANTS_CHARS
        super(glsToobarItem, self).__init__(parent,style=style)
        return

################################################################

class glsToolTextButton(glsToobarItem):
    def __init__(self, parent, label, icon, callback_search):
        super(glsToolTextButton, self).__init__(parent)
        self.callback_search = callback_search
        self.icon = icon
        self.icons = glsIcons()
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_row = wx.BoxSizer(wx.HORIZONTAL)
        self.tc_text = wx.TextCtrl(self, wx.ID_ANY, size=(200,-1),
                                   style=wx.TE_PROCESS_ENTER)
        self.tc_text.Bind(wx.EVT_TEXT_ENTER, self.__OnSearch)
        box_row.Add(self.tc_text, 1, wx.EXPAND | wx.LEFT, 5)
        self.bt_search = wx.Button(self, wx.ID_ANY, label)
        self.bt_search.SetBitmap(self.icons.Get(self.icon))
        self.bt_search.Bind(wx.EVT_BUTTON, self.__OnSearch)
        box_row.Add(self.bt_search, 0, wx.LEFT | wx.RIGHT, 5)
        box_main.Add(box_row, 0, wx.ALL, 0)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def __OnSearch(self, event):
        text = self.tc_text.GetValue()
        self.callback_search(text)
        return

################################################################

class glsToolSearchFiles(glsToolTextButton):
    def __init__(self, parent, callback_search):
        super(glsToolSearchFiles, self).__init__(parent, "Search Files",
                                                 'magnifier', self.OnSearch)
        self.callback_search = callback_search
        return
    def OnSearch(self, text):
        self.callback_search(text)
        return

class glsToolSearchContents(glsToolTextButton):
    def __init__(self, parent, callback_search):
        super(glsToolSearchContents, self).__init__(parent, "Search Contents",
                                                    'magnifier', self.OnSearch)
        self.callback_search = callback_search
        return
    def OnSearch(self, text):
        self.callback_search(text)
        return

################################################################

class glsToolOpenDir(glsToolTextButton):
    def __init__(self, parent, callback_opendir):
        super(glsToolOpenDir, self).__init__(parent, "Open Path",
                                                    'chart_organisation_add',
                                                    self.OnOpenDir)
        self.callback_opendir = callback_opendir
        return
    def OnOpenDir(self, text):
        self.callback_opendir(text)
        return

################################################################

class glsToolBarPopupMenu(wx.Menu):
    ID_MANAGE = 1000
    def __init__(self, parent):
        super(glsToolBarPopupMenu, self).__init__()
        self.icons = glsIcons()
        item = wx.MenuItem(self, self.ID_NEW_TERM, 'Manage Shortcuts')
        item.SetBitmap(self.icons.Get('cog'))
        self.Append(item)
        return

################################################################

class glsToolBar(wx.Window):
    def __init__(self, parent, settings, callback_searchfiles,
                 callback_searchcontents, callback_opendir):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsToolBar, self).__init__(parent,style=style)
        self.settings = settings
        self.callback_searchfiles = callback_searchfiles
        self.callback_searchcontents = callback_searchcontents
        self.callback_opendir = callback_opendir
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_tool = wx.BoxSizer(wx.HORIZONTAL)
        self.tools = [ glsToolOpenDir(self, self.callback_opendir),
                       glsToolSearchFiles(self, self.callback_searchfiles),
                       glsToolSearchContents(self, self.callback_searchcontents) ]
        for tool in self.tools:
            box_tool.Add(tool, 0, wx.EXPAND)
        box_main.Add(box_tool, 0, wx.ALIGN_RIGHT)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return

################################################################
