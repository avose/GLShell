from wx.glcanvas import GLCanvas
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
from itertools import product
import numpy as np
import sys, math
import wx
import datetime

from glsGLBuffer import glsGLBuffer
from glsGLText import glsGLTextSizer
from glsGLText import glsGLText
from glsFDP import fdpNode
from glsFDP import fdpGraph
from glsProject import glsFile
from glsProject import glsDir

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
    time_draw  = datetime.timedelta(0, 1, 0)
    time_fdp   = datetime.timedelta(0, 1, 0)
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
            finfo = wx.FontInfo(10).FaceName("Monospace")
            self.textsizer.SetFont(finfo)
            tw,th = self.textsizer.TextSize(text)
            buff = glsGLBuffer(tw,th)
            self.textbuff = glsGLText(buff,finfo,(255,255,0,255),text)
            self.init = True
        self.SetCurrent(self.glctx)
        start = datetime.datetime.now()
        self.OnDraw()
        self.time_draw = datetime.datetime.now() - start
        return
    def Tick(self,event):
        if self.project is not None and len(self.project.roots) > 0:
            root = self.project.roots[0]
            graph = root.graph
            start = datetime.datetime.now()
            graph.tick(speed=(0.1/self.fps))
            self.time_fdp = datetime.datetime.now() - start
        self.OnDraw()
        return
    def OnDraw(self):
        # Clear buffer.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        red = [1.0, 0.0, 0.0 ,1.0]
        grn = [0.0, 1.0, 0.0 ,1.0]
        blu = [0.0, 0.0, 1.0 ,1.0]
        ylw = [1.0, 1.0, 0.0 ,1.0]
        # Draw stats.
        self.textbuff.SetColor(grn)
        fps_fdp = 1.0 / self.time_fdp.total_seconds()
        fps_fdp = "FPS(fdp): %.2f "%(fps_fdp)
        fps_pos = [0, self.Size[1]-self.textbuff.height, 0]
        self.textbuff.DrawGL(fps_pos, text=fps_fdp)
        fps_ogl = 1.0 / self.time_draw.total_seconds()
        fps_ogl = "FPS(ogl): %.2f"%(fps_ogl)
        fps_pos = [0, self.Size[1]-2*self.textbuff.height, 0]
        self.textbuff.DrawGL(fps_pos, text=fps_ogl)
        fps_tot = 1.0 / (self.time_draw.total_seconds() +
                         self.time_fdp.total_seconds())
        fps_tot = "FPS(tot): %.2f"%(fps_tot)
        fps_pos = [0, self.Size[1]-3*self.textbuff.height, 0]
        self.textbuff.DrawGL(fps_pos, text=fps_tot)
        self.textbuff.SetColor(ylw)
        # Apply zoom and rotation.
        glPushMatrix()
        glTranslatef(*self.translate, 0)
        # !!avose: Rotation need to be fixed to not rotate text!!
        glTranslatef(self.Size[0]/2.0, self.Size[1]/2.0, 0)
        glRotatef(self.rotate[0], 0, 0, 1)
        glTranslatef(-self.Size[0]/2.0, -self.Size[1]/2.0, 0)
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
                glPushMatrix()
                pos = np.array(node.pos)
                pos[0] = pos[0]*self.zoom + self.Size[0]/2.0
                pos[1] = pos[1]*self.zoom + self.Size[1]/2.0
                glTranslatef(*pos)
                if isinstance(node, glsDir):
                    glColor4fv(red)
                    size = 10.0
                else:
                    glColor4fv(blu)
                    size = 8.0
                glPointSize(size)
                glBegin(GL_POINTS)
                glVertex3fv([0,0,0])
                glEnd()
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
        # Enable alpha blending.
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glEnable(GL_LINE_SMOOTH);
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
        glEnable(GL_POINT_SMOOTH);
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST);
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
