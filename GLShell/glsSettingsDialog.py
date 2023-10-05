import os
import wx

from glsFontDialog import glsFontDialog
from glsSettings import glsSettings
from glsKeyPress import glsKeyPress
from glsIcons import glsIcons

################################################################

class KeyPressesFrame(wx.Frame):
    def __init__(self, parent, callback,
                 style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="Keypress Recorder", style=style)
        self.callback = callback
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(glsIcons.Get('keyboard'))
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
        self.btn_cancel.SetBitmap(glsIcons.Get('cross'))
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_cancel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_cancel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_cancel)
        self.btn_clear = wx.Button(self, wx.ID_ANY, "Clear")
        self.btn_clear.SetBitmap(glsIcons.Get('arrow_undo'))
        self.btn_clear.Bind(wx.EVT_BUTTON, self.OnClear)
        self.btn_clear.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.btn_clear.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        row1.Add(self.btn_clear)
        self.btn_ok = wx.Button(self, wx.ID_ANY, "OK")
        self.btn_ok.SetBitmap(glsIcons.Get('tick'))
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
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour((192,192,192))
        vbox = wx.BoxSizer(wx.VERTICAL)
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_path = wx.StaticText(self, wx.ID_ANY, "Program Path:")
        row0.Add(self.st_shell_path, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_shellpath = wx.TextCtrl(self, wx.ID_ANY)
        shell_path = os.path.abspath(glsSettings.Get('shell_path'))
        self.tc_shellpath.SetValue(shell_path)
        row0.Add(self.tc_shellpath, 1, wx.ALIGN_CENTER | wx.ALL)
        row0.AddSpacer(5)
        vbox.Add(row0, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_shell_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_shell_args, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_shellargs = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_shellargs.SetValue(str(glsSettings.Get('shell_args')))
        row1.Add(self.tc_shellargs, 1, wx.ALIGN_CENTER | wx.ALL)
        row1.AddSpacer(5)
        vbox.Add(row1, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row two.
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_term_type = wx.StaticText(self, wx.ID_ANY, "Type ($TERM):")
        row2.Add(self.st_term_type, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_termtype = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_termtype.SetValue(str(glsSettings.Get('term_type')))
        row2.Add(self.tc_termtype, 1, wx.ALIGN_CENTER | wx.ALL)
        vbox.Add(row2, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row three.
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb_termcolor = wx.CheckBox(self, wx.ID_ANY, "Support Text Color")
        self.cb_termcolor.SetValue(glsSettings.Get('term_color'))
        row3.Add(self.cb_termcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        row2.AddSpacer(5)
        vbox.Add(row3, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row four is a 2x2 grid.
        grid2 = wx.GridSizer(2,2,5,5)
        self.st_fgcolor = wx.StaticText(self, wx.ID_ANY, "Foreground Color:")
        grid2.Add(self.st_fgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.cp_fgcolor = wx.ColourPickerCtrl(self)
        self.cp_fgcolor.SetColour(glsSettings.Get('term_fgcolor'))
        grid2.Add(self.cp_fgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.st_bgcolor = wx.StaticText(self, wx.ID_ANY, "Backround Color:")
        grid2.Add(self.st_bgcolor, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.cp_bgcolor = wx.ColourPickerCtrl(self)
        self.cp_bgcolor.SetColour(glsSettings.Get('term_bgcolor'))
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
        self.SetFontSelection(glsSettings.Get('term_font'),
                              glsSettings.Get('term_font_size'))
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
        self.tc_shellpath.SetValue(glsSettings.Get('shell_path'))
        self.tc_shellargs.SetValue(glsSettings.Get('shell_args'))
        self.tc_termtype.SetValue(glsSettings.Get('term_type'))
        self.cb_termcolor.SetValue(glsSettings.Get('term_color'))
        self.cp_fgcolor.SetColour(glsSettings.Get('term_fgcolor'))
        self.cp_bgcolor.SetColour(glsSettings.Get('term_bgcolor'))
        self.SetFontSelection(glsSettings.Get('term_font'),
                              glsSettings.Get('term_font_size'))
        self.Refresh()
        return
    def Save(self):
        settings = []
        shell_path = self.tc_shellpath.GetValue()
        settings.append( ('shell_path', os.path.abspath(shell_path)) )
        settings.append( ('shell_args', self.tc_shellargs.GetValue()) )
        settings.append( ('term_type', self.tc_termtype.GetValue()) )
        settings.append( ('term_color', self.cb_termcolor.IsChecked()) )
        color = self.cp_fgcolor.GetColour()
        settings.append( ('term_fgcolor', (color.GetRed(), color.GetGreen(), color.GetBlue())) )
        color = self.cp_bgcolor.GetColour()
        settings.append( ('term_bgcolor', (color.GetRed(), color.GetGreen(), color.GetBlue())) )
        settings.append( ('term_font', self.font_name) )
        settings.append( ('term_font_size', self.font_size) )
        glsSettings.SetList(settings)
        return

################################################################

class TabGraph(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.SetBackgroundColour((192,192,192))
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_graph_ignore = wx.StaticText(self, wx.ID_ANY, "Path Ignore List:")
        row1.Add(self.st_graph_ignore, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_graph_ignore = wx.TextCtrl(self, wx.ID_ANY)
        graph_ignore = ", ".join(glsSettings.Get('graph_ignore'))
        self.tc_graph_ignore.SetValue(graph_ignore)
        row1.Add(self.tc_graph_ignore, 1, wx.ALIGN_CENTER | wx.ALL)
        box_main.Add(row1, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)
        # Row two.
        dims = ['3D', '2D']
        self.rbox = wx.RadioBox(self, label='Graph Rendering', choices=dims,
                                majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        if glsSettings.Get('graph_3D'):
            self.rbox.SetSelection(0)
        else:
            self.rbox.SetSelection(1)
        box_main.Add(self.rbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        # Row three.
        btn_font = wx.Button(self, wx.ID_ANY, "Select Graph Font")
        btn_font.Bind(wx.EVT_BUTTON, self.OnFontDialog)
        box_main.Add(btn_font, 0, wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 5)
        # Row four.
        p_sample = wx.Panel(self, style=wx.RAISED_BORDER)
        p_sample.SetBackgroundColour((255,255,255))
        self.st_sample = wx.StaticText(p_sample, -1, "Font Sample Text",
                                       size=(-1, 64))
        self.SetFontSelection(glsSettings.Get('graph_font'),
                              glsSettings.Get('graph_font_size'))
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
        if glsSettings.Get('graph_3D'):
            dims = "3D"
        else:
            dims = "2D"            
        graph_ignore = ", ".join(glsSettings.Get('graph_ignore'))
        self.tc_graph_ignore.SetValue(graph_ignore)
        self.rbox.SetStringSelection(dims)
        self.SetFontSelection(glsSettings.Get('graph_font'),
                              glsSettings.Get('graph_font_size'))
        self.Refresh()
        return
    def Save(self):
        settings = []
        dims = self.rbox.GetStringSelection()
        if dims == "3D":
            settings.append( ('graph_3D', True) )
        else:
            settings.append( ('graph_3D', False) )
        ignore = self.tc_graph_ignore.GetValue().split(",")
        ignore = [ i.strip() for i in ignore if i != "" ]
        ignore = [ i for i in ignore if i != "" ]
        settings.append( ('graph_ignore', ignore) )
        settings.append( ('graph_font', self.font_name) )
        settings.append( ('graph_font_size', self.font_size) )
        glsSettings.SetList(settings)
        return

################################################################

class TabEditor(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.SetBackgroundColour((192,192,192))
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_path = wx.StaticText(self, wx.ID_ANY, "Editor Path:")
        row0.Add(self.st_edit_path, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_path = wx.TextCtrl(self, wx.ID_ANY)
        edit_path = os.path.abspath(glsSettings.Get('edit_path'))
        self.tc_path.SetValue(edit_path)
        row0.Add(self.tc_path, 1, wx.ALL)
        row0.AddSpacer(5)
        box_main.Add(row0, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        # Row one.
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_edit_args = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        row1.Add(self.st_edit_args, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_args = wx.TextCtrl(self, wx.ID_ANY)
        self.tc_args.SetValue(str(glsSettings.Get('edit_args')))
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
        self.tc_open.SetValue(str(glsSettings.Get('edit_open')))
        row3.Add(self.tc_open, 1, wx.EXPAND | wx.RIGHT, 5)
        box_main.Add(row3, 0, wx.EXPAND | wx.BOTTOM, 5)
        # Row four.
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_line = wx.Button(self, wx.ID_ANY, "Goto Line")
        self.btn_line.Bind(wx.EVT_BUTTON, self.OnLineKeys)
        row4.Add(self.btn_line, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        self.tc_line = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.tc_line.SetValue(str(glsSettings.Get('edit_line')))
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
        self.tc_path.SetValue(glsSettings.Get('edit_path'))
        self.tc_args.SetValue(glsSettings.Get('edit_args'))
        self.tc_open.SetValue(glsSettings.Get('edit_open'))
        self.tc_line.SetValue(glsSettings.Get('edit_line'))
    def Save(self):
        settings = []
        edit_path = self.tc_path.GetValue()
        settings.append( ('edit_path', os.path.abspath(edit_path)) )
        settings.append( ('edit_args', self.tc_args.GetValue()) )
        settings.append( ('edit_open', self.tc_open.GetValue()) )
        settings.append( ('edit_line', self.tc_line.GetValue()) )
        glsSettings.SetList(settings)
        return

################################################################

class TabGeneral(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.SetBackgroundColour((192,192,192))
        # Row zero.
        row0 = wx.BoxSizer(wx.HORIZONTAL)
        self.st_log_level = wx.StaticText(self, wx.ID_ANY, "Debug Log Level:")
        row0.Add(self.st_log_level, 0, wx.ALIGN_CENTER | wx.LEFT | wx.TOP | wx.RIGHT, 5)
        log_level = glsSettings.Get('log_level')
        self.sp_log = wx.SpinCtrl(self, id=wx.ID_ANY, value=str(log_level),
                                  style=wx.SP_ARROW_KEYS, min=0, max=100, initial=log_level)
        row0.Add(self.sp_log, 0, wx.ALIGN_CENTER | wx.LEFT | wx.TOP | wx.RIGHT, 5)
        box_main.Add(row0, 0)
        self.SetSizerAndFit(box_main)
        self.Show(True)
    def Load(self):
        self.sp_log.SetValue(glsSettings.Get('log_level'))
    def Save(self):
        settings = []
        settings.append( ('log_level', self.sp_log.GetValue()) )
        glsSettings.SetList(settings)
        return

################################################################

class glsSettingsDialog(wx.Frame):
    def __init__(self, parent, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="Settings", style=style)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.SetBackgroundColour((192,192,192))
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(glsIcons.Get('cog'))
        self.SetIcon(self.icon)
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(glsIcons.Get('monitor'))
        self.image_list.Add(glsIcons.Get('monitor_edit'))
        self.image_list.Add(glsIcons.Get('chart_organisation'))
        self.image_list.Add(glsIcons.Get('cog'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = [ TabTerminal(self.notebook),
                      TabEditor(self.notebook),
                      TabGraph(self.notebook),
                      TabGeneral(self.notebook) ]
        self.tab_names = [ " Terminal", " Term Editor", " FDP Graph", " General" ]
        for t in range(len(self.tabs)):
            self.notebook.AddPage(self.tabs[t], self.tab_names[t])
            self.notebook.SetPageImage(t, t)
        box_main.Add(self.notebook, 1, wx.EXPAND | wx.TOP)
        # Create buttons.
        row_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(self, wx.ID_ANY, "Cancel")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_cancel.SetBitmap(glsIcons.Get('cross'))
        row_bottom.Add(self.btn_cancel)
        self.btn_reset = wx.Button(self, wx.ID_ANY, "Reset")
        self.btn_reset.Bind(wx.EVT_BUTTON, self.OnReset)
        self.btn_reset.SetBitmap(glsIcons.Get('arrow_undo'))
        row_bottom.Add(self.btn_reset)
        self.btn_load = wx.Button(self, wx.ID_ANY, "Load")
        self.btn_load.Bind(wx.EVT_BUTTON, self.OnLoad)
        self.btn_load.SetBitmap(glsIcons.Get('database_go'))
        row_bottom.Add(self.btn_load)
        self.btn_save = wx.Button(self, wx.ID_ANY, "Save")
        self.btn_save.Bind(wx.EVT_BUTTON, self.OnSave)
        self.btn_save.SetBitmap(glsIcons.Get('disk'))
        row_bottom.Add(self.btn_save)
        self.btn_apply = wx.Button(self, wx.ID_ANY, "Apply")
        self.btn_apply.Bind(wx.EVT_BUTTON, self.OnApply)
        self.btn_apply.SetBitmap(glsIcons.Get('tick'))
        row_bottom.Add(self.btn_apply)
        box_main.Add(row_bottom, 0)
        # Set main box as frame sizer.
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnLoad(self, event):
        glsSettings.Load()
        for tab in self.tabs:
            tab.Load()
        return
    def OnSave(self, event):
        for tab in self.tabs:
            tab.Save()
        glsSettings.Save()
        glsSettings.OnChange()
        return
    def OnApply(self, event):
        for tab in self.tabs:
            tab.Save()
        glsSettings.OnChange()
        self.OnClose()
        return
    def OnReset(self, event):
        glsSettings.Reset()
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
