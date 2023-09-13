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
        self.graph_2D = settings.graph_2D
        self.graph_3D = settings.graph_3D
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
        self.translate = np.array((0, 0, 0), dtype=np.single)
        self.rotate = 0
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
        self.SetMatrices()
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
        dx = (self.mouse_pos[0] - pos[0])*0.3
        dy = (self.mouse_pos[1] - pos[1])*0.3
        if self.mouse_down[0]:
            self.translate += np.array((-dx, dy, 0), dtype=np.single)
        if self.mouse_down[3]:
            self.rotate += dx + dy
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
        if self.graph_2D:
            self.Set2D()
        elif self.graph_3D:
            self.Set3D()
        red = [1.0, 0.0, 0.0 ,1.0]
        grn = [0.0, 1.0, 0.0 ,1.0]
        blu = [0.0, 0.0, 1.0 ,1.0]
        ylw = [1.0, 1.0, 0.0 ,1.0]
        self.textbuff.SetColor(ylw)
        # Apply zoom and rotation.
        if self.graph_2D:
            glTranslatef(*self.translate, 0)
            glTranslatef(self.Size[0]/2.0, self.Size[1]/2.0, 0)
            glRotatef(self.rotate, 0, 0, 1)
            glTranslatef(-self.Size[0]/2.0, -self.Size[1]/2.0, 0)
            zoom = self.zoom
        elif self.graph_3D:
            zoom = self.zoom * 0.05
            glTranslatef(self.translate[0]/self.Size[0]*5*self.zoom,
                         self.translate[1]/self.Size[1]*5*self.zoom, 0)
            glRotatef(self.rotate, 0, 1, 0)
        # Draw the graph.
        self.Record3DTo2DMatrices()
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
                        pos *= zoom
                        if self.graph_2D:
                            pos[0] += self.Size[0]/2.0
                            pos[1] += self.Size[1]/2.0
                        glVertex3fv(pos)
                glEnd()
                # Draw nodes.
                pos_nodes = []
                for ni,node in enumerate(graph.nlist):
                    pos = np.array(graph.np_nodes[ni])
                    pos *= zoom
                    if self.graph_2D:
                        pos[0] += self.Size[0]/2.0
                        pos[1] += self.Size[1]/2.0
                    if isinstance(node, glsDir):
                        glColor4fv(red)
                        size = 10.0
                    else:
                        glColor4fv(blu)
                        size = 8.0
                    glPointSize(size)
                    glBegin(GL_POINTS)
                    glVertex3fv(pos)
                    glEnd()
                    pos_nodes.append(self.Project3DTo2D(pos))
                # Draw labels.
                self.Set2D()
                for ni,node in enumerate(graph.nlist):
                    pos = pos_nodes[ni]
                    if self.graph_3D:
                        if isinstance(node, glsDir):
                            label = True
                        else:
                            label = True if self.zoom >= 10 else False
                    elif self.graph_2D:
                        if isinstance(node, glsDir):
                            label = True
                        else:
                            label = True if zoom >= 10 else False
                    if label is True:
                        self.textbuff.DrawGL((pos[0], pos[1]+10, 0),
                                             text=node.name, center=True)
        # Draw stats.
        self.Set2D()
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
    def Project3DTo2D(self, pos):
        return gluProject(*pos, self.model_view, self.projection, self.viewport)
    def Record3DTo2DMatrices(self):
        self.model_view = glGetDoublev(GL_MODELVIEW_MATRIX)
        self.projection = glGetDoublev(GL_PROJECTION_MATRIX)
        self.viewport   = glGetIntegerv(GL_VIEWPORT)
        return
    def Set2D(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.Size[0],
                0.0, self.Size[1],
                -0.01, 10.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        return
    def Set3D(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75, self.Size[0]/self.Size[1], 1, 1000);
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0.0,  0.0, 10.0,  # eye
                  0.0,  0.0,  0.0,   # center
                  0.0,  1.0,  0.0 ); # up vector
        return
    def SetMatrices(self):
        # Projection and model view.
        if self.graph_2D:
            self.Set2D()
        elif self.graph_3D:
            self.Set3D()
        # Viewport.
        glViewport(0, 0, self.Size[0],self.Size[1])
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
        # Set projection and model view.
        self.SetMatrices()
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
