import wx
import datetime

from glsLog import glsLog

################################################################

class glsLogList(wx.VListBox):
    def __init__(self, parent, log, size):
        self.log = log
        style = wx.LB_NEEDED_SB | wx.SIMPLE_BORDER
        self.char_w,self.char_h = 10,10
        super(glsLogList, self).__init__(parent, style=style, size=size)
        self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        self.SetBackgroundColour((0,0,0))
        self.char_w,self.char_h = dc.GetTextExtent("X")
        self.SetItemCount(self.log.count())
        self.ScrollRows(self.log.count())
        self.Show(True)
        return
    def LineWrapText(self, initial_text):
        if initial_text is None or len(initial_text) == 0:
            return ("", 0)
        max_len = max(1, int(self.Size[0]/self.char_w)-28)
        nlines = 0
        text = ""
        initial_text = initial_text.replace("\t","    ")
        lines = initial_text.split("\n")
        for line in lines:
            while len(line) > max_len:
                text += line[0:max_len] + '\n'
                line = line[max_len:]
                nlines += 1
            text += line + '\n'
            nlines += 1
        return (text, nlines)
    def OnMeasureItem(self, index):
        timestamp, text = self.log.get(index)
        text, rows = self.LineWrapText(text)
        return  rows * self.char_h
    def OnDrawItem(self, dc, rect, index):
        timestamp, text = self.log.get(index)
        text, rows = self.LineWrapText(self.log.get(index)[1])
        dc.Clear()
        dc.SetFont(self.font)
        # Draw background and borders.
        if self.IsSelected(index):
            brush = wx.Brush((64,0,64))
        else:
            brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.SetPen(wx.Pen((0,0,100)))
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        dc.SetPen(wx.Pen((0,75,150)))
        dc.DrawLine(rect[0] + int(5.5*self.char_w), rect[1],
                    rect[0] + int(5.5*self.char_w), rect[1]+rect[3])
        dc.DrawLine(rect[0] + int(25.5*self.char_w), rect[1],
                    rect[0] + int(25.5*self.char_w), rect[1]+rect[3])
        # Draw log line number and date.
        dc.SetTextForeground((255,255,0))
        dc.DrawText("%d"%index, rect[0], rect[1])
        dc.SetTextForeground((255,0,255))
        dc.DrawText(timestamp, rect[0] + 6*self.char_w, rect[1])
        # Draw log entry text.
        dc.SetTextForeground((128,192,128))
        dc.DrawText(text, rect[0] + 26*self.char_w, rect[1])
        # Update to catch new log entries.
        self.SetItemCount(self.log.count())
        return
    def OnDrawBackground(self, dc, rect, index):
        dc.Clear()
        pen = wx.Pen((0,0,255))
        dc.SetPen(pen)
        brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        # Update to catch new log entries.
        self.SetItemCount(self.log.count())
        return
    def OnDrawSeparator(self, dc, rect, index):
        return

################################################################

class glsStatusBarPopup(wx.PopupTransientWindow):
    def __init__(self, parent, log):
        style = wx.SIMPLE_BORDER
        wx.PopupTransientWindow.__init__(self, parent, style)
        self.log = log
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.log_list = glsLogList(self, self.log, (parent.Size[0], 150))
        box_main.Add(self.log_list, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def ProcessLeftDown(self, event):
        return wx.PopupTransientWindow.ProcessLeftDown(self, event)
    def OnDismiss(self):
        self.Parent.popup = None
        return

################################################################

class glsStatusBar(wx.StatusBar):
    def __init__(self, parent):
        super(glsStatusBar, self).__init__(parent)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        glsLog.add("Create StatusBar")
        return
    def OnLeftDown(self, event):
        sbsize = self.GetSize()
        pos = event.GetPosition()
        if pos[0] >= sbsize[0] - 50:
            if self.popup is not None:
                self.popup.Dismiss()
                self.popup = None
            event.Skip()
            return
        self.popup = glsStatusBarPopup(self, glsLog)
        pos = self.ClientToScreen( (0,0) )
        self.popup.Position((pos[0],pos[1]-150), (0, 0))
        self.popup.Popup()
        return

################################################################
