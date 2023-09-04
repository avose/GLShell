import wx
import numpy as np
from glsGLBuffer import glsGLBuffer
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *

class glsGLTextSizer():
    fontinfo = None
    font     = None
    dc       = None
    def __init__(self,fontinfo=None):
        self.dc = wx.MemoryDC()
        if fontinfo is not None:
            self.SetFont(fontinfo)
        return
    def SetFont(self,fontinfo):
        self.fontinfo = fontinfo
        self.font = wx.Font(self.fontinfo)
        self.dc.SetFont(self.font)
        return
    def TextSize(self,text):
        return self.dc.GetTextExtent(text)

class glsGLText():
    buff       = None
    text       = None
    font       = None
    fontinfo   = None
    color      = None
    width      = 0
    height     = 0
    def __init__(self,buff,fontinfo,color=None,text=None):
        if not isinstance(buff, glsGLBuffer):
            raise Exception("glsGLText(): Buffer must have type glsGLBuffer.")
        self.buff = buff
        self.buff.dc.SetTextForeground([255,255,255])
        self.buff.dc.SetTextBackground(wx.NullColour)
        self.buff.dc.SetBackgroundMode(wx.TRANSPARENT)
        if not isinstance(fontinfo, wx.FontInfo):
            raise Exception("glsGLText(): Fontinfo must have type wx.FontInfo.")
        self.SetFont(fontinfo)
        if color is not None:
            self.SetColor(color)
        if text is not None:
            self.SetText(text)
        return
    def SetFont(self,fontinfo):
        self.fontinfo = fontinfo
        self.font = wx.Font(self.fontinfo)
        self.buff.dc.SetFont(self.font)
        return
    def SetColor(self,color):
        self.color = color
        return
    def SetText(self,text):
        self.text = text
        self.width, self.height = self.buff.dc.GetTextExtent(self.text)
        self.DrawDC()
        return
    def SyncBuffer(self):
        self.buff.SyncBuffer()
        self.buff.SyncTexture()
        return
    def DrawDC(self,text=None):
        if text is not None:
            self.SetText(text)
        self.buff.Clear()
        self.buff.dc.DrawText(self.text, 0, 0)
        self.SyncBuffer()
        return
    def DrawGL(self,pos,text=None,center=False):
        if text is not None:
            self.DrawDC(text)
        if center:
            half_width  = self.width/2.0
            half_height = self.height/2.0
            xtoff = float(self.width)/float(self.buff.width)
            offsets = [ [-half_width, -half_height, 0],
                        [-half_width,  half_height, 0],
                        [ half_width,  half_height, 0],
                        [ half_width, -half_height, 0] ]
            tex_coords = [ [0.0, 1.0],
                           [0.0, 0.0],
                           [xtoff, 0.0],
                           [xtoff, 1.0] ]
        else:
            offsets = [ [0,               0,                0],
                        [0,               self.buff.height, 0],
                        [self.buff.width, self.buff.height, 0],
                        [self.buff.width, 0,                0] ]
            tex_coords = [ [0.0, 1.0],
                           [0.0, 0.0],
                           [1.0, 0.0],
                           [1.0, 1.0] ]
        pos = np.array(pos, dtype=np.single)
        offsets = np.array(offsets, dtype=np.single)
        glEnable(GL_TEXTURE_2D)
        self.buff.BindTexture()
        glColor4fv(self.color)
        glBegin(GL_QUADS)
        for off,coord in zip(offsets,tex_coords):
            glTexCoord2fv(coord);
            glVertex3fv(pos+off)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        return
