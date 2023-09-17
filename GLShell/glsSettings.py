import os
import wx
import json

from glsKeyPress import glsKeyPress

################################################################

class glsSettings():
    path       = "~/.glshell"
    shell_path = "/bin/bash"
    shell_args = ""
    term_type  = "linux"
    term_color = True
    term_fgcolor = (192,192,192)
    term_bgcolor = (0,0,0)
    term_wchars = "-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-z0123456789,./?%&#:_=+@~"
    graph_3D = True
    edit_path = "/usr/bin/emacs"
    edit_args = "-nw"
    edit_open = "\x18\x06{FILE}\x0a"
    edit_line = "\x1b\x78goto-line\x0a{LINE}\x0a"
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
                self.graph_3D = d['graph_3D'] if 'graph_3D' in d else self.graph_3D
                self.edit_path = d['edit_path'] if 'edit_path' in d else self.edit_path
                self.edit_args = d['edit_args'] if 'edit_args' in d else self.edit_args
                self.edit_open = d['edit_open'] if 'edit_open' in d else self.edit_open
                self.edit_line = d['edit_line'] if 'edit_line' in d else self.edit_line
        except:
            self.Save()
            pass
        self.OnChange()
        return
    def Save(self,path=None):
        if path is not None:
            self.path = path
        conf_path = os.path.abspath(os.path.expanduser(self.path))
        try:
            with open(conf_path,"w") as conf:
                d = {'shell_path': self.shell_path,
                     'shell_args': self.shell_args,
                     'term_type': self.term_type,
                     'term_color': self.term_color,
                     'term_fgcolor': self.term_fgcolor,
                     'term_bgcolor': self.term_bgcolor,
                     'term_wchars': self.term_wchars,
                     'graph_3D': self.graph_3D,
                     'edit_path': self.edit_path,
                     'edit_args': self.edit_args,
                     'edit_open': self.edit_open,
                     'edit_line': self.edit_line }
                json.dump(d, conf, indent=2)
        except:
            pass
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

class KeyPressesFrame(wx.Frame):
    def __init__(self, parent, callback,
                 style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="Keypress Recorder", style=style)
        self.callback = callback
        self.panel = wx.Panel(self)
        self.panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.panel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.panel.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.panel.SetFocus()
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_panel = wx.BoxSizer(wx.VERTICAL)
        # Row 0.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_keys_label = wx.StaticText(self.panel, wx.ID_ANY, "Key Presses:")
        row0.Add(self.st_keys_label, 0, wx.LEFT | wx.RIGHT, 5)
        self.tc_keys = wx.TextCtrl(self.panel, wx.ID_ANY, style=wx.TE_READONLY,
                                   size=(200,-1))
        self.tc_keys.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.tc_keys.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row0.Add(self.tc_keys, 1, wx.EXPAND | wx.ALL)
        box_panel.Add(row0, 1, wx.ALIGN_CENTER | wx.ALL, 50)
        self.panel.SetSizerAndFit(box_panel)
        # Row 1.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(self, wx.ID_ANY, "Cancel")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_cancel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_cancel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_cancel)
        self.btn_clear = wx.Button(self, wx.ID_ANY, "Clear")
        self.btn_clear.Bind(wx.EVT_BUTTON, self.OnClear)
        self.btn_clear.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_clear.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_clear)
        self.btn_ok = wx.Button(self, wx.ID_ANY, "OK")
        self.btn_ok.Bind(wx.EVT_BUTTON, self.OnOK)
        self.btn_ok.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_ok.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_ok)
        box_main.Add(self.panel, 1, wx.EXPAND)
        box_main.Add(row1, 0, wx.ALIGN_RIGHT)
        self.SetSizerAndFit(box_main)
        self.keys_down = {}
        self.keypress = glsKeyPress(self.keys_down)
        self.keys = ""
        self.Show(True)
        return
    def OnSetFocus(self, event):
        return
    def OnKillFocus(self, event):
        self.panel.SetFocus()
        return
    def OnClear(self, event):
        self.keys = ""
        self.tc_keys.SetValue(self.keys)
        self.panel.SetFocus()
        return
    def OnOK(self, event):
        self.callback(self.keys)
        self.Destroy()
        return
    def OnCancel(self, event):
        self.Destroy()
        return
    def OnKeyDown(self, event):
        key = event.GetKeyCode()
        self.keys_down[key] = True
        seq = self.keypress.KeyCodeToSequence(key)
        if seq is not None:
            self.keys += seq
            self.tc_keys.SetValue(self.keys)
        event.Skip()
        return
    def OnKeyUp(self, event):
        key = event.GetKeyCode()
        if key in self.keys_down:
            del self.keys_down[event.GetKeyCode()]
        event.Skip()
        return

################################################################

