import os
import wx
import json

################################################################

class glsSettings():
    path       = "~/.glshell"
    shell_path = "/bin/bash"
    shell_args = "-l"
    term_type  = "linux"
    term_color = True
    term_fgcolor = (192,192,192)
    term_bgcolor = (0,0,0)
    term_wchars = "-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-z0123456789,./?%&#:_=+@~"
    def __init__(self):
        self.watchers = []
        return
    def Load(self, path=None):
        if path is not None:
            self.path = path
        conf_path = os.path.abspath(os.path.expanduser(self.path))
        try:
            with open(conf_path,"r") as conf:
                d = json.load(conf)
                self.shell_path = d['shell_path'] if 'shell_path' in d else self.shell_path
                self.shell_args = d['shell_args'] if 'shell_args' in d else self.shell_args
                self.term_type = d['term_type'] if 'term_type' in d else self.term_type
                self.term_color = d['term_color'] if 'term_color' in d else self.term_color
                self.term_fgcolor = d['term_fgcolor'] if 'term_fgcolor' in d else self.term_fgcolor
                self.term_gbcolor = d['term_bgcolor'] if 'term_bgcolor' in d else self.term_bgcolor
                self.term_wchars = d['term_wchars'] if 'term_wchars' in d else self.term_wchars
        except:
            pass
        self.OnChange()
        return
    def Save(self,path=None):
        if path is not None:
            self.path = path
        conf_path = os.path.abspath(os.path.expanduser(self.path))
        with open(conf_path,"w") as conf:
            d = {'shell_path': self.shell_path,
                 'shell_args': self.shell_args,
                 'term_type': self.term_type,
                 'term_color': self.term_color,
                 'term_fgcolor': self.term_fgcolor,
                 'term_bgcolor': self.term_bgcolor,
                 'term_wchars': self.term_wchars }
            json.dump(d, conf, indent=2)
        return
    def OnChange(self):
        # Call this method if settings have changed.
        for watcher in self.watchers:
            watcher(self)
        return
    def AddWatcher(self, callback):
        self.watchers.append(callback)
        return
    def RemoveWatcher(self, callback):
        if callback in self.watchers:
            self.watchers.remove(callback)
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
        row0.Add(self.st_shell_path, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_shellpath = wx.TextCtrl(self, wx.ID_ANY)
        shell_path = os.path.abspath(settings.shell_path)
        self.tc_shellpath.SetValue(shell_path)
        row0.Add(self.tc_shellpath, 1, wx.ALIGN_CENTER | wx.ALL)
        row0.AddSpacer(5)
        vbox.Add(row0, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_shell_args, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_shellargs = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_shellargs.SetValue(str(settings.shell_args))
        row1.Add(self.tc_shellargs, 1, wx.ALIGN_CENTER | wx.ALL)
        row1.AddSpacer(5)
        vbox.Add(row1, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row two.
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_term_type = wx.StaticText(self, wx.ID_ANY, "Type ($TERM):")
        row2.Add(self.st_term_type, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_termtype = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_termtype.SetValue(str(settings.term_type))
        row2.Add(self.tc_termtype, 1, wx.ALIGN_CENTER | wx.ALL)
        vbox.Add(row2, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row three.
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb_termcolor = wx.CheckBox(self, wx.ID_ANY, "Support Text Color")
        self.cb_termcolor.SetValue(settings.term_color)
        row3.Add(self.cb_termcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        row2.AddSpacer(5)
        vbox.Add(row3, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row four is a 2x2 grid.
        grid2 = wx.GridSizer(2,2,5,5)
        self.st_fgcolor = wx.StaticText(self, wx.ID_ANY, "Foreground Color:")
        grid2.Add(self.st_fgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.cp_fgcolor = wx.ColourPickerCtrl(self)
        self.cp_fgcolor.SetColour(settings.term_fgcolor)
        grid2.Add(self.cp_fgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.st_bgcolor = wx.StaticText(self, wx.ID_ANY, "Backround Color:")
        grid2.Add(self.st_bgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.cp_bgcolor = wx.ColourPickerCtrl(self)
        self.cp_bgcolor.SetColour(settings.term_bgcolor)
        grid2.Add(self.cp_bgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)        
        vbox.Add(grid2, 0, wx.BOTTOM, 5)
        # Set vertical box as panel sizer.
        self.SetSizerAndFit(vbox)
        return
    def Save(self):
        shell_path               = self.tc_shellpath.GetValue()
        self.settings.shell_path = os.path.abspath(shell_path)
        self.settings.shell_args = self.tc_shellargs.GetValue()
        self.settings.term_type  = self.tc_termtype.GetValue()
        self.settings.term_color = self.cb_termcolor.IsChecked()
        color = self.cp_fgcolor.GetColour()
        self.settings.term_fgcolor = (color.GetRed(), color.GetGreen(), color.GetBlue())
        color = self.cp_bgcolor.GetColour()
        self.settings.term_bgcolor = (color.GetRed(), color.GetGreen(), color.GetBlue())
        self.settings.OnChange()
        return

class TabGraph(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        main_box = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.msg = wx.StaticText(self, -1, "Settings for force-directed placement graph.")
        row.Add(self.msg, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        main_box.Add(row, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        self.SetSizerAndFit(main_box)
        return
    def Save(self):
        return

class SettingsFrame(wx.Frame):
    def __init__(self, parent, settings,
                 style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="Settings", style=style)
        self.parent = parent
        self.settings = settings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Create panel and notebook on the panel.
        main_box = wx.BoxSizer(wx.VERTICAL)
        self.nb = wx.Notebook(self)
        self.tab_term = TabTerminal(self.nb, self.settings)
        self.tab_graph = TabGraph(self.nb, self.settings)
        self.nb.AddPage(self.tab_term, "Terminal")
        self.nb.AddPage(self.tab_graph, "FDP Graph")
        main_box.Add(self.nb, 1, wx.EXPAND | wx.TOP)
        # Create buttons.
        row_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(self, wx.ID_ANY, "Cancel")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        row_bottom.Add(self.btn_cancel)
        self.btn_load = wx.Button(self, wx.ID_ANY, "Load")
        self.btn_load.Bind(wx.EVT_BUTTON, self.OnLoad)
        row_bottom.Add(self.btn_load)
        self.btn_save = wx.Button(self, wx.ID_ANY, "Save")
        self.btn_save.Bind(wx.EVT_BUTTON, self.OnSave)
        row_bottom.Add(self.btn_save)
        self.btn_ok = wx.Button(self, wx.ID_ANY, "Apply")
        self.btn_ok.Bind(wx.EVT_BUTTON, self.OnApply)
        row_bottom.Add(self.btn_ok)
        main_box.Add(row_bottom, 0)
        # Set main box as frame sizer.
        self.SetSizerAndFit(main_box)
        self.Show(True)
        return
    def OnLoad(self, event):
        self.parent.settings.Load()
        return
    def OnSave(self, event):
        self.tab_term.Save()
        self.tab_graph.Save()
        self.parent.settings.Save()
        return
    def OnApply(self, event):
        self.tab_term.Save()
        self.tab_graph.Save()
        self.OnClose(event)
        return
    def OnCancel(self, event):
        self.OnClose(event)
        return
    def OnClose(self, event):
        self.parent.settings_frame = None
        self.Destroy()
        return
