from wx.glcanvas import GLCanvas, WX_GL_DEPTH_SIZE
from OpenGL.GLU import *
from OpenGL.GL import *
import datetime
import numpy as np
import math
import sys
import wx

from glsGLBuffer import glsGLBuffer
from glsSettings import glsSettings
from glsDirTree import glsFile
from glsDirTree import glsDir
from glsDirTree import glsDirTree
from glsGLFont import glsGLFont
from glsIcons import glsIcons
from glsFDP import fdpNode
from glsFDP import fdpGraph

################################################################

class glsGraphPopupMenu(wx.Menu):
    ID_EXIT       = 1000
    ID_SEL_ALL    = 1001
    ID_SEL_NONE   = 1002
    ID_SEL_IVRT   = 1003
    ID_SHOW_FILES = 1004
    ID_SHOW_DIRS  = 1005
    def __init__(self, parent):
        super(glsGraphPopupMenu, self).__init__()
        item = wx.MenuItem(self, self.ID_SEL_ALL, 'Select All')
        item.SetBitmap(glsIcons.Get('chart_line_add'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SEL_IVRT, 'Select Inverse')
        item.SetBitmap(glsIcons.Get('chart_line'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SEL_NONE, 'Select None')
        item.SetBitmap(glsIcons.Get('chart_line_delete'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SHOW_FILES, 'Files && Directories', kind=wx.ITEM_RADIO)
        self.ri_files = item
        self.Append(self.ri_files)
        self.ri_files.Check(parent.show_files)
        item = wx.MenuItem(self, self.ID_SHOW_DIRS, 'Directories Only', kind=wx.ITEM_RADIO)
        self.ri_dirs = item
        self.Append(self.ri_dirs)
        self.ri_dirs.Check(not parent.show_files)
        item = wx.MenuItem(self, self.ID_EXIT, 'Close Graph')
        item.SetBitmap(glsIcons.Get('chart_organisation_delete'))
        self.Append(item)
        return

################################################################

class glsGraphCanvas(GLCanvas):
    # Color constatns.
    red = [1.0, 0.0, 0.0, 1.0]
    grn = [0.0, 1.0, 0.0, 1.0]
    blu = [0.0, 0.0, 1.0, 1.0]
    ylw = [1.0, 1.0, 0.0, 1.0]
    orn = [1.0, 0.6, 0.0, 1.0]
    prp = [1.0, 0.3, 1.0, 1.0]
    wht = [1.0, 1.0, 1.0, 1.0]
    def __init__(self, parent, dirtree, size, callback_close):
        # Initialize glsGraphCanvas.
        attrs = [ WX_GL_DEPTH_SIZE, 24, 0 ];
        GLCanvas.__init__(self, parent, -1, size=size, attribList=attrs)
        self.dirtree = dirtree
        self.gthread = self.dirtree.thread
        self.lock = self.gthread.lock
        self.callback_close = callback_close
        self.graph_3D = glsSettings.Get('graph_3D')
        glsSettings.AddWatcher(self.OnSettingsChange)
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
        self.done = False
        self.closing = False
        self.refresh = True
        self.show_files = True
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
        self.InitGL()
        font_name = glsSettings.Get('graph_font')
        font_size = glsSettings.Get('graph_font_size')
        self.glfont = glsGLFont(wx.FontInfo(font_size).FaceName(font_name))
        # node_style = (color, size, label, yoff, lcolor, bkgrnd)
        self.node_styles = { glsDirTree.KIND_DIR: (self.orn, 10.0, True, 10.0, self.ylw, False),
                             glsDirTree.KIND_FILE: (self.blu, 8.0, False, 10.0, self.prp, False),
                             glsDirTree.KIND_SELECT: (self.red, 15.0, True, 20.0, self.red, True),
                             glsDirTree.KIND_RESULT: (self.wht, 15.0, True, 20.0, self.wht, True),
                             glsDirTree.KIND_NONE: (self.red, 20.0, True, 20.0, self.red, True) }
        self.kind_order = [ glsDirTree.KIND_SELECT, glsDirTree.KIND_RESULT, glsDirTree.KIND_DIR,
                            glsDirTree.KIND_FILE, glsDirTree.KIND_NONE ]
        wx.CallAfter(self.PushFrames)
        return
    def InitGL(self):
        # Initialize OpenGL settings.
        self.glctx = wx.glcanvas.GLContext(self)
        self.SetCurrent(self.glctx)
        glDisable(GL_LIGHTING)
        glDepthFunc(GL_LEQUAL)
        glDepthMask(GL_TRUE)
        glClearDepth(1.0)
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glEnable(GL_LINE_SMOOTH);
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
        glEnable(GL_POINT_SMOOTH);
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST);
        self.SetMatrices()
        return
    def OnSettingsChange(self):
        # Handle settings change.
        font_name = glsSettings.Get('graph_font')
        font_size = glsSettings.Get('graph_font_size')
        self.glfont = glsGLFont(wx.FontInfo(font_size).FaceName(font_name))
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
    def DrawEdges(self, zoom):
        # Draw graph edges.
        graph = self.gthread.graph
        glColor4fv(self.grn)
        glVertexPointer(3, GL_FLOAT, 0, graph.np_nodes)
        glEnableClientState(GL_VERTEX_ARRAY)
        kinds = self.kind_order.copy()
        if not self.show_files:
            kinds = [ glsDirTree.KIND_DIR ]
        for kind in kinds:
            edges = graph.np_ekinds[kind]
            glDrawElements(GL_LINES, len(edges)*2, GL_UNSIGNED_INT, edges)
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
            return
        glVertexPointer(3, GL_FLOAT, 0, graph.np_nodes)
        glEnableClientState(GL_VERTEX_ARRAY)
        kinds = self.kind_order.copy()
        if not self.show_files:
            kinds.remove(glsDirTree.KIND_FILE)
        for kind in kinds:
            nodes = graph.np_nkinds[kind]
            color, size, label, yoff, lcolor, bkgrnd = self.node_styles[kind]
            glColor4fv(color)
            glPointSize(size)
            glDrawElements(GL_POINTS, len(nodes), GL_UNSIGNED_INT, nodes)
        # Draw node labels.
        self.Set2D()
        if self.graph_3D:
            always_label = True if zoom >= 1.5 else False
        else:
            always_label = True if zoom >= 60 else False
        drawn = {}
        for kind in kinds:
            nodes = graph.np_nkinds[kind]
            color, size, label, yoff, lcolor, bkgrnd = self.node_styles[kind]
            label = True if always_label else label
            for ndx in nodes:
                ndx = ndx[0]
                if ndx in drawn:
                    continue
                drawn[ndx] = True
                pos = self.Project3DTo2D(graph.np_nodes[ndx])
                if pos[2] > 1:
                    continue
                node = graph.nlist[ndx]
                if label:
                    self.glfont.DrawText(node.name, [pos[0], pos[1]+yoff, pos[2]],
                                         lcolor, True, bkgrnd)
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
            self.DrawEdges(zoom)
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
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.DrawGraph()
        self.DrawSelectionBox()
        self.DrawStats()
        self.SwapBuffers()
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
        if self.SelectionBoxValid():
            selected = [ s[1] for s in selected ]
            self.dirtree.SelectAdd(selected)
        else:
            selected.sort(key=lambda x: x[0])
            selected = [ selected[0][1] ]
            self.dirtree.SelectToggle(selected)
        return
    def OnPaint(self, event):
        # Draw the scene and handle node selection modes.
        if self.closing:
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
        self.refresh = False
        return
    def PushFrames(self):
        # Draw frames repeatedly.
        wx.YieldIfNeeded()
        if self.closing:
            self.done = True
            return
        if not self.refresh:
            self.refresh = True
            self.Refresh()
        wx.CallLater(int(1000.0/self.fps_max), self.PushFrames)
        return
    def OnChar(self, event):
        # Handle keyboard key character event.
        key_map = { wx.WXK_UP:'w', wx.WXK_LEFT:'a', wx.WXK_DOWN:'s', wx.WXK_RIGHT:'d' }
        key_delta = {'w':(1,5), 'a':(0,-5), 's':(1,-5), 'd':(0,5) }
        key = event.GetKeyCode()
        if key < 256:
            key = chr(key)
        elif key in key_map:
            key = key_map[key]
        if wx.WXK_TAB in self.keys_down:
            self.rotate += key_delta.get(key, (0,0))[1]
        else:
            delta = key_delta.get(key, (0,0))
            self.translate[delta[0]] += delta[1]
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
    def ShowFiles(self, enable):
        self.show_files = enable
        return
    def OnMenuItem(self, event):
        # Handle menu item event.
        menu_id = event.GetId()
        if menu_id == glsGraphPopupMenu.ID_EXIT:
            self.OnClose()
        elif menu_id == glsGraphPopupMenu.ID_SEL_ALL:
            self.dirtree.SelectAll()
        elif menu_id == glsGraphPopupMenu.ID_SEL_NONE:
            self.dirtree.SelectNone()
        elif menu_id == glsGraphPopupMenu.ID_SEL_IVRT:
            self.dirtree.SelectInverse()
        elif menu_id == glsGraphPopupMenu.ID_SHOW_FILES:
            self.ShowFiles(True)
        elif menu_id == glsGraphPopupMenu.ID_SHOW_DIRS:
            self.ShowFiles(False)
        return
    def OnSize(self, event):
        # Handle resize event.
        self.SetMatrices()
        return
    def OnClose(self, event=None):
        # Handle close event.
        if not self.closing:
            self.closing = True
            glsSettings.RemoveWatcher(self.OnSettingsChange)
            self.dirtree.thread.stop()
            self.dirtree.thread.join()
        if not self.done:
            wx.CallLater(10, self.OnClose)
            return
        self.callback_close()
        return
    def OnDestroy(self, event):
        # Handle destroy event.
        if not self.closing:
            self.closing = True
            glsSettings.RemoveWatcher(self.OnSettingsChange)
            self.dirtree.thread.stop()
            self.dirtree.thread.join()
        return

################################################################

class glsGraphPanel(wx.Window):
    def __init__(self, parent, dirtree, callback_close):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsGraphPanel, self).__init__(parent, style=style)
        self.dirtree = dirtree
        self.callback_close = callback_close
        self.min_size = (320,320)
        self.SetMinSize(self.min_size)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.SetBackgroundColour( (0,0,0) )
        self.graph_canvas = None
        self.Show(True)
        return
    def StartGraph(self):
        if self.graph_canvas is not None:
            return
        size = (max(self.min_size[0],self.Size[0]),
                max(self.min_size[1],self.Size[1]))
        self.graph_canvas = glsGraphCanvas(self, self.dirtree, size=size,
                                           callback_close=self.CloseGraph)
        return
    def OnSize(self, event=None):
        if self.graph_canvas is None:
            return
        self.graph_canvas.SetSize(0, 0, self.Size[0], self.Size[1])
        return
    def Resume(self):
        self.dirtree.Resume()
        return
    def Pause(self):
        self.dirtree.Pause()
        return
    def Rescan(self):
        self.dirtree.ScanDir()
        return
    def ShowFiles(self, enable):
        if self.graph_canvas is None:
            return
        self.graph_canvas.ShowFiles(enable)
        return
    def SelectAll(self):
        self.dirtree.SelectAll()
        return
    def SelectNone(self):
        self.dirtree.SelectNone()
        return
    def SelectInverse(self):
        self.dirtree.SelectInverse()
        return
    def CloseGraph(self):
        self.callback_close(self)
        return
    def OnClose(self, event=None):
        if self.graph_canvas is None:
            return
        self.graph_canvas.OnClose()
        return

################################################################