class TabTerminal(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        self.settings = settings
        vbox = wx.BoxSizer(wx.VERTICAL)
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_path = wx.StaticText(self, wx.ID_ANY, "Program Path:")
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
    def Load(self):
        self.tc_shellpath.SetValue(self.settings.shell_path)
        self.tc_shellargs.SetValue(self.settings.shell_args)
        self.tc_termtype.SetValue(self.settings.term_type)
        self.cb_termcolor.SetValue(self.settings.term_color)
        self.cp_fgcolor.SetColour(self.settings.term_fgcolor)
        self.cp_bgcolor.SetColour(self.settings.term_bgcolor)
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
        return

################################################################

class TabGraph(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        self.settings = settings
        main_box = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        lblList = ['3D', '2D']
        self.rbox = wx.RadioBox(self, label='Graph Rendering',
                                pos=(80,10), choices=lblList ,
                                majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        if self.settings.graph_3D:
            self.rbox.SetSelection(0)
        else:
            self.rbox.SetSelection(1)
        row.Add(self.rbox, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        main_box.Add(row, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        self.SetSizerAndFit(main_box)
        return
    def Load(self):
        if self.settings.graph_3D:
            dims = "3D"
        else:
            dims = "2D"            
        self.rbox.SetStringSelection(dims)
        return
    def Save(self):
        dims = self.rbox.GetStringSelection()
        if dims == "3D":
            self.settings.graph_3D = True
        else:
            self.settings.graph_3D = False
        return

################################################################

class TabEditor(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        self.settings = settings
        main_box = wx.BoxSizer(wx.VERTICAL)
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_path = wx.StaticText(self, wx.ID_ANY, "Editor Path:")
        row0.Add(self.st_edit_path, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_path = wx.TextCtrl(self, wx.ID_ANY)
        edit_path = os.path.abspath(settings.edit_path)
        self.tc_path.SetValue(edit_path)
        row0.Add(self.tc_path, 1, wx.ALL)
        row0.AddSpacer(5)
        main_box.Add(row0, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_edit_args, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_args = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_args.SetValue(str(settings.edit_args))
        row1.Add(self.tc_args, 1, wx.ALL)
        row1.AddSpacer(5)
        main_box.Add(row1, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row 2.
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_args = wx.StaticText(self, wx.ID_ANY, "Editor Commands:")
        row2.Add(self.st_edit_args, 0, wx.LEFT | wx.RIGHT, 5)
        main_box.Add(row2, 0,  wx.BOTTOM, 5)
        # Row three.
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open = wx.Button(self, wx.ID_ANY, "Open File")
        self.btn_open.Bind(wx.EVT_BUTTON, self.OnOpenKeys)
        row3.Add(self.btn_open, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_open = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.tc_open.SetValue(str(settings.edit_open))
        row3.Add(self.tc_open, 1, wx.EXPAND | wx.RIGHT, 5)
        main_box.Add(row3, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row four.
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_line = wx.Button(self, wx.ID_ANY, "Goto Line")
        self.btn_line.Bind(wx.EVT_BUTTON, self.OnLineKeys)
        row4.Add(self.btn_line, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_line = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.tc_line.SetValue(str(settings.edit_line))
        row4.Add(self.tc_line, 1, wx.EXPAND | wx.RIGHT, 5)
        main_box.Add(row4, 0, wx.EXPAND | wx.BOTTOM, 5)
        self.SetSizerAndFit(main_box)
        return
    def OnOpenKeys(self, event):
        self.open_keys = KeyPressesFrame(self, self.SetOpenKeys)
        return
    def OnLineKeys(self, event):
        self.line_keys = KeyPressesFrame(self, self.SetLineKeys)
        return
    def SetOpenKeys(self, keys):
        self.tc_open.SetValue(keys)
        return
    def SetLineKeys(self, keys):
        self.tc_line.SetValue(keys)
        return
    def Load(self):
        self.tc_path.SetValue(self.settings.edit_path)
        self.tc_args.SetValue(self.settings.edit_args)
        self.tc_open.SetValue(self.settings.edit_open)
        self.tc_line.SetValue(self.settings.edit_line)
    def Save(self):
        edit_path               = self.tc_path.GetValue()
        self.settings.edit_path = os.path.abspath(edit_path)
        self.settings.edit_args = self.tc_args.GetValue()
        self.settings.edit_open = self.tc_open.GetValue()
        self.settings.edit_line = self.tc_line.GetValue()
        return

################################################################

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
        self.tab_edit = TabEditor(self.nb, self.settings)
        self.nb.AddPage(self.tab_term, "Terminal")
        self.nb.AddPage(self.tab_graph, "FDP Graph")
        self.nb.AddPage(self.tab_edit, "Term Editor")
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
        self.btn_apply = wx.Button(self, wx.ID_ANY, "Apply")
        self.btn_apply.Bind(wx.EVT_BUTTON, self.OnApply)
        row_bottom.Add(self.btn_apply)
        main_box.Add(row_bottom, 0)
        # Set main box as frame sizer.
        self.SetSizerAndFit(main_box)
        self.Show(True)
        return
    def OnLoad(self, event):
        self.parent.settings.Load()
        self.tab_term.Load()
        self.tab_graph.Load()
        self.tab_edit.Load()
        return
    def OnSave(self, event):
        self.tab_term.Save()
        self.tab_graph.Save()
        self.tab_edit.Save()
        self.parent.settings.Save()
        self.settings.OnChange()
        return
    def OnApply(self, event):
        self.tab_term.Save()
        self.tab_graph.Save()
        self.tab_edit.Save()
        self.settings.OnChange()
        self.OnClose(event)
        return
    def OnCancel(self, event):
        self.OnClose(event)
        return
    def OnClose(self, event):
        self.parent.settings_frame = None
        self.Destroy()
        return

################################################################
