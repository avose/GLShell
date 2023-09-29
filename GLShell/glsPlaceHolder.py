import wx

################################################################

class glsPlaceHolder(wx.Window):
        def __init__(self, parent, message):
            super(glsPlaceHolder, self).__init__(parent)
            self.message = message
            self.SetBackgroundColour((0,0,0))
            box_main = wx.BoxSizer(wx.VERTICAL)
            box_panel = wx.BoxSizer(wx.HORIZONTAL)
            p_message = wx.Panel(self, style=wx.RAISED_BORDER)
            p_message.SetBackgroundColour((192,192,192))
            box_messg = wx.BoxSizer(wx.VERTICAL)
            self.st_message = wx.StaticText(p_message, wx.ID_ANY, self.message)
            box_messg.Add(self.st_message, 1, wx.ALL, 20)
            p_message.SetSizerAndFit(box_messg)
            box_panel.Add(p_message, 1, wx.ALIGN_CENTER)
            box_main.Add(box_panel, 1, wx.ALIGN_CENTER)
            self.SetSizerAndFit(box_main)
            self.Show(True)
            return
        def OnClose(self, event=None):
            return

################################################################
