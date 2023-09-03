import os
import wx
import json

################################################################

class glsSettings():
    path       = "~/.glshell"
    shell_path = "/bin/bash"
    shell_args = "-l"
    term_rows  = 24
    term_cols  = 80
    term_color = True
    def __init__(self):
        return
    def Load(self,path=None):
        if path is not None:
            self.path = path
        conf_path = os.path.abspath(os.path.expanduser(self.path))
        with open(conf_path,"r") as conf:
            data = json.load(conf)
            self.shell_path = data['shell_path'] if 'shell_path' in data else self.shell_path
            self.shell_args = data['shell_args'] if 'shell_args' in data else self.shell_args
            self.term_rows  = data['term_rows']  if 'term_rows'  in data else self.term_rows
            self.term_cols  = data['term_cols']  if 'term_cols'  in data else self.term_cols
            self.term_color = data['term_color'] if 'term_color' in data else self.term_color
        return
    def Save(self,path=None):
        if path is not None:
            self.path = path
        conf_path = os.path.abspath(os.path.expanduser(self.path))
        with open(conf_path,"w") as conf:
            data = {'shell_path': self.shell_path,
                    'shell_args': self.shell_args,
                    'term_rows':  self.term_rows,
                    'term_cols':  self.term_cols,
                    'term_color': self.term_color}
            json.dump(data, conf, indent=2)
        return

################################################################

class TabTerminal(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        self.settings = settings
        vbox = wx.BoxSizer(wx.VERTICAL)
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_path = wx.StaticText(self, wx.ID_ANY, "Program path:")
        row0.Add(self.st_shell_path, 0, wx.ALIGN_CENTER | wx.LEFT, 10)
        row0.AddSpacer(10)
        self.tc_shellpath = wx.TextCtrl(self, wx.ID_ANY)
        shell_path = os.path.abspath(settings.shell_path)
        self.tc_shellpath.SetValue(shell_path)
        row0.Add(self.tc_shellpath, 1, wx.ALIGN_CENTER)
        vbox.Add(row0, 0, wx.EXPAND | wx.HORIZONTAL | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_shell_args, 0, wx.ALIGN_CENTER | wx.LEFT, 10)
        row1.AddSpacer(10)
        self.tc_shellargs = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_shellargs.SetValue(str(settings.shell_args))
        row1.Add(self.tc_shellargs, 1, wx.ALIGN_CENTER)
        vbox.Add(row1, 0, wx.EXPAND | wx.HORIZONTAL | wx.TOP | wx.BOTTOM, 5)
        # Row two.
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_termrows = wx.StaticText(self, wx.ID_ANY, "Terminal Size, Rows:")
        row2.Add(self.st_termrows, 0, wx.ALIGN_CENTER | wx.LEFT, 10)
        row2.AddSpacer(10)
        self.tc_termrows = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_termrows.SetValue(str(settings.term_rows))
        row2.Add(self.tc_termrows, 1, wx.ALIGN_CENTER)
        self.st_termcols = wx.StaticText(self, wx.ID_ANY, "Columns:")
        row2.Add(self.st_termcols, 0, wx.ALIGN_CENTER | wx.LEFT, 10)
        row2.AddSpacer(10)
        self.tc_termcols = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_termcols.SetValue(str(settings.term_cols))
        row2.Add(self.tc_termcols, 1, wx.ALIGN_CENTER)
        vbox.Add(row2, 0, wx.EXPAND | wx.VERTICAL | wx.BOTTOM, 5)
        # Row three.
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb_termcolor = wx.CheckBox(self, wx.ID_ANY, "Support Text Color")
        self.cb_termcolor.SetValue(settings.term_color)
        row3.Add(self.cb_termcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 10)
        vbox.Add(row3, 0, wx.EXPAND | wx.VERTICAL | wx.BOTTOM, 5)
        # Set vertical box as panel sizer.
        self.SetSizer(vbox)
        return
    def Save(self):
        shell_path               = self.tc_shellpath.GetValue()
        self.settings.shell_path = os.path.abspath(shell_path)
        self.settings.shell_args = self.tc_shellargs.GetValue()
        self.settings.term_rows  = int(self.tc_termrows.GetValue())
        self.settings.term_cols  = int(self.tc_termcols.GetValue())
        self.settings.term_color = self.cb_termcolor.IsChecked()
        return

class TabGraph(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        wx.StaticText(self, -1, "Settings for force-directed placement graph.", (40, 40))
        return
    def Save(self):
        return

class PageDynamic(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        wx.StaticText(self, -1, "This is a Dynamic object", (60, 60))
        return

class SettingsFrame(wx.Frame):
    def __init__(self, parent, settings,
                 size=(520, 240), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="Settings", size=size, style=style)
        self.parent = parent
        self.settings = settings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Create vertical sizer for settings (top) and buttons (bottom).
        vbox = wx.BoxSizer(wx.VERTICAL)
        # Create panel and notebook on the panel.
        p = wx.Panel(self)
        self.nb = wx.Notebook(p)
        self.tab_term = TabTerminal(self.nb, self.settings)
        self.tab_graph = TabGraph(self.nb, self.settings)
        self.nb.AddPage(self.tab_term, "Terminal")
        self.nb.AddPage(self.tab_graph, "FDP Graph")
        vbox.Add(self.nb, 1, wx.EXPAND | wx.TOP)
        # Create buttons.
        row_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(p, wx.ID_ANY, "Cancel")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        row_bottom.Add(self.btn_cancel, 1, wx.RIGHT)
        self.btn_load = wx.Button(p, wx.ID_ANY, "Load")
        self.btn_load.Bind(wx.EVT_BUTTON, self.OnLoad)
        row_bottom.Add(self.btn_load, 1, wx.RIGHT)
        self.btn_save = wx.Button(p, wx.ID_ANY, "Save")
        self.btn_save.Bind(wx.EVT_BUTTON, self.OnSave)
        row_bottom.Add(self.btn_save, 1, wx.RIGHT)
        self.btn_ok = wx.Button(p, wx.ID_ANY, "Ok")
        self.btn_ok.Bind(wx.EVT_BUTTON, self.OnOk)
        row_bottom.Add(self.btn_ok, 1, wx.RIGHT)
        vbox.Add(row_bottom, 1, wx.ALIGN_RIGHT)
        # Set vertical box as panel sizer.
        p.SetSizer(vbox)
        return
    def OnLoad(self, event):
        self.parent.settings.Load()
        return
    def OnSave(self, event):
        self.tab_term.Save()
        self.tab_graph.Save()
        self.parent.settings.Save()
        return
    def OnOk(self, event):
        self.OnSave(event)
        self.OnClose(event)
        return
    def OnCancel(self, event):
        self.OnClose(event)
        return
    def OnClose(self, event):
        self.parent.settings_frame = None
        self.Destroy()
        return
    def dynamic_tab(self, event):
        dynamic_page = PageDynamic(self.nb)
        self.nb.AddPage(dynamic_page, "Page Dynamic")
        return
