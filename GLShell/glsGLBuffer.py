import wx
import numpy as np
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *

class glsGLBuffer():
    dc     = None
    bitmap = None
    buff   = None
    tex    = None
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
        self.bitmap.CopyToBuffer(self.buff, format=wx.BitmapBufferFormat_RGBA)
        self.dc.SelectObject(self.bitmap)
        return
    def SyncDC(self):
        self.dc.SelectObject(wx.NullBitmap)
        self.bitmap.CopyFromBuffer(self.buff, format=wx.BitmapBufferFormat_RGBA)
        self.dc.SelectObject(self.bitmap)
        return
    def SyncTexture(self):
        if self.tex is None:
            self.tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                     self.width, self.height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, self.buff)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)
        return
    def BindTexture(self):
        if self.tex is not None:
            glBindTexture(GL_TEXTURE_2D, self.tex)

        
