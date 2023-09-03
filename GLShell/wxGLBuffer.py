import wx
import numpy as np

class wxGLBuffer():
    dc     = None
    bitmap = None
    buff    = None
    width  = 0
    height = 0
    def __init__(self,w,h):
        self.width  = w
        self.height = h
        self.buff = np.zeros((self.width,self.height,4), np.uint8)
        self.dc = wx.MemoryDC()
        self.bitmap = wx.Bitmap(self.width, self.height, 32)
        self.dc.SelectObject(self.bitmap)
        return
    def Clear(self):
        self.dc.SetBrush(wx.Brush('#000000'))
        self.dc.DrawRectangle(0, 0, self.width, self.height)
        self.buff.fill(0)        
        return
    def SyncBuffer(self):
        self.dc.SelectObject(wx.NullBitmap)
        self.bitmap.CopyToBuffer(self.buff, format=wx.BitmapBufferFormatRGBA)
        self.dc.SelectObject(self.bitmap)
        return
    def SyncDC(self):
        self.dc.SelectObject(wx.NullBitmap)
        self.bitmap.CopyFromBuffer(self.buff, format=wx.BitmapBufferFormatRGBA)
        self.dc.SelectObject(self.bitmap)
        return
    def GetBuffer(self):
        return self.buff
