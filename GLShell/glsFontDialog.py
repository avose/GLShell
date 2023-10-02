from string import ascii_lowercase as ascii_lc

import wx
from glsIcons import glsIcons

################################################################

class glsFontPanel(wx.Panel):
    def __init__(self, parent, callback_font):
        wx.Panel.__init__(self, parent, -1)
        self.callback_font = callback_font
        self.font_enum = wx.FontEnumerator()
        self.font_enum.EnumerateFacenames(wx.FONTENCODING_SYSTEM, fixedWidthOnly=True)
        self.all_fonts = self.font_enum.GetFacenames(wx.FONTENCODING_SYSTEM)
        st_names = wx.StaticText(self, -1, "Font Names:")
        self.lb_font = wx.ListBox(self, -1, size=(240, 240))
        st_size = wx.StaticText(self, -1, "Font Size:")
        style = wx.SL_VERTICAL | wx.SL_RIGHT | wx.SL_LABELS
        self.sl_font_size = wx.Slider(self, wx.ID_ANY, style=style, size=(-1, 210),
                                      value=10, minValue=6, maxValue=32)
        p_sample = wx.Panel(self, style=wx.RAISED_BORDER)
        p_sample.SetBackgroundColour((255,255,255))
        self.st_sample = wx.StaticText(p_sample, -1, "Sample Text", size=(-1, 64))
        btn_cancel = wx.Button(self, wx.ID_ANY, "Cancel")
        btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btn_cancel.SetBitmap(glsIcons.Get('cross'))
        btn_ok = wx.Button(self, wx.ID_ANY, "Ok")
        btn_ok.Bind(wx.EVT_BUTTON, self.OnOk)
        btn_ok.SetBitmap(glsIcons.Get('tick'))
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_prop = wx.BoxSizer(wx.HORIZONTAL)
        box_list = wx.BoxSizer(wx.VERTICAL)
        box_list.Add(st_names, 0, wx.ALL, 5)
        box_list.Add(self.lb_font, 0, wx.ALL, 5)
        box_prop.Add(box_list)
        box_size = wx.BoxSizer(wx.VERTICAL)
        box_size.Add(st_size, 0, wx.ALL, 5)
        box_size.Add(self.sl_font_size, 0, wx.EXPAND | wx.ALL, 20)
        box_prop.Add(box_size, wx.EXPAND)
        box_main.Add(box_prop)
        box_samp = wx.BoxSizer(wx.VERTICAL)
        box_samp.Add(self.st_sample, 0, wx.EXPAND | wx.ALL, 5)
        box_main.Add(p_sample, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        box_ctrl = wx.BoxSizer(wx.HORIZONTAL)
        box_ctrl.Add(btn_cancel, 0, wx.EXPAND)
        box_ctrl.Add(btn_ok, 0, wx.EXPAND)
        box_main.Add(box_ctrl, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        p_sample.SetSizerAndFit(box_samp)
        self.SetSizerAndFit(box_main)
        self.Layout()
        self.lb_font.Bind(wx.EVT_LISTBOX, self.OnFont)
        self.sl_font_size.Bind(wx.EVT_SLIDER, self.OnFont)
        self.lb_font.SetSelection(wx.NOT_FOUND)
        self.sl_font_size.SetToolTip('Select font size')
        self.Show(True)
        wx.CallAfter(self.LoadFonts)
        return
    def GetFonts(self):
        dc = wx.MemoryDC()
        for fndx,font_name in enumerate(self.all_fonts):
            font = wx.Font(10, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.NORMAL,
                           underline=False, faceName=font_name)
            dc.SetFont(font)
            full_extent = dc.GetFullTextExtent("X")
            valid = True
            for c in ascii_lc:
                if full_extent != dc.GetFullTextExtent(c):
                    valid = False
                    break
            if valid:
                yield font_name, fndx
            else:
                yield None, fndx
        return
    def LoadFonts(self):
        progress = wx.ProgressDialog("Searching Fonts",
                                     "Searching for valid fixed-width fonts...",
                                     len(self.all_fonts), parent=self,
                                     style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        font_list = []
        for font_name, fndx in self.GetFonts():
            if font_name is not None:
                font_list.append(font_name)
            progress.Update(fndx+1, "Checking Font %d of %d."%
                            (fndx+1, len(self.all_fonts)))
        self.lb_font.InsertItems(font_list, 0)
        self.lb_font.SetSelection(0)
        self.Refresh()
        return
    def OnFont(self, evt):
        facename = self.lb_font.GetStringSelection()
        size = self.sl_font_size.GetValue()
        font = wx.Font(size, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.NORMAL,
                       underline=False, faceName=facename)
        self.st_sample.SetLabel(facename+" Sample Text")
        self.st_sample.SetFont(font)
        self.Layout()
        self.Fit()
        self.Refresh()
        return
    def OnOk(self, event):
        self.callback_font(self.lb_font.GetStringSelection(),
                           self.sl_font_size.GetValue())
        self.Parent.Destroy()
        return
    def OnCancel(self, event):
        self.Parent.Destroy()
        return

################################################################

class glsFontDialog(wx.Frame):
    def __init__(self, parent, callback_font):
        wx.Frame.__init__(self, parent, title="Select Font", size=(800,600),
                          style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        icon = wx.Icon()
        icon.CopyFromBitmap(glsIcons.Get('font'))
        self.SetIcon(icon)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.font_panel = glsFontPanel(self, callback_font)
        box_main.Add(self.font_panel)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return

################################################################
