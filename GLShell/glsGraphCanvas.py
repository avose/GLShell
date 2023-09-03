from wx.glcanvas import GLCanvas
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
from itertools import product
import numpy as np
import sys, math
import wx

from glsGLBuffer import glsGLBuffer
from glsGLText import glsGLText

class fdpNode():
    pos = np.array([0,0,0], dtype=float)
    frc = np.array([0,0,0], dtype=float)
    id  = ""
    def __init__(self,id):
        self.pos = np.random.random(size=3)
        self.frc = np.array([0,0,0], dtype=float)
        self.pos[2] = 0.0
        self.id = id
        return

class fdpGraph():
    nodes = {}
    edges = {}
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        return
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
        return
    def add_node(self,node):
        if node not in self:
            self.nodes[node.id] = node
        return
    def add_edge(self,edge):
        for n in edge:
            self.add_node(n)
        if edge not in self:
            self.edges[(edge[0].id,edge[1].id)] = edge
        return
    def compute_forces(self):
        for k in self.nodes:
            n = self.nodes[k]
            n.pos[2] = 0
        # Anti-gravity force between node pairs.
        for k0,k1 in product(self.nodes,self.nodes):
            if k0 == k1:
                continue
            a = self.nodes[k0]
            b = self.nodes[k1]
            v = np.subtract(b.pos,a.pos)
            d = np.linalg.norm(v)
            f = 0.1 * (v / (d*d))
            a.frc -= f
            b.frc += f
        # Spring force for edges (non-linear).
        for k0,k1 in self.edges:
            a = self.nodes[k0]
            b = self.nodes[k1]
            v = np.subtract(b.pos,a.pos)
            d = np.linalg.norm(v)
            f = 0.1 * (v * d)
            a.frc += f
            b.frc -= f
        return
    def apply_forces(self,speed=1.0):
        for n in self.nodes:
            node = self.nodes[n]
            node.pos += speed * node.frc
            node.frc *= 0
        return
    def tick(self,speed=1.0):
        self.compute_forces()
        self.apply_forces(speed)
        return

################################################################

class glsGraphCanvas(GLCanvas):
    init      = False
    glctx     = None
    quadratic = None
    project   = None
    textbuff  = None
    fps       = 10
    def __init__(self, parent, pos, size):
        #glattrs = wx.glcanvas.GLAttributes()
        GLCanvas.__init__(self, parent, id=-1, pos=pos, size=size)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.Tick, self.timer)
        self.timer.Start(int(1000.0/self.fps))
        return
    def AddProject(self,proj):
        self.project = proj
        return
    def OnPaint(self,event):
        if not self.init:
            self.glctx = wx.glcanvas.GLContext(self)
            self.SetCurrent(self.glctx)
            glutInit(sys.argv);
            self.InitGL()
            #
            self.buff = glsGLBuffer(160,32)
            self.textbuff = glsGLText(self.buff,"Example Text!",
                                      wx.FontInfo(12),(255,255,0,255))
            print(self.textbuff.width,self.textbuff.height)
            self.buff.SyncBuffer()
            self.buff.SyncTexture()
            #
            self.init = True
        self.SetCurrent(self.glctx)
        self.OnDraw()
        return
    def Tick(self,event):
        if self.project is not None and len(self.project.roots) > 0:
            root = self.project.roots[0]
            graph = root.graph
            graph.tick(speed=(0.1/self.fps))
        self.OnDraw()
        return
    def OnDraw(self):
        # Clear buffer.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.textbuff.DrawGL([100,100,0])
        # Scale for the FDP graph.
        glPushMatrix()
        glTranslatef(self.Size[0]/2.0, self.Size[1]/2.0, 0.0)
        glScalef(20.00, 20.0, 1.0)
        red = [1.0, 0.0, 0.0 ,1.0]
        grn = [0.0, 1.0, 0.0 ,1.0]
        # Draw the graph.
        if self.project is not None and len(self.project.roots) > 0:
            root = self.project.roots[0]
            graph = root.graph
            # Draw edges.
            glColor4fv(grn)
            glBegin(GL_LINES)
            for e in graph.edges:
                for n in e:
                    glVertex3fv(graph.nodes[n].pos)
            glEnd()
            # Draw nodes.
            for node in graph.nodes.values():
                glColor4fv(red)
                glPushMatrix()
                glTranslatef(*node.pos)
                gluSphere(self.quadratic,0.1,12,12)
                glPopMatrix()
        # Swap buffers to show the scene.
        glPopMatrix()
        self.SwapBuffers()
        return
    def InitGL(self):
        # Lighting.
        glDisable(GL_LIGHTING)
        # Clear color / depth.
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        # Projection.
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.Size[0],
                0.0, self.Size[1],
                -0.01, 10.0)
        # Model view.
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # Get a reusable quadric.
        self.quadratic = gluNewQuadric()
        gluQuadricNormals(self.quadratic, GLU_SMOOTH)
        gluQuadricTexture(self.quadratic, GL_TRUE)
        return
