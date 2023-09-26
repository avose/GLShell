import os
import wx
import json

from glsFontDialog import glsFontDialog
from glsKeyPress import glsKeyPress
from glsIcons import glsIcons

################################################################

class glsSettings():
    __settings = { "path": "~/.glshell",
                   "shell_path": "/bin/bash",
                   "shell_args": "",
                   "term_type": "linux",
                   "term_color": True,
                   "term_fgcolor": (192,192,192),
                   "term_bgcolor": (0,0,0),
                   "term_wchars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"\
                                  "abcdefghijklmnopqrstuvwxyz"\
                                  "-z0123456789,./?%&#:_=+@~",
                   "term_font": "Monospace",
                   "term_font_size": 11,
                   "graph_3D": True,
                   "graph_font": "Monospace",
                   "graph_font_size": 10,
                   "edit_path": "/usr/bin/emacs",
                   "edit_args": "-nw",
                   "edit_open": "\x18\x06{FILE}\x0a",
                   "edit_line": "\x1b\x78goto-line\x0a{LINE}\x0a" }
    def __init__(self):
        self.watchers = []
        self.Reset()
        return
    def Reset(self):
        self.__settings = dict(glsSettings.__settings)
        self.OnChange()
        return
    def Load(self, path=None):
        if path is not None:
            self.Set('path', path)
        conf_path = os.path.abspath(os.path.expanduser(self.Get('path')))
        try:
            with open(conf_path,"r") as conf:
                d = json.load(conf)
                for key in self.__settings:
                    self.__settings[key] = d[key] if key in d else self.Get(key)
        except:
            self.Save()
            pass
        self.OnChange()
        return
    def Save(self,path=None):
        if path is not None:
            self.Set('path', path)
        conf_path = os.path.abspath(os.path.expanduser(self.Get('path')))
        try:
            with open(conf_path,"w") as conf:
                json.dump(self.__settings, conf, indent=2)
        except:
            pass
        return
    def Get(self, key):
        if key in self.__settings:
            return self.__settings[key]
        return None
    def Set(self, key, value):
        self.__settings[key] = value
        self.OnChange()
        return value
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
        self.icons = glsIcons()
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(self.icons.Get('keyboard'))
        self.SetIcon(self.icon)
        self.panel = wx.Panel(self)
        self.panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.panel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.panel.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
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
        self.btn_cancel.SetBitmap(self.icons.Get('cross'))
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_cancel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_cancel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_cancel)
        self.btn_clear = wx.Button(self, wx.ID_ANY, "Clear")
        self.btn_clear.SetBitmap(self.icons.Get('arrow_undo'))
        self.btn_clear.Bind(wx.EVT_BUTTON, self.OnClear)
        self.btn_clear.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_clear.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_clear)
        self.btn_ok = wx.Button(self, wx.ID_ANY, "OK")
        self.btn_ok.SetBitmap(self.icons.Get('tick'))
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
    def OnClose(self, event=None):
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
        shell_path = os.path.abspath(settings.Get('shell_path'))
        self.tc_shellpath.SetValue(shell_path)
        row0.Add(self.tc_shellpath, 1, wx.ALIGN_CENTER | wx.ALL)
        row0.AddSpacer(5)
        vbox.Add(row0, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_shell_args, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_shellargs = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_shellargs.SetValue(str(settings.Get('shell_args')))
        row1.Add(self.tc_shellargs, 1, wx.ALIGN_CENTER | wx.ALL)
        row1.AddSpacer(5)
        vbox.Add(row1, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row two.
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_term_type = wx.StaticText(self, wx.ID_ANY, "Type ($TERM):")
        row2.Add(self.st_term_type, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_termtype = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_termtype.SetValue(str(settings.Get('term_type')))
        row2.Add(self.tc_termtype, 1, wx.ALIGN_CENTER | wx.ALL)
        vbox.Add(row2, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row three.
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb_termcolor = wx.CheckBox(self, wx.ID_ANY, "Support Text Color")
        self.cb_termcolor.SetValue(settings.Get('term_color'))
        row3.Add(self.cb_termcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        row2.AddSpacer(5)
        vbox.Add(row3, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row four is a 2x2 grid.
        grid2 = wx.GridSizer(2,2,5,5)
        self.st_fgcolor = wx.StaticText(self, wx.ID_ANY, "Foreground Color:")
        grid2.Add(self.st_fgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.cp_fgcolor = wx.ColourPickerCtrl(self)
        self.cp_fgcolor.SetColour(settings.Get('term_fgcolor'))
        grid2.Add(self.cp_fgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.st_bgcolor = wx.StaticText(self, wx.ID_ANY, "Backround Color:")
        grid2.Add(self.st_bgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.cp_bgcolor = wx.ColourPickerCtrl(self)
        self.cp_bgcolor.SetColour(settings.Get('term_bgcolor'))
        grid2.Add(self.cp_bgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)        
        vbox.Add(grid2, 0, wx.BOTTOM, 5)
        # Row five.
        btn_font = wx.Button(self, wx.ID_ANY, "Select Terminal Font")
        btn_font.Bind(wx.EVT_BUTTON, self.OnFontDialog)
        vbox.Add(btn_font, 0, wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 5)
        # Row six.
        p_sample = wx.Panel(self, style=wx.RAISED_BORDER)
        p_sample.SetBackgroundColour((255,255,255))
        self.st_sample = wx.StaticText(p_sample, -1, "Font Sample Text",
                                       size=(-1, 64))
        self.SetFontSelection(self.settings.Get('term_font'),
                              self.settings.Get('term_font_size'))
        box_samp = wx.BoxSizer(wx.VERTICAL)
        box_samp.Add(self.st_sample, 0, wx.EXPAND | wx.ALL, 5)
        p_sample.SetSizerAndFit(box_samp)
        vbox.Add(p_sample, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        # Set vertical box as panel sizer.
        self.SetSizerAndFit(vbox)
        return
    def OnFontDialog(self, event):
        self.font_dialog = glsFontDialog(self, self.SetFontSelection)
        return
    def SetFontSelection(self, name, size):
        self.font_name = name
        self.font_size = size
        self.st_sample.SetLabel(name+" Sample Text")
        font = wx.Font(self.font_size, family=wx.DEFAULT,
                       style=wx.NORMAL, weight=wx.NORMAL, underline=False,
                       faceName=self.font_name)
        self.st_sample.SetFont(font)
        self.Layout()
        self.Fit()
        return
    def Load(self):
        self.tc_shellpath.SetValue(self.settings.Get('shell_path'))
        self.tc_shellargs.SetValue(self.settings.Get('shell_args'))
        self.tc_termtype.SetValue(self.settings.Get('term_type'))
        self.cb_termcolor.SetValue(self.settings.Get('term_color'))
        self.cp_fgcolor.SetColour(self.settings.Get('term_fgcolor'))
        self.cp_bgcolor.SetColour(self.settings.Get('term_bgcolor'))
        self.SetFontSelection(self.settings.Get('term_font'),
                              self.settings.Get('term_font_size'))
        self.Refresh()
        return
    def Save(self):
        shell_path               = self.tc_shellpath.GetValue()
        self.settings.Set('shell_path', os.path.abspath(shell_path))
        self.settings.Set('shell_args', self.tc_shellargs.GetValue())
        self.settings.Set('term_type', self.tc_termtype.GetValue())
        self.settings.Set('term_color', self.cb_termcolor.IsChecked())
        color = self.cp_fgcolor.GetColour()
        self.settings.Set('term_fgcolor', (color.GetRed(), color.GetGreen(), color.GetBlue()))
        color = self.cp_bgcolor.GetColour()
        self.settings.Set('term_bgcolor', (color.GetRed(), color.GetGreen(), color.GetBlue()))
        self.settings.Set('term_font', self.font_name)
        self.settings.Set('term_font_size', self.font_size)
        return

################################################################

class TabGraph(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        self.settings = settings
        box_main = wx.BoxSizer(wx.VERTICAL)
        # Row one.
        lblList = ['3D', '2D']
        self.rbox = wx.RadioBox(self, label='Graph Rendering', choices=lblList,
                                majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        if self.settings.Get('graph_3D'):
            self.rbox.SetSelection(0)
        else:
            self.rbox.SetSelection(1)
        box_main.Add(self.rbox, 0, wx.EXPAND | wx.ALL, 5)
        # Row two.
        btn_font = wx.Button(self, wx.ID_ANY, "Select Graph Font")
        btn_font.Bind(wx.EVT_BUTTON, self.OnFontDialog)
        box_main.Add(btn_font, 0, wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 5)
        # Row three.
        p_sample = wx.Panel(self, style=wx.RAISED_BORDER)
        p_sample.SetBackgroundColour((255,255,255))
        self.st_sample = wx.StaticText(p_sample, -1, "Font Sample Text",
                                       size=(-1, 64))
        self.SetFontSelection(self.settings.Get('graph_font'),
                              self.settings.Get('graph_font_size'))
        box_samp = wx.BoxSizer(wx.VERTICAL)
        box_samp.Add(self.st_sample, 0, wx.EXPAND | wx.ALL, 5)
        box_main.Add(p_sample, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        p_sample.SetSizerAndFit(box_samp)
        self.SetSizerAndFit(box_main)
        return
    def OnFontDialog(self, event):
        self.font_dialog = glsFontDialog(self, self.SetFontSelection)
        return
    def SetFontSelection(self, name, size):
        self.font_name = name
        self.font_size = size
        self.st_sample.SetLabel(name+" Sample Text")
        font = wx.Font(self.font_size, family=wx.DEFAULT,
                       style=wx.NORMAL, weight=wx.NORMAL, underline=False,
                       faceName=self.font_name)
        self.st_sample.SetFont(font)
        self.Layout()
        self.Fit()
        return
    def Load(self):
        if self.settings.Get('graph_3D'):
            dims = "3D"
        else:
            dims = "2D"            
        self.rbox.SetStringSelection(dims)
        self.SetFontSelection(self.settings.Get('graph_font'),
                              self.settings.Get('graph_font_size'))
        self.Refresh()
        return
    def Save(self):
        dims = self.rbox.GetStringSelection()
        if dims == "3D":
            self.settings.Set('graph_3D', True)
        else:
            self.settings.Set('graph_3D', False)
        self.settings.Set('graph_font', self.font_name)
        self.settings.Set('graph_font_size', self.font_size)
        return

################################################################

class TabEditor(wx.Panel):
    def __init__(self, parent, settings):
        wx.Panel.__init__(self, parent)
        self.settings = settings
        box_main = wx.BoxSizer(wx.VERTICAL)
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_path = wx.StaticText(self, wx.ID_ANY, "Editor Path:")
        row0.Add(self.st_edit_path, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_path = wx.TextCtrl(self, wx.ID_ANY)
        edit_path = os.path.abspath(settings.Get('edit_path'))
        self.tc_path.SetValue(edit_path)
        row0.Add(self.tc_path, 1, wx.ALL)
        row0.AddSpacer(5)
        box_main.Add(row0, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_edit_args, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_args = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_args.SetValue(str(settings.Get('edit_args')))
        row1.Add(self.tc_args, 1, wx.ALL)
        row1.AddSpacer(5)
        box_main.Add(row1, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row 2.
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_args = wx.StaticText(self, wx.ID_ANY, "Editor Commands:")
        row2.Add(self.st_edit_args, 0, wx.LEFT | wx.RIGHT, 5)
        box_main.Add(row2, 0,  wx.BOTTOM, 5)
        # Row three.
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open = wx.Button(self, wx.ID_ANY, "Open File")
        self.btn_open.Bind(wx.EVT_BUTTON, self.OnOpenKeys)
        row3.Add(self.btn_open, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_open = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.tc_open.SetValue(str(settings.Get('edit_open')))
        row3.Add(self.tc_open, 1, wx.EXPAND | wx.RIGHT, 5)
        box_main.Add(row3, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row four.
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_line = wx.Button(self, wx.ID_ANY, "Goto Line")
        self.btn_line.Bind(wx.EVT_BUTTON, self.OnLineKeys)
        row4.Add(self.btn_line, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_line = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.tc_line.SetValue(str(settings.Get('edit_line')))
        row4.Add(self.tc_line, 1, wx.EXPAND | wx.RIGHT, 5)
        box_main.Add(row4, 0, wx.EXPAND | wx.BOTTOM, 5)
        self.SetSizerAndFit(box_main)
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
        self.tc_path.SetValue(self.settings.Get('edit_path'))
        self.tc_args.SetValue(self.settings.Get('edit_args'))
        self.tc_open.SetValue(self.settings.Get('edit_open'))
        self.tc_line.SetValue(self.settings.Get('edit_line'))
    def Save(self):
        edit_path = self.tc_path.GetValue()
        self.settings.Set('edit_path', os.path.abspath(edit_path))
        self.settings.Set('edit_args', self.tc_args.GetValue())
        self.settings.Set('edit_open', self.tc_open.GetValue())
        self.settings.Set('edit_line', self.tc_line.GetValue())
        return

################################################################

class SettingsFrame(wx.Frame):
    def __init__(self, parent, settings,
                 style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="Settings", style=style)
        self.settings = settings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Create panel and notebook on the panel.
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.icons = glsIcons()
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(self.icons.Get('cog'))
        self.SetIcon(self.icon)
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(self.icons.Get('monitor'))
        self.image_list.Add(self.icons.Get('monitor_edit'))
        self.image_list.Add(self.icons.Get('chart_organisation'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = [ TabTerminal(self.notebook, self.settings),
                      TabEditor(self.notebook, self.settings),
                      TabGraph(self.notebook, self.settings) ]
        self.tab_names = [ " Terminal", " Term Editor", " FDP Graph" ]
        for t in range(len(self.tabs)):
            self.notebook.AddPage(self.tabs[t], self.tab_names[t])
            self.notebook.SetPageImage(t, t)
        box_main.Add(self.notebook, 1, wx.EXPAND | wx.TOP)
        # Create buttons.
        row_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(self, wx.ID_ANY, "Cancel")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_cancel.SetBitmap(self.icons.Get('cross'))
        row_bottom.Add(self.btn_cancel)
        self.btn_reset = wx.Button(self, wx.ID_ANY, "Reset")
        self.btn_reset.Bind(wx.EVT_BUTTON, self.OnReset)
        self.btn_reset.SetBitmap(self.icons.Get('arrow_undo'))
        row_bottom.Add(self.btn_reset)
        self.btn_load = wx.Button(self, wx.ID_ANY, "Load")
        self.btn_load.Bind(wx.EVT_BUTTON, self.OnLoad)
        self.btn_load.SetBitmap(self.icons.Get('database_go'))
        row_bottom.Add(self.btn_load)
        self.btn_save = wx.Button(self, wx.ID_ANY, "Save")
        self.btn_save.Bind(wx.EVT_BUTTON, self.OnSave)
        self.btn_save.SetBitmap(self.icons.Get('disk'))
        row_bottom.Add(self.btn_save)
        self.btn_apply = wx.Button(self, wx.ID_ANY, "Apply")
        self.btn_apply.Bind(wx.EVT_BUTTON, self.OnApply)
        self.btn_apply.SetBitmap(self.icons.Get('tick'))
        row_bottom.Add(self.btn_apply)
        box_main.Add(row_bottom, 0)
        # Set main box as frame sizer.
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnLoad(self, event):
        self.settings.Load()
        for tab in self.tabs:
            tab.Load()
        return
    def OnSave(self, event):
        for tab in self.tabs:
            tab.Save()
        self.settings.Save()
        self.settings.OnChange()
        return
    def OnApply(self, event):
        for tab in self.tabs:
            tab.Save()
        self.settings.OnChange()
        self.OnClose()
        return
    def OnReset(self, event):
        self.settings.Reset()
        for tab in self.tabs:
            tab.Load()
        return
    def OnCancel(self, event):
        self.OnClose()
        return
    def OnClose(self, event=None):
        self.Parent.settings_frame = None
        self.Destroy()
        return

################################################################
