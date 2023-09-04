from wx.glcanvas import GLCanvas
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
from itertools import product
import numpy as np
import sys, math
import wx

from glsGLBuffer import glsGLBuffer
from glsGLText import glsGLTextSizer
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
    init       = False
    glctx      = None
    quadratic  = None
    project    = None
    textbuff   = None
    textsizer  = None
    fps        = 10
    mouse_down = [False, False, False, False]
    mouse_pos  = np.array([0, 0],dtype=np.single)
    translate  = np.array([0, 0],dtype=np.single)
    rotate     = np.array([0, 0],dtype=np.single)
    zoom       = 20.0
    def __init__(self, parent, pos, size):
        #glattrs = wx.glcanvas.GLAttributes()
        GLCanvas.__init__(self, parent, id=-1, pos=pos, size=size)
        self.textsizer = glsGLTextSizer()
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.Tick, self.timer)
        self.timer.Start(int(1000.0/self.fps))
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        return
    def OnLeftDown(self,event):
        self.mouse_pos = event.GetPosition()
        self.mouse_down[0] = True
        return
    def OnLeftUp(self,event):
        self.OnMove(event)
        self.mouse_down[0] = False
        return
    def OnRightDown(self,event):
        self.mouse_pos = event.GetPosition()
        self.mouse_down[3] = True
        return
    def OnRightUp(self,event):
        self.OnMove(event)
        self.mouse_down[3] = False
        return
    def OnMove(self,event):
        pos = event.GetPosition()
        if self.mouse_down[0]:
            self.translate += (-(self.mouse_pos[0] - pos[0]),
                                (self.mouse_pos[1] - pos[1]))
        if self.mouse_down[3]:
            self.rotate += ((self.mouse_pos[0] - pos[0])*0.3,
                            (self.mouse_pos[1] - pos[1])*0.3)
        self.mouse_pos = pos
        return
    def OnWheel(self,event):
        if event.GetWheelRotation() < 0:
            self.zoom -= 1
        else:
            self.zoom += 1
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
            text = "string with length of max length for file and directory names"
            finfo = wx.FontInfo(11)
            self.textsizer.SetFont(finfo)
            tw,th = self.textsizer.TextSize(text)
            buff = glsGLBuffer(tw,th)
            self.textbuff = glsGLText(buff,finfo,(255,255,0,255),text)
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
        # Apply zoom and rotation.
        glPushMatrix()
        glTranslatef(*self.translate, 0)
        # !!avose: Rotation need to be fixed to not rotate text!!
        glTranslatef(self.Size[0]/2.0, self.Size[1]/2.0, 0)
        glRotatef(self.rotate[0], 0, 0, 1)
        glTranslatef(-self.Size[0]/2.0, -self.Size[1]/2.0, 0)
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
                    pos = np.array(graph.nodes[n].pos)
                    pos[0] = pos[0]*self.zoom + self.Size[0]/2.0
                    pos[1] = pos[1]*self.zoom + self.Size[1]/2.0
                    glVertex3fv(pos)
            glEnd()
            # Draw nodes.
            for node in graph.nodes.values():
                glColor4fv(red)
                glPushMatrix()
                pos = np.array(node.pos)
                pos[0] = pos[0]*self.zoom + self.Size[0]/2.0
                pos[1] = pos[1]*self.zoom + self.Size[1]/2.0
                glTranslatef(*pos)
                gluSphere(self.quadratic,0.1*20.0,12,12)
                glPopMatrix()
                self.textbuff.DrawGL(pos,text=node.name,center=True)
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
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
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
