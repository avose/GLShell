from wx.glcanvas import GLCanvas
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
import numpy as np
import sys, math
import wx


class fdpNode():
    pos = None
    frc = None
    def __init__(self):
        self.pos = np.ndarray(3, dtype=float)
        self.frc = np.ndarray(3, dtype=float)

class fdpCanvas(GLCanvas):
    def __init__(self, parent, pos, size):
        glattrs = wx.glcanvas.GLAttributes()
        GLCanvas.__init__(self, parent, id=-1, pos=pos, size=size)
        wx.EVT_PAINT(self, self.OnPaint)
        self.init = 0
        return

    def OnPaint(self,event):
        if not self.init:
            self.InitGL()
            self.glctx = wx.glcanvas.GLContext(self)
            self.SetCurrent(self.glctx)
            glutInit(sys.argv);
            self.init = 1
        self.SetCurrent(self.glctx)
        self.OnDraw()
        return

    def OnDraw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        color = [1.0,0.,0.,1.]
        glMaterialfv(GL_FRONT,GL_DIFFUSE,color)
        '''
        glBegin(GL_LINE_LOOP)
        radius = 0.25
        for vertex in range(0, 100):
            angle  = float(vertex) * 2.0 * np.pi / 100
            glVertex3f(np.cos(angle)*radius, np.sin(angle)*radius, 0.0)
        glEnd();
        '''
        glDisable(GL_LIGHTING)
        glColor4fv(color)
        gluSphere(self.quadratic,0.333,32,32)
        glEnable(GL_LIGHTING)
        glPopMatrix()
        self.SwapBuffers()
        return
        
    def InitGL(self):
        # set viewing projection
        light_diffuse = [1.0, 1.0, 1.0, 1.0]
        light_position = [1.0, 1.0, 1.0, 0.0]

        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        glLightfv(GL_LIGHT0, GL_POSITION, light_position)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(40.0, 1.0, 1.0, 30.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0.0, 0.0, 10.0,
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)
        self.quadratic = gluNewQuadric()
        gluQuadricNormals(self.quadratic, GLU_SMOOTH)
        gluQuadricTexture(self.quadratic, GL_TRUE)
        return
