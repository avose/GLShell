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
    fps_max    = 100
    mouse_down = [False, False, False, False]
    mouse_pos  = np.array([0, 0],dtype=np.single)
    translate  = np.array([0, 0],dtype=np.single)
    rotate     = np.array([0, 0],dtype=np.single)
    zoom       = 20.0
    time_draw  = 1
    time_fdp   = 1
    def __init__(self, parent, size, settings):
        #glattrs = wx.glcanvas.GLAttributes()
        GLCanvas.__init__(self, parent, id=-1, size=size)
        self.parent = parent
        self.settings = settings
        self.settings.AddWatcher(self.OnChangeSettings)
        self.textsizer = glsGLTextSizer()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        wx.CallLater(10, self.PushFrames)
        return
    def OnChangeSettings(self, settings):
        return
    def OnClose(self, event):
        self.settings.RemoveWatcher(self.OnChangeSettings)
        return
    def OnDestroy(self, event):
        self.settings.RemoveWatcher(self.OnChangeSettings)
        return
    def OnSize(self, event):
        # Projection.
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.Size[0],
                0.0, self.Size[1],
                -0.01, 10.0)
        # Model view.
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # Viewport.
        glViewport(0,0,self.Size[0],self.Size[1])
        return
    def OnLeftDown(self, event):
        self.mouse_pos = event.GetPosition()
        self.mouse_down[0] = True
        return
    def OnLeftUp(self, event):
        self.OnMove(event)
        self.mouse_down[0] = False
        return
    def OnRightDown(self, event):
        self.mouse_pos = event.GetPosition()
        self.mouse_down[3] = True
        return
    def OnRightUp(self, event):
        self.OnMove(event)
        self.mouse_down[3] = False
        return
    def OnMove(self, event):
        pos = event.GetPosition()
        if self.mouse_down[0]:
            self.translate += (-(self.mouse_pos[0] - pos[0]),
                                (self.mouse_pos[1] - pos[1]))
        if self.mouse_down[3]:
            self.rotate += ((self.mouse_pos[0] - pos[0])*0.3,
                            (self.mouse_pos[1] - pos[1])*0.3)
        self.mouse_pos = pos
        return
    def OnWheel(self, event):
        if event.GetWheelRotation() < 0:
            self.zoom *= 0.9
        else:
            self.zoom *= 1.1
        return
    def AddProject(self, proj):
        self.project = proj
        return
    def OnPaint(self, event):
        if not self.init:
            self.glctx = wx.glcanvas.GLContext(self)
            self.SetCurrent(self.glctx)
            glutInit(sys.argv);
            self.InitGL()
            text = "string with length of max length for file and directory names"
            finfo = wx.FontInfo(10).FaceName("Monospace").Bold()
            self.textsizer.SetFont(finfo)
            tw,th = self.textsizer.TextSize(text)
            buff = glsGLBuffer(tw,th)
            self.textbuff = glsGLText(buff,finfo,(255,255,0,255),text)
            self.init = True
        self.SetCurrent(self.glctx)
        start = datetime.datetime.now()
        self.OnDraw()
        self.time_draw = datetime.datetime.now() - start
        self.time_draw = self.time_draw.total_seconds()
        return
    def PushFrames(self):
        start = datetime.datetime.now()
        if self.init:
            self.OnDraw()
        self.time_draw = (datetime.datetime.now() - start).total_seconds()
        next_draw = 1000.0/self.fps_max - self.time_draw
        next_draw = 5 if next_draw <= 5 else int(next_draw)
        wx.CallLater(next_draw, self.PushFrames)
        return
    def OnDraw(self):
        # Clear buffer.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        red = [1.0, 0.0, 0.0 ,1.0]
        grn = [0.0, 1.0, 0.0 ,1.0]
        blu = [0.0, 0.0, 1.0 ,1.0]
        ylw = [1.0, 1.0, 0.0 ,1.0]
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
            gthread = self.project.threads[0]
            graph   = gthread.get_graph()
            # Draw graph while holding the lock.
            with gthread.lock:
                # Draw edges.
                glColor4fv(grn)
                glBegin(GL_LINES)
                for ei in range(graph.np_edges.shape[0]):
                    e = graph.np_edges[ei]
                    for n in e:
                        pos = np.array(graph.np_nodes[n])
                        pos[0] = pos[0]*self.zoom + self.Size[0]/2.0
                        pos[1] = pos[1]*self.zoom + self.Size[1]/2.0
                        glVertex3fv(pos)
                glEnd()
                # Draw nodes.
                for ni,node in enumerate(graph.nlist):
                    glPushMatrix()
                    pos = np.array(graph.np_nodes[ni])
                    pos[0] = pos[0]*self.zoom + self.Size[0]/2.0
                    pos[1] = pos[1]*self.zoom + self.Size[1]/2.0
                    glTranslatef(*pos)
                    if isinstance(node, glsDir):
                        glColor4fv(red)
                        self.textbuff.SetColor([1,0,1,1])
                        size = 10.0
                        label = True
                    else:
                        glColor4fv(blu)
                        self.textbuff.SetColor(ylw)
                        size = 8.0
                        label = True if self.zoom >= 10 else False
                    glPointSize(size)
                    glBegin(GL_POINTS)
                    glVertex3fv([0,0,0])
                    glEnd()
                    glPopMatrix()
                    if label is True:
                        pos[1] += 10
                        self.textbuff.DrawGL(pos,text=node.name,center=True)
        glPopMatrix()
        # Draw stats.
        glColor4fv([0,0,0,0.75])
        glBegin(GL_QUADS)
        glVertex3fv([0,   self.Size[1]-2*self.textbuff.height, 0])
        glVertex3fv([0,   self.Size[1],                        0])
        glVertex3fv([140, self.Size[1],                        0])
        glVertex3fv([140, self.Size[1]-2*self.textbuff.height, 0])
        glEnd()
        self.textbuff.SetColor(grn)
        if self.project is not None and len(self.project.roots) > 0:
            gthread = self.project.threads[0]
            self.time_fdp = gthread.get_time()
            if self.time_fdp == 0:
                fps_fdp = 0
            else:
                fps_fdp = 1.0 / self.time_fdp
        else:
            fps_fdp = 0.0
        fps_fdp = "FPS(fdp): %.2f "%(fps_fdp)
        fps_pos = [0, self.Size[1]-self.textbuff.height, 0]
        self.textbuff.DrawGL(fps_pos, text=fps_fdp)
        fps_ogl = 1.0 / self.time_draw
        fps_ogl = "FPS(ogl): %.2f"%(fps_ogl)
        fps_pos = [0, self.Size[1]-2*self.textbuff.height, 0]
        self.textbuff.DrawGL(fps_pos, text=fps_ogl)
        # Swap buffers to show the scene.
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
        # Viewport.
        glViewport(0,0,self.Size[0],self.Size[1])
        # Get a reusable quadric.
        self.quadratic = gluNewQuadric()
        gluQuadricNormals(self.quadratic, GLU_SMOOTH)
        gluQuadricTexture(self.quadratic, GL_TRUE)
        return

class glsGraphPanel(wx.Window):
    def __init__(self, parent, settings, close_handler):
        # Call super.
        box_main = wx.BoxSizer(wx.VERTICAL)
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsGraphPanel, self).__init__(parent, style=style)
        self.SetMinSize( (320,320) )
        self.SetBackgroundColour( (255,0,0) )
        self.graph_canvas = glsGraphCanvas(self, size=(320,320), settings=settings)
        box_main.Add(self.graph_canvas, 1, wx.ALIGN_LEFT | wx.ALL | wx.EXPAND, 0)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def AddProject(self, proj):
        self.graph_canvas.AddProject(proj)
        return
    def OnSize(self, event):
        self.graph_canvas.SetSize(0,0,self.Size[0],self.Size[1])
        return
