import wx

from glsIcons import glsIcons

################################################################

class glsSearchDialog(wx.Dialog):
    ID_CANCEL = 1000
    ID_SEARCH = 1001
    def __init__(self, parent):
        title = "Advanced Search"
        super(glsSearchDialog, self).__init__(parent, title=title)
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_panel = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self)
        font_fw = wx.Font(wx.FontInfo(11).FaceName("Monospace"))
        # Row One
        self.st_name = wx.StaticText(panel, wx.ID_ANY, "Search Name:")
        box_panel.Add(self.st_name, 0, wx.LEFT | wx.TOP | wx.RIGHT, 5)
        # Row Two
        self.tc_name = wx.TextCtrl(panel, wx.ID_ANY, size=(400,26))
        self.tc_name.SetFont(font_fw)
        box_panel.Add(self.tc_name, 1, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 5)
        # Row Three
        row3 = wx.GridSizer(1,4,5,5)
        self.rb_name_text = wx.RadioButton(panel, label='Text', style=wx.RB_GROUP)
        row3.Add(self.rb_name_text, 0, wx.ALIGN_CENTER)
        self.rb_name_regex = wx.RadioButton(panel, label='Regex')
        row3.Add(self.rb_name_regex, 0, wx.ALIGN_CENTER)
        self.cb_files = wx.CheckBox(panel, wx.ID_ANY, "Files")
        row3.Add(self.cb_files, 0, wx.ALIGN_CENTER)
        self.cb_files.SetValue(True)
        self.cb_dirs = wx.CheckBox(panel, wx.ID_ANY, "Directories")
        row3.Add(self.cb_dirs, 0, wx.ALIGN_CENTER)
        box_panel.Add(row3, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 5)
        # Row Four
        self.cb_contents = wx.CheckBox(panel, wx.ID_ANY, "Match Contents:")
        box_panel.Add(self.cb_contents, 0, wx.LEFT | wx.TOP | wx.RIGHT, 5)
        # Row Five
        self.tc_contents = wx.TextCtrl(panel, wx.ID_ANY, size=(400,26))
        self.tc_contents.SetFont(font_fw)
        box_panel.Add(self.tc_contents, 1, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 5)
        # Row Six
        row6 = wx.GridSizer(1,4,5,5)
        self.rb_contents_text = wx.RadioButton(panel, label='Text', style=wx.RB_GROUP)
        row6.Add(self.rb_contents_text, 0, wx.ALIGN_CENTER)
        self.rb_contents_regex = wx.RadioButton(panel, label='Regex')
        row6.Add(self.rb_contents_regex, 0, wx.ALIGN_CENTER)
        box_panel.Add(row6, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 5)
        # Row Seven
        row7 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(panel, wx.ID_ANY, "Cancel")
        self.btn_cancel.SetBitmap(glsIcons.Get('cross'))
        row7.Add(self.btn_cancel)
        self.btn_search = wx.Button(panel, wx.ID_ANY, "Search")
        self.btn_search.SetBitmap(glsIcons.Get('magnifier'))
        row7.Add(self.btn_search)
        box_panel.Add(row7, 0, wx.ALIGN_RIGHT)
        panel.SetSizerAndFit(box_panel)
        box_main.Add(panel, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.tc_contents.Enable(False)
        self.rb_contents_text.Enable(False)
        self.rb_contents_regex.Enable(False)
        self.btn_search.Enable(False)
        # Bind events.
        self.tc_name.Bind(wx.EVT_TEXT, self.OnName)
        self.cb_files.Bind(wx.EVT_CHECKBOX, self.OnFiles)
        self.cb_dirs.Bind(wx.EVT_CHECKBOX, self.OnDirs)
        self.cb_contents.Bind(wx.EVT_CHECKBOX, self.OnContents)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_search.Bind(wx.EVT_BUTTON, self.OnSearch)
        self.Show(True)
        return
    def OnName(self, event):
        if self.tc_name.GetValue() == "":
            self.btn_search.Enable(False)
        else:
            self.btn_search.Enable(True)
        return
    def OnFiles(self, event):
        if not self.cb_files.IsChecked() and not self.cb_dirs.IsChecked():
            self.cb_files.SetValue(True)
        return
    def OnDirs(self, event):
        if not self.cb_files.IsChecked() and not self.cb_dirs.IsChecked():
            self.cb_files.SetValue(True)
        return
    def OnContents(self, event):
        if self.cb_contents.IsChecked():
            self.tc_contents.Enable(True)
            self.rb_contents_text.Enable(True)
            self.rb_contents_regex.Enable(True)
        else:
            self.tc_contents.Enable(False)
            self.rb_contents_text.Enable(False)
            self.rb_contents_regex.Enable(False)
        return
    def OnCancel(self, event):
        if self.IsModal():
            self.EndModal(glsSearchDialog.ID_CANCEL)
        else:
            self.Close()
        return
    def OnSearch(self, event):
        if self.IsModal():
            self.EndModal(glsSearchDialog.ID_SEARCH)
        else:
            self.Close()
        return
    def SearchSettings(self):
        return { 'name': self.tc_name.GetValue(),
                 'name_regex': self.rb_name_regex.GetValue(),
                 'files': self.cb_files.IsChecked(),
                 'dirs': self.cb_dirs.IsChecked(),
                 'match_contents': self.cb_contents.IsChecked(),
                 'contents': self.tc_contents.GetValue(),
                 'contents_regex': self.rb_contents_regex.GetValue() }

################################################################
