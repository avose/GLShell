from wx.glcanvas import GLCanvas
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
import numpy as np
import sys, math
import wx


class fdpNode():
    pos = np.array([0,0,0], dtype=float)
    frc = np.array([0,0,0], dtype=float)
    id = None
    def __init__(self,id):
        self.id = id

class fdpGraph():
    nodes = {}
    edges = {}
    def __init__(self):
        pass
    def __contains__(self, key):
        if isinstance(key, tuple):
            tup = key
            if isinstance(key[0], fdpNode):
                tup = (tup[0].id,tup[1])
            if isinstance(key[1], fdpNode):
                tup = (tup[0],tup[1].id)
            return tup in self.edges
        elif isinstance(key, fdpNode):
            return key.id in self.nodes
        elif isinstance(key, str):
            return key in self.nodes
    def add_node(self,node):
        if node not in self:
            self.nodes[node.id] = node
    def add_edge(self,edge):
        for n in edge:
            self.add_node(n)
        if edge not in self:
            self.edges[(edge[0].id,edge[1].id)] = edge

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
