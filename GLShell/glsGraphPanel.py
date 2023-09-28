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
from glsDirTree import glsDirTree
from glsIcons import glsIcons

################################################################

class glsGraphPopupMenu(wx.Menu):
    ID_EXIT     = 1000
    ID_SEL_ALL  = 1001
    ID_SEL_NONE = 1002
    ID_SEL_IVRT = 1003
    def __init__(self, parent):
        super(glsGraphPopupMenu, self).__init__()
        self.icons = glsIcons()
        item = wx.MenuItem(self, self.ID_SEL_ALL, 'Select All')
        item.SetBitmap(self.icons.Get('chart_line_add'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SEL_IVRT, 'Select Inverse')
        item.SetBitmap(self.icons.Get('chart_line'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SEL_NONE, 'Select None')
        item.SetBitmap(self.icons.Get('chart_line_delete'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_EXIT, 'Close Graph')
        item.SetBitmap(self.icons.Get('chart_organisation_delete'))
        self.Append(item)
        return

################################################################

class glsGraphCanvas(GLCanvas):
    # Color constatns.
    red = [1.0, 0.0, 0.0, 1.0]
    grn = [0.0, 1.0, 0.0, 1.0]
    blu = [0.0, 0.0, 1.0, 1.0]
    ylw = [1.0, 1.0, 0.0, 1.0]
    prp = [1.0, 0.3, 1.0, 1.0]
    wht = [1.0, 1.0, 1.0, 1.0]
    def __init__(self, parent, dirtree, size, settings, callback_close):
        # Initialize glsGraphCanvas.
        GLCanvas.__init__(self, parent, id=-1, size=size)
        self.dirtree = dirtree
        self.gthread = self.dirtree.thread
        self.lock = self.gthread.lock
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
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
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
        self.selection_box = [ [None, None], [None, None]]
        self.glctx = wx.glcanvas.GLContext(self)
        self.SetCurrent(self.glctx)
        self.InitGL()
        font_name = self.settings.Get('graph_font')
        font_size = self.settings.Get('graph_font_size')
        self.glfont = glsGLFont(wx.FontInfo(font_size).FaceName(font_name))
        self.closing = False
        self.pushframes_done = False
        self.node_styles = { glsDirTree.KIND_DIR: (self.prp, 10.0),
                             glsDirTree.KIND_FILE: (self.blu, 8.0),
                             glsDirTree.KIND_SELECT: (self.red, 15.0),
                             glsDirTree.KIND_RESULT: (self.wht, 15.0) }
        wx.CallLater(10, self.PushFrames)
        return
    def InitGL(self):
        # Initialize OpenGL settings.
        glDisable(GL_LIGHTING)
        # Lighting, clear color, clear depth.
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(0.0)
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
        # Handle settings change.
        font_name = self.settings.Get('graph_font')
        font_size = self.settings.Get('graph_font_size')
        self.glfont = glsGLFont(wx.FontInfo(font_size).FaceName(font_name))
        return
    def OnSize(self, event):
        # Handle resize event.
        self.SetMatrices()
        return
    def OnChar(self, event):
        # Handle keyboard key character event.
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
        # Handle keyboard key down event.
        self.keys_down[event.GetKeyCode()] = True
        if wx.WXK_CONTROL in self.keys_down or wx.WXK_SHIFT in self.keys_down:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        event.Skip()
        return
    def OnKeyUp(self, event):
        # Handle keyboard key up event.
        if event.GetKeyCode() in self.keys_down:
            del self.keys_down[event.GetKeyCode()]
        if wx.WXK_SHIFT not in self.keys_down and wx.WXK_CONTROL not in self.keys_down:
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        event.Skip()
        return
    def OnLeftDown(self, event):
        # Handle left mouse button down event.
        self.mouse_pos = event.GetPosition()
        self.mouse_down[0] = True
        if wx.WXK_CONTROL in self.keys_down:
            self.selection = True
        if wx.WXK_SHIFT in self.keys_down:
            self.selection_box = [ [self.mouse_pos[0], self.mouse_pos[1]],
                                   [None, None] ]
        event.Skip()
        return
    def OnLeftUp(self, event):
        # Handle left mouse button up event.
        if self.SelectionBoxValid():
            self.selection = True
        else:
            self.selection_box = [ [None, None], [None, None]]
        self.OnMouseMove(event)
        self.mouse_down[0] = False
        return
    def OnMiddleDown(self, event):
        # Handle middle mouse button down event.
        self.mouse_pos = event.GetPosition()
        self.mouse_down[2] = True
        return
    def OnMiddleUp(self, event):
        # Handle middle mouse button up event.
        self.OnMouseMove(event)
        self.mouse_down[2] = False
        return
    def OnRightDown(self, event):
        # Handle right mouse button down event.
        self.PopupMenu(glsGraphPopupMenu(self), event.GetPosition())
        return
    def OnMouseMove(self, event):
        # Handle mouse motion event.
        pos = event.GetPosition()
        if self.SelectionBoxStarted():
            self.selection_box[1] = [ pos[0], pos[1] ]
            self.mouse_pos = pos
            return
        if (wx.WXK_CONTROL in self.keys_down or
            wx.WXK_SHIFT in self.keys_down):
            return
        dx = (self.mouse_pos[0] - pos[0])*0.3
        dy = (self.mouse_pos[1] - pos[1])*0.3
        if self.mouse_down[0] and wx.WXK_TAB not in self.keys_down:
            self.translate += np.array((-dx, dy, 0), dtype=np.single)
        if self.mouse_down[2] or self.mouse_down[0] and wx.WXK_TAB in self.keys_down:
            self.rotate += dx + dy
        self.mouse_pos = pos
        return
    def OnWheel(self, event):
        # Handle zoom / mouse wheel event.
        if event.GetWheelRotation() < 0:
            self.zoom *= 0.95
        else:
            self.zoom /= 0.95
        return
    def OnMenuItem(self, event):
        # Handle menu item event.
        menu_id = event.GetId()
        if menu_id == glsGraphPopupMenu.ID_EXIT:
            self.OnClose()
        elif menu_id == glsGraphPopupMenu.ID_SEL_ALL:
            for node in self.IterateNodes():
                node.selected = True
        elif menu_id == glsGraphPopupMenu.ID_SEL_NONE:
            for node in self.IterateNodes():
                node.selected = False
        elif menu_id == glsGraphPopupMenu.ID_SEL_IVRT:
            for node in self.IterateNodes():
                node.selected = not node.selected
            pass
        return
    def OnPaint(self, event):
        # Handle paint event.
        start = datetime.datetime.now()
        self.OnDraw()
        self.time_draw = datetime.datetime.now() - start
        self.time_draw = self.time_draw.total_seconds()
        return
    def IterateNodes(self):
        # Convenient, clean, but slow iteration over graph nodes.
        with self.lock:
            for node in self.gthread.graph.nlist:
                yield node
        return
    def IterateEdges(self):
        # Convenient, clean, but slow iteration over graph edges.
        with self.lock:
            graph = self.gthread.graph
            for e in graph.np_edges:
                yield e, graph.nlist[e[0]], graph.nlist[e[1]]
        return
    def SelectionBoxValid(self):
        # Retrun True if mouse selection box is filled and valid, else false.
        return None not in self.selection_box[0] and None not in self.selection_box[1]
    def SelectionBoxStarted(self):
        # Retrun True if mouse selection box is started, else false.
        return None not in self.selection_box[0]
    def ProcessSelected(self, selected):
        # selected = [(dist, dist, [id+1]), ...]
        selected = [ (s[0], s[2][0]-1) for s in selected
                     if len(s[2]) == 1  and s[2][0] >= 1 ]
        if len(selected) == 0:
            return
        with self.lock:
            graph = self.gthread.graph
            kinds = graph.np_kinds[glsDirTree.KIND_SELECT]
            if self.SelectionBoxValid():
                selected = [ s[1] for s in selected ]
                selected = np.reshape(np.array(selected, dtype=np.intc), (len(selected),1))
                kinds = np.vstack( (kinds, selected) )
            else:
                selected.sort(key=lambda x: x[0])
                selected = selected[0][1]
                ndx = np.where(kinds == selected)[0]
                if len(ndx):
                    kinds = np.delete(kinds, ndx)
                else:
                    kinds = np.vstack( (kinds, selected) )
                kinds = np.reshape(np.unique(kinds), (len(kinds),1))
            graph.np_kinds[glsDirTree.KIND_SELECT] = kinds
        return
    def PushFrames(self):
        # Draw frames repeatedly and handle node selection modes.
        if self.closing:
            self.pushframes_done = True
            return
        start = datetime.datetime.now()
        if self.selection and self.SelectionBoxValid():
            w = abs(self.selection_box[1][0] - self.selection_box[0][0])
            h = abs(self.selection_box[1][1] - self.selection_box[0][1])
            if w < 1 or h < 1:
                self.selection_box = [ [None, None], [None, None] ]
                self.selection = False
        if self.selection:
            select_max = 100000
            select = np.zeros((select_max), dtype=np.uint32)
            self.glctx.SetCurrent(self)
            glSelectBuffer(select_max, select);
            glRenderMode(GL_SELECT)
            self.OnDraw()
            selected = glRenderMode(GL_RENDER);
            self.ProcessSelected(selected);
            self.selection = False
            self.selection_box = [ [None, None], [None, None] ]
        self.OnDraw()
        self.time_draw = (datetime.datetime.now() - start).total_seconds()
        next_draw = 1000.0/self.fps_max - self.time_draw
        next_draw = 5 if next_draw <= 5 else int(next_draw)
        wx.CallLater(next_draw, self.PushFrames)
        return
    def DrawEdges(self, zoom):
        # Draw graph edges.
        graph = self.gthread.graph
        glColor4fv(self.grn)
        glVertexPointer(3, GL_FLOAT, 0, graph.np_nodes)
        glEnableClientState(GL_VERTEX_ARRAY)
        glDrawElements(GL_LINES, len(graph.np_edges)*2, GL_UNSIGNED_INT, graph.np_edges)
        return
    def DrawNodes(self, zoom):
        # Draw graph nodes.
        graph = self.gthread.graph
        if self.selection:
            glInitNames();
            glPushName(0);
            for ni,pos in enumerate(graph.np_nodes):
                glLoadName(ni+1)
                glBegin(GL_POINTS)
                glVertex3fv(pos)
                glEnd()
            glLoadName(0)
        else:
            glVertexPointer(3, GL_FLOAT, 0, graph.np_nodes)
            glEnableClientState(GL_VERTEX_ARRAY)
            for kind in range(glsDirTree.KINDS):
                nodes = graph.np_kinds[kind]
                color, size = self.node_styles[kind]
                glColor4fv(color)
                glPointSize(size)
                glDrawElements(GL_POINTS, len(nodes), GL_UNSIGNED_INT, nodes)
        return
        pos_nodes = []
        pos_nodes.append(self.Project3DTo2D(pos))
        # Draw node labels.
        self.Set2D()
        for ni,node in enumerate(graph.nodes.values()):
            pos = pos_nodes[ni]
            if pos[2] > 1:
                continue
            if node.selected:
                bckg = True
                yoff = 20
                color = self.red
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
                        color = self.ylw
                        label = True
                    else:
                        color = self.prp
                        label = True if zoom >= 1.5 else False
                else:
                    if isinstance(node, glsDir):
                        color = self.ylw
                        label = True
                    else:
                        color = self.prp
                        label = True if zoom >= 60 else False
            if label:
                self.glfont.DrawText(node.name, [pos[0], pos[1]+yoff, pos[2]],
                                     color, True, bckg)
        return
    def DrawGraph(self):
        # Draw graph while holding the lock.
        with self.lock:
            # Get graph and its settings.
            graph = self.gthread.graph
            if self.gthread.dims == 2:
                self.Set2D()
                self.graph_3D = False
            elif self.gthread.dims == 3:
                self.Set3D()
                self.graph_3D = True
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
                glTranslatef(self.Size[0]/2.0, self.Size[1]/2.0, 0)
                zoom = self.zoom
            glScalef(zoom, zoom, zoom)
            # Save 2D screen coordinates for the nodes.
            self.Record3DTo2DMatrices()
            # Draw edges.
            self.DrawEdges(zoom)
            # Draw nodes.
            self.DrawNodes(zoom)
        return
    def DrawSelectionBox(self):
        # Draw box for selecting nodes.
        if not self.SelectionBoxValid():
            return
        self.Set2D()
        height = self.Size[1]
        v0 = (self.selection_box[0][0], height-self.selection_box[0][1])
        v1 = (self.selection_box[1][0], height-self.selection_box[0][1])
        v2 = (self.selection_box[1][0], height-self.selection_box[1][1])
        v3 = (self.selection_box[0][0], height-self.selection_box[1][1])
        glColor4fv([1, 0, 0, 0.15])
        glBegin(GL_POLYGON)
        glVertex2fv(v0)
        glVertex2fv(v1)
        glVertex2fv(v2)
        glVertex2fv(v3)
        glEnd()
        glColor4fv([1,1,1,1])
        glBegin(GL_LINE_LOOP)
        glVertex2fv(v0)
        glVertex2fv(v1)
        glVertex2fv(v2)
        glVertex2fv(v3)
        glEnd()
        return
    def DrawStats(self):
        # Draw text stats overlay.
        self.Set2D()
        glColor4fv([0,0,0,0.75])
        glBegin(GL_POLYGON)
        glVertex3fv([0,   self.Size[1]-2*self.glfont.char_h, 0])
        glVertex3fv([0,   self.Size[1],                      0])
        glVertex3fv([140, self.Size[1],                      0])
        glVertex3fv([140, self.Size[1]-2*self.glfont.char_h, 0])
        glEnd()
        self.time_fdp = self.gthread.get_time()
        if self.time_fdp == 0:
            fps_fdp = 0
        else:
            fps_fdp = 1.0 / self.time_fdp
        fps_fdp = "FPS(fdp): %.2f "%(fps_fdp)
        fps_pos = [0, self.Size[1]-self.glfont.char_h, 0]
        self.glfont.DrawText(fps_fdp, fps_pos, self.grn)
        fps_ogl = 1.0 / self.time_draw
        fps_ogl = "FPS(ogl): %.2f"%(fps_ogl)
        fps_pos = [0, self.Size[1]-2*self.glfont.char_h, 0]
        self.glfont.DrawText(fps_ogl, fps_pos, self.grn)
        return
    def OnDraw(self):
        # Draw everything.
        self.SetCurrent(self.glctx)
        self.SetMatrices()
        # Clear buffer.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Draw the graph.
        self.DrawGraph()
        # Draw selection box.
        self.DrawSelectionBox()
        # Draw stats.
        self.DrawStats()
        # Swap buffers to show the scene.
        self.SwapBuffers()
        return
    def Project3DTo2D(self, pos):
        # Map point from 3D to 2D.
        return gluProject(*pos, self.model_view, self.projection, self.viewport)
    def Record3DTo2DMatrices(self):
        # Save matrices for mapping from 3D to 2D coordinates.
        self.model_view = glGetDoublev(GL_MODELVIEW_MATRIX)
        self.projection = glGetDoublev(GL_PROJECTION_MATRIX)
        self.viewport   = glGetIntegerv(GL_VIEWPORT)
        return
    def SetPickMatrix(self):
        # Applies picking matrix for node selection.
        if not self.selection:
            return
        if self.SelectionBoxValid():
            x = (self.selection_box[0][0] + self.selection_box[1][0]) / 2.0
            y = (self.selection_box[0][1] + self.selection_box[1][1]) / 2.0
            w = abs(self.selection_box[1][0] - self.selection_box[0][0])
            h = abs(self.selection_box[1][1] - self.selection_box[0][1])
        else:
            x = self.mouse_pos[0]
            y = self.mouse_pos[1]
            w = 20
            h = 20
        self.viewport = glGetIntegerv(GL_VIEWPORT)
        gluPickMatrix(x, self.viewport[3]-y, w, h, self.viewport);
        return
    def Set2D(self):
        # Setup OpenGL matrices for 2D drawing.
        glViewport(0, 0, self.Size[0], self.Size[1])
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.SetPickMatrix()
        glOrtho(0.0, self.Size[0],
                0.0, self.Size[1],
                -0.01, 10.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        return
    def Set3D(self):
        # Setup OpenGL matrices for 3D drawing.
        glViewport(0, 0, self.Size[0], self.Size[1])
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.SetPickMatrix()
        gluPerspective(75, self.Size[0]/self.Size[1], 1, 1000);
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0.0,  0.0, 10.0,   # eye
                  0.0,  0.0,  0.0,   # center
                  0.0,  1.0,  0.0 ); # up vector
        return
    def SetMatrices(self):
        # Set OpenGL matrices for 2D or 3D drawing.
        if self.graph_3D:
            self.Set3D()
        else:
            self.Set2D()
        return
    def OnClose(self, event=None):
        # Handle close event.
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
    def OnDestroy(self, event):
        # Handle destroy event.
        self.settings.RemoveWatcher(self.OnChangeSettings)
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
