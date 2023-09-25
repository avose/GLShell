from wx.glcanvas import GLCanvas
from OpenGL.GLU import *
from OpenGL.GL import *
import datetime
import numpy as np
import math
import sys
import wx

from glsGLBuffer import glsGLBuffer
from glsGLFont import glsGLFont
from glsFDP import fdpNode
from glsFDP import fdpGraph
from glsDirTree import glsFile
from glsDirTree import glsDir
from glsIcons import glsIcons

################################################################

class glsGraphPopupMenu(wx.Menu):
    ID_EXIT = 1000
    def __init__(self, parent):
        super(glsGraphPopupMenu, self).__init__()
        self.icons = glsIcons()
        item = wx.MenuItem(self, self.ID_EXIT, 'Close Graph')
        item.SetBitmap(self.icons.Get('chart_organisation_delete'))
        self.Append(item)
        return

################################################################

class glsGraphCanvas(GLCanvas):
    def __init__(self, parent, dirtree, size, settings, callback_close):
        #glattrs = wx.glcanvas.GLAttributes()
        GLCanvas.__init__(self, parent, id=-1, size=size)
        self.dirtree = dirtree
        self.settings = settings
        self.callback_close = callback_close
        self.graph_3D = settings.Get('graph_3D')
        self.settings.AddWatcher(self.OnChangeSettings)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        self.Bind(wx.EVT_MENU, self.OnMenuItem)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.keys_down = {}
        self.translate = np.array((0, 0, 0), dtype=np.single)
        self.rotate = 0
        self.glctx = None
        self.fps_max = 100
        self.mouse_down = [False, False, False, False]
        self.mouse_pos = np.array([0, 0],dtype=np.single)
        self.zoom = 20.0
        self.time_draw = 1
        self.time_fdp = 1
        self.selection = False
        self.glctx = wx.glcanvas.GLContext(self)
        self.SetCurrent(self.glctx)
        self.InitGL()
        self.glfont = glsGLFont(wx.FontInfo(10).FaceName("Monospace"))
        self.closing = False
        self.pushframes_done = False
        wx.CallLater(10, self.PushFrames)
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
        return
    def OnChangeSettings(self, settings):
        return
    def OnDestroy(self, event):
        self.settings.RemoveWatcher(self.OnChangeSettings)
        return
    def OnSize(self, event):
        self.SetMatrices()
        return
    def OnChar(self, event):
        key_map = { wx.WXK_UP:'w', wx.WXK_LEFT:'a', wx.WXK_DOWN:'s', wx.WXK_RIGHT:'d' }
        key = event.GetKeyCode()
        if key < 256:
            key = chr(key)
        elif key in key_map:
            key = key_map[key]
        if wx.WXK_TAB in self.keys_down:
            #    self.rotate += dx + dy
            if key == 'w':
                self.rotate += 5
            elif key == 'a':
                self.rotate -= 5
            elif key == 's':
                self.rotate -= 5
            elif key == 'd':
                self.rotate += 5
        else:
            if key == 'w':
                self.translate[1] += 5
            elif key == 'a':
                self.translate[0] -= 5
            elif key == 's':
                self.translate[1] -= 5
            elif key == 'd':
                self.translate[0] += 5
        return
    def OnKeyDown(self, event):
        self.keys_down[event.GetKeyCode()] = True
        if wx.WXK_CONTROL in self.keys_down or wx.WXK_SHIFT in self.keys_down:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        event.Skip()
        return
    def OnKeyUp(self, event):
        if event.GetKeyCode() in self.keys_down:
            del self.keys_down[event.GetKeyCode()]
        if wx.WXK_SHIFT not in self.keys_down and wx.WXK_CONTROL not in self.keys_down:
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        event.Skip()
        return
    def OnLeftDown(self, event):
        if wx.WXK_CONTROL in self.keys_down:
            self.selection = True
        self.mouse_pos = event.GetPosition()
        self.mouse_down[0] = True
        event.Skip()
        return
    def OnLeftUp(self, event):
        self.OnMove(event)
        self.mouse_down[0] = False
        return
    def OnMiddleDown(self, event):
        self.mouse_pos = event.GetPosition()
        self.mouse_down[2] = True
        return
    def OnMiddleUp(self, event):
        self.OnMove(event)
        self.mouse_down[2] = False
        return
    def OnRightDown(self, event):
        self.PopupMenu(glsGraphPopupMenu(self), event.GetPosition())
        return
    def OnMove(self, event):
        if (wx.WXK_CONTROL in self.keys_down or
            wx.WXK_SHIFT in self.keys_down):
            return
        pos = event.GetPosition()
        dx = (self.mouse_pos[0] - pos[0])*0.3
        dy = (self.mouse_pos[1] - pos[1])*0.3
        if self.mouse_down[0] and wx.WXK_TAB not in self.keys_down:
            self.translate += np.array((-dx, dy, 0), dtype=np.single)
        if self.mouse_down[2] or self.mouse_down[0] and wx.WXK_TAB in self.keys_down:
            self.rotate += dx + dy
        self.mouse_pos = pos
        return
    def OnWheel(self, event):
        if event.GetWheelRotation() < 0:
            self.zoom *= 0.95
        else:
            self.zoom /= 0.95
        return
    def OnMenuItem(self, event):
        id = event.GetId()
        if id == glsGraphPopupMenu.ID_EXIT:
            self.OnClose()
        return
    def OnPaint(self, event):
        start = datetime.datetime.now()
        self.OnDraw()
        self.time_draw = datetime.datetime.now() - start
        self.time_draw = self.time_draw.total_seconds()
        return
    def ProcessSelected(self, selected):
        selected = [ (s[0], s[2][0]) for s in selected if len(s[2]) == 1 ]
        selected.sort(key=lambda x: x[0])
        if len(selected) == 0:
            return
        selected = selected[0][1] - 1
        gthread = self.dirtree.thread
        graph = gthread.get_graph()
        with gthread.lock:
            nlist = list(graph.nodes.values())
            nlist[selected].selected = not nlist[selected].selected
        return
    def PushFrames(self):
        if self.closing:
            self.pushframes_done = True
            return
        start = datetime.datetime.now()
        if self.selection:
            select_max = 100000
            select = np.zeros((select_max), dtype=np.uint32)
            self.glctx.SetCurrent(self)
            glSelectBuffer(select_max, select);
            glRenderMode(GL_SELECT)
            self.OnDraw()
            self.selection = False
            selected = glRenderMode(GL_RENDER);
            self.ProcessSelected(selected);
        self.OnDraw()
        self.time_draw = (datetime.datetime.now() - start).total_seconds()
        next_draw = 1000.0/self.fps_max - self.time_draw
        next_draw = 5 if next_draw <= 5 else int(next_draw)
        wx.CallLater(next_draw, self.PushFrames)
        return
    def DrawGraph(self):
        # Get graph and its settings.
        gthread = self.dirtree.thread
        graph   = gthread.get_graph()
        # Draw graph while holding the lock.
        with gthread.lock:
            if gthread.dims == 2:
                self.Set2D()
                self.graph_3D = False
            elif gthread.dims == 3:
                self.Set3D()
                self.graph_3D = True
            red = [1.0, 0.0, 0.0, 1.0]
            grn = [0.0, 1.0, 0.0, 1.0]
            blu = [0.0, 0.0, 1.0, 1.0]
            ylw = [1.0, 1.0, 0.0, 1.0]
            prp = [1.0, 0.3, 1.0, 1.0]
            # Apply zoom and rotation.
            if self.graph_3D:
                zoom = self.zoom * 0.05
                glTranslatef(self.translate[0]/self.Size[0]*5*self.zoom,
                             self.translate[1]/self.Size[1]*5*self.zoom, 0)
                glRotatef(self.rotate, 0, 1, 0)
            else:
                glTranslatef(*self.translate, 0)
                glTranslatef(self.Size[0]/2.0, self.Size[1]/2.0, 0)
                glRotatef(self.rotate, 0, 0, 1)
                glTranslatef(-self.Size[0]/2.0, -self.Size[1]/2.0, 0)
                zoom = self.zoom
            # Save 2D screen coordinates for the nodes.
            self.Record3DTo2DMatrices()
            pos_nodes = []
            # Draw edges.
            glColor4fv(grn)
            glBegin(GL_LINES)
            for ei in range(graph.np_edges.shape[0]):
                e = graph.np_edges[ei]
                for n in e:
                    pos = np.array(graph.np_nodes[n])
                    pos *= zoom
                    if not self.graph_3D:
                        pos[0] += self.Size[0]/2.0
                        pos[1] += self.Size[1]/2.0
                    glVertex3fv(pos)
            glEnd()
            # Draw nodes.
            if self.selection:
                glInitNames();
                glPushName(0);
            for ni,node in enumerate(graph.nodes.values()):
                pos = np.array(graph.np_nodes[ni])
                pos *= zoom
                if not self.graph_3D:
                    pos[0] += self.Size[0]/2.0
                    pos[1] += self.Size[1]/2.0
                if node.selected:
                    glColor4fv(red)
                    size = 20.0
                elif node.search_result:
                    glColor4fv((1,1,1,1))
                    size = 20.0
                    pass
                else:
                    if isinstance(node, glsDir):
                        glColor4fv(prp)
                        size = 10.0
                    else:
                        glColor4fv(blu)
                        size = 8.0
                glPointSize(size)
                if self.selection:
                    glLoadName(ni+1)
                glBegin(GL_POINTS)
                glVertex3fv(pos)
                glEnd()
                pos_nodes.append(self.Project3DTo2D(pos))
            if self.selection:
                glLoadName(0)
            # Draw labels.
            self.Set2D()
            for ni,node in enumerate(graph.nodes.values()):
                pos = pos_nodes[ni]
                if pos[2] > 1:
                    continue
                if node.selected:
                    bckg = True
                    yoff = 20
                    color = red
                    label = True
                elif node.search_result:
                    bckg = True
                    yoff = 20
                    color = (1,1,1,1)
                    label = True
                else:
                    bckg = False
                    yoff = 10
                    if self.graph_3D:
                        if isinstance(node, glsDir):
                            color = ylw
                            label = True
                        else:
                            color = prp
                            label = True if self.zoom >= 25 else False
                    else:
                        if isinstance(node, glsDir):
                            color = ylw
                            label = True
                        else:
                            color = prp
                            label = True if zoom >= 10 else False
                if label:
                    self.glfont.DrawText(node.name, [pos[0], pos[1]+yoff, pos[2]],
                                         color, True, bckg)
        return
    def DrawStats(self):
        self.Set2D()
        red = [1.0, 0.0, 0.0 ,1.0]
        grn = [0.0, 1.0, 0.0 ,1.0]
        blu = [0.0, 0.0, 1.0 ,1.0]
        ylw = [1.0, 1.0, 0.0 ,1.0]
        glColor4fv([0,0,0,0.75])
        glBegin(GL_POLYGON)
        glVertex3fv([0,   self.Size[1]-2*self.glfont.char_h, 0])
        glVertex3fv([0,   self.Size[1],                      0])
        glVertex3fv([140, self.Size[1],                      0])
        glVertex3fv([140, self.Size[1]-2*self.glfont.char_h, 0])
        glEnd()
        gthread = self.dirtree.thread
        self.time_fdp = gthread.get_time()
        if self.time_fdp == 0:
            fps_fdp = 0
        else:
            fps_fdp = 1.0 / self.time_fdp
        fps_fdp = "FPS(fdp): %.2f "%(fps_fdp)
        fps_pos = [0, self.Size[1]-self.glfont.char_h, 0]
        self.glfont.DrawText(fps_fdp, fps_pos, grn)
        fps_ogl = 1.0 / self.time_draw
        fps_ogl = "FPS(ogl): %.2f"%(fps_ogl)
        fps_pos = [0, self.Size[1]-2*self.glfont.char_h, 0]
        self.glfont.DrawText(fps_ogl, fps_pos, grn)
        return
    def OnDraw(self):
        self.SetCurrent(self.glctx)
        self.SetMatrices()
        # Clear buffer.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Draw the graph.
        self.DrawGraph()
        # Draw stats.
        self.DrawStats()
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
        glViewport(0, 0, self.Size[0], self.Size[1])
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.selection:
            self.viewport = glGetIntegerv(GL_VIEWPORT)
            gluPickMatrix(self.mouse_pos[0], self.viewport[3]-self.mouse_pos[1],
                          20, 20, self.viewport);
        glOrtho(0.0, self.Size[0],
                0.0, self.Size[1],
                -0.01, 10.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        return
    def Set3D(self):
        glViewport(0, 0, self.Size[0], self.Size[1])
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.selection:
            self.viewport = glGetIntegerv(GL_VIEWPORT)
            gluPickMatrix(self.mouse_pos[0], self.viewport[3]-self.mouse_pos[1],
                          20, 20, self.viewport);
        gluPerspective(75, self.Size[0]/self.Size[1], 1, 1000);
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0.0,  0.0, 10.0,   # eye
                  0.0,  0.0,  0.0,   # center
                  0.0,  1.0,  0.0 ); # up vector
        return
    def SetMatrices(self):
        if self.graph_3D:
            self.Set3D()
        else:
            self.Set2D()
        return
    def OnClose(self, event=None):
        if not self.closing:
            self.closing = True
            self.settings.RemoveWatcher(self.OnChangeSettings)
            self.dirtree.thread.stop()
            self.dirtree.thread.join()
        if not self.pushframes_done:
            wx.CallLater(10, self.OnClose)
            return
        self.callback_close()
        return

################################################################

class glsGraphPanel(wx.Window):
    def __init__(self, parent, dirtree, settings, callback_close):
        # Call super.
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsGraphPanel, self).__init__(parent, style=style)
        self.dirtree = dirtree
        self.settings = settings
        self.callback_close = callback_close
        self.SetMinSize( (320,320) )
        self.SetBackgroundColour( (255,0,0) )
        self.graph_canvas = None
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Show(True)
        return
    def StartGraph(self):
        if self.graph_canvas is None:
            self.graph_canvas = glsGraphCanvas(self, self.dirtree, size=(320,320),
                                               settings=self.settings,
                                               callback_close=self.CloseGraph)
        return
    def OnSize(self, event=None):
        if self.graph_canvas is not None:
            self.graph_canvas.SetSize(0, 0, self.Size[0], self.Size[1])
        return
    def CloseGraph(self):
        self.callback_close(self)
        return
    def OnClose(self, event=None):
        if self.graph_canvas is not None:
            self.graph_canvas.OnClose()
        return

################################################################
