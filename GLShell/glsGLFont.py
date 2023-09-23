import wx
import numpy as np
from glsGLBuffer import glsGLBuffer
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *

################################################################

# Fixed width+height fonts only for now.
class glsGLFont():
    def __init__(self, fontinfo):
        self.fontinfo = fontinfo
        self.font = wx.Font(self.fontinfo)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        self.char_w, self.char_h = dc.GetTextExtent("X")
        del dc
        self.buff = glsGLBuffer(self.char_w*16, self.char_h*16)
        self.buff.dc.SetFont(self.font)
        self.buff.dc.SetTextForeground([255,255,255])
        self.buff.dc.SetTextBackground(wx.NullColour)
        self.buff.dc.SetBackgroundMode(wx.TRANSPARENT)
        for c in range(256):
            char = chr(c)
            x = c%16
            y = int(c/16)
            if c > 32 and c < 127 or c > 159:
                self.buff.dc.DrawText(char, x*self.char_w, y*self.char_h)
        self.buff.SyncBuffer()
        self.buff.SyncTexture()
        w,h = self.char_w, self.char_h
        self.display_lists = glGenLists(256)
        self.offsets = np.array([ [0, 0],
                                  [0, h],
                                  [w, h],
                                  [w, 0] ],
                                dtype=np.single)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glEnable(GL_TEXTURE_2D)
        self.buff.BindTexture()
        for c in range(256):
            char = chr(c)
            x = c%16
            y = int(c/16)
            tex_coords = [ [(x+0)/16.0, (y+1)/16.0],
                           [(x+0)/16.0, (y+0)/16.0],
                           [(x+1)/16.0, (y+0)/16.0],
                           [(x+1)/16.0, (y+1)/16.0] ]
            tex_coords = np.array(tex_coords, dtype=np.single)
            glNewList(self.display_lists+c, GL_COMPILE);
            glBegin(GL_POLYGON)
            for off,coord in zip(self.offsets,tex_coords):
                glTexCoord2fv(coord);
                glVertex2fv(off)
            glEnd()
            glTranslatef(self.char_w, 0, 0)
            glEndList()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        return
    def DrawText(self, text, pos=(0,0,0), color=(1,1,1,1), center=False, background=False):
        if center:
            pos[0] -= (len(text)*self.char_w) / 2.0
            pos[1] -= self.char_h / 2.0
        glPushMatrix()
        glTranslatef(pos[0], pos[1], -pos[2])
        if background:
            glColor4fv([0,0,0,0.80])
            offsets = self.offsets.copy()
            offsets[:,0] *= len(text)
            offsets[:2,0] -= self.char_w / 2.0
            offsets[2:,0] += self.char_w / 2.0
            glBegin(GL_POLYGON)
            for off in offsets:
                glVertex2fv(off)
            glEnd()
        glColor4fv(color)
        glEnable(GL_TEXTURE_2D)
        self.buff.BindTexture()
        glListBase(self.display_lists)
        glCallLists(len(text), GL_UNSIGNED_BYTE, bytes(text,"utf-8"))
        glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        return

################################################################
