import wx
import numpy as np
from wxGLBuffer import wxGLBuffer

class wxGLText():
    buff     = None
    text     = None
    font     = None
    fontinfo = None
    width    = 0
    height   = 0
    def __init__(self,buff,text=None,fontinfo=None):
        if not isinstance(buff, wxGLBuffer):
            raise Exception("wxGLTextWriter(): Buffer must have type wxGLTextWriter.")
        self.buff = buff
        if fontinfo is not None:
            if not isinstance(fontinfo, wx.FontInfo):
                raise Exception("wxGLTextWriter(): Fontinfo must have type wx.FontInfo.")
            self.SetFont(fontinfo)
        if text is not None:
            self.SetText(text)
        return
    def SetFont(self,fontinfo):
        self.fontinfo = fontinfo
        self.font = wx.Font(self.fontinfo)
        self.buff.dc.SetFont(self.font)
        return
    def SetText(self,text):
        self.text = text
        if self.font is not None:
            self.width, self.height = self.buff.dc.GetTextExtent(self.text)
        return
    def Draw(self,text=None):
        if text is not None:
            self.SetText(text)
        self.buff.dc.DrawText(self.text,
                              (self.buff.width-self.width)/2,
                              (self.buff.height-self.height)/2)
        return
    def SyncBuffer(self):
        self.buff.SyncBuffer()
        return
    def GetBuffer(self):
        return self.buff.GetBuffer()
