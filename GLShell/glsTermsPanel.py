import os
import wx
import fcntl
import termios
import struct
import select
import pty
import tty
import string
import threading
from time import sleep
from array import *

import TermEmulator

def PrintStringAsAscii(s):
    for ch in s:
        if ch in string.printable:
            print(ch, end="")
        else:
            print(ord(ch), end="")
    return

class glsTermPanelPopupMenu(wx.Menu):
    ID_NEW_TERM    = 1000
    ID_SEARCH_TEXT = 1001
    ID_SEARCH_FILE = 1002
    def __init__(self, parent):
        super(glsTermPanelPopupMenu, self).__init__()
        item = wx.MenuItem(self, self.ID_NEW_TERM, 'New Terminal')
        self.Append(item)
        item = wx.MenuItem(self, wx.ID_COPY, 'Copy')
        self.Append(item)
        item = wx.MenuItem(self, wx.ID_PASTE, 'Paste')
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SEARCH_TEXT, 'Search Text')
        self.Append(item)
        item = wx.MenuItem(self, self.ID_SEARCH_FILE, 'Search File')
        self.Append(item)
        return

class glsTerminalPanel(wx.Window):
    color_map_fg = ( ( 192, 192, 192),
                     ( 0,   0,     0),
                     ( 255, 0,     0),
                     ( 0,   255,   0),
                     ( 255, 255,   0),
                     ( 0,   0,   255),
                     ( 255, 0,   255),
                     ( 0,   255, 255),
                     ( 255, 255, 255) )
    color_map_bg = ( ( 0,   0,     0),
                     ( 0,   0,     0),
                     ( 255, 0,     0),
                     ( 0,   255,   0),
                     ( 255, 255,   0),
                     ( 0,   0,   255),
                     ( 255, 0,   255),
                     ( 0,   255, 255),
                     ( 255, 255, 255),
                     ( 255, 255, 255) )
    word_chars = "-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-z0123456789,./?%&#:_=+@~"
    shift_key_map = { ',':'<', '.':'>', '/':'?', ';':':', "'":'"', '[' :'{', ']':'}',
                      '1':'!', '2':'@', '3':'#', '4':'$', '5':'%', '6' :'^', '7':'&',
                      '8':'*', '9':'(', '0':')', '-':'_', '=':'+', '\\':'|', '`':'~',
                      '<':'<', '(':'(', ')':')' }
    special_key_map = {wx.WXK_UP:"\x1b[A",   wx.WXK_DOWN:"\x1b[B", wx.WXK_RIGHT:"\x1b[C",
                       wx.WXK_LEFT:"\x1b[D", wx.WXK_ESCAPE:"\x1b", wx.WXK_INSERT:"\x1b[2~" }
    def __init__(self, parent, settings, callback_close, callback_title, min_size):
        # Call super.
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTerminalPanel, self).__init__(parent,style=style)
        self.SetMinSize(min_size)
        self.settings = settings
        self.callback_close = callback_close
        self.callback_title = callback_title
        # Bind events.
        self.Bind(wx.EVT_MENU, self.MenuHandler)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDouble)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.dbl_click = False
        self.left_down = False
        self.sel_start = None
        self.sel_end = None
        self.selected = None
        wx.CallLater(10, self.MonitorTerminal)
        self.keys_down = {}
        # Set background and font.
        self.SetBackgroundColour(wx.BLACK)
        self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        w,h = dc.GetTextExtent("X")
        self.char_w = w
        self.char_h = h
        # Setup terminal emulator.
        self.rows = int((self.Size[1]-10) / self.char_h)
        self.cols = int((self.Size[0]-10) / self.char_w)
        self.cursor_pos = (0,0)
        self.terminal = TermEmulator.V102Terminal(self.rows,
                                                  self.cols)
        self.terminal.SetCallback(self.terminal.CALLBACK_SCROLL_UP_SCREEN,
                                  self.OnTermScrollUpScreen)
        self.terminal.SetCallback(self.terminal.CALLBACK_UPDATE_LINES,
                                  self.OnTermUpdateLines)
        self.terminal.SetCallback(self.terminal.CALLBACK_UPDATE_CURSOR_POS,
                                  self.OnTermUpdateCursorPos)
        self.terminal.SetCallback(self.terminal.CALLBACK_UPDATE_WINDOW_TITLE,
                                  self.OnTermUpdateWindowTitle)
        self.terminal.SetCallback(self.terminal.CALLBACK_UNHANDLED_ESC_SEQ,
                                  self.OnTermUnhandledEscSeq)
        # Start child process.
        self.path = self.settings.shell_path
        basename = os.path.basename(self.path)
        arglist = [ basename ]
        arguments = self.settings.shell_args
        if arguments != "":
            for arg in arguments.split(' '):
                arglist.append(arg)
        self.pid, self.io = pty.fork()
        os.environ["TERM"] = "vt100"
        if self.pid == 0:
            # Child process.
            os.execl(self.path, *arglist)
        fcntl.ioctl(self.io, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.rows, self.cols, 0, 0))
        tcattrib = termios.tcgetattr(self.io)
        tcattrib[3] = tcattrib[3] & ~termios.ICANON
        termios.tcsetattr(self.io, termios.TCSAFLUSH, tcattrib)
        self.notified_parent_closed = False
        self.child_output_notifier_thread_done = False
        self.child_output_notifier_thread = threading.Thread(
            target = self.ChildOuputNotifier)
        self.output_wait = True
        self.stop_output_notifier = False
        self.child_output_notifier_thread.start()
        self.child_running = True
        # Add scrollbar.
        self.scrollbar = wx.ScrollBar(self, pos=(self.Size[0]-10,0),
                                      size=(10,self.Size[1]), style=wx.SB_VERTICAL)
        self.scrollbar.Bind(wx.EVT_SCROLL, self.OnScroll)
        self.scrolled_text = []
        self.scrolled_rendition = []
        self.max_scroll_history = 10000
        self.UpdateScrollbar()
        # Setup buffer for double-buffered rendering.
        self.dc_buffer = wx.EmptyBitmap(*self.Size)
        return
    def ChildIsAlive(self):
        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid and os.WIFEXITED(status):
                return False
        except:
            return False
        return True
    def ChildOuputNotifier(self):
        inp_set = [ self.io ]
        while (not self.stop_output_notifier and self.ChildIsAlive()):
            if self.output_wait:
                inp_ready, out_ready, err_ready = select.select(inp_set, [], [], 0)
                if self.io in inp_ready:
                    self.output_wait = False
                    wx.CallAfter(self.ReadProcessOutput)
                else:
                    sleep(0.001)
            else:
                sleep(0.001)
        if not self.ChildIsAlive():
            self.child_running = False
            wx.CallAfter(self.ReadProcessOutput)
        self.child_output_notifier_thread_done = True
        return
    def ReadProcessOutput(self):
        output = bytes("",'utf8')
        try:
            while True:
                data = os.read(self.io, 512)
                datalen = len(data)
                output += data
                if datalen < 512:
                    break
        except:
            output = bytes("",'utf8')
        try:
            output = output.decode()
            self.terminal.ProcessInput(output)
        except:
            pass
        self.output_wait = True
        return
    def OnSetFocus(self, event):
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnKillFocus(self, event):
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def MenuHandler(self, event):
        id = event.GetId() 
        if id == wx.ID_COPY:
            self.Copy()
        elif id == wx.ID_PASTE:
            self.Paste()
        elif id == glsTermPanelPopupMenu.ID_NEW_TERM:
            self.Parent.Parent.OnNewTerm(event)
        return
    def WriteClipboard(self, text):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        return
    def ReadClipboard(self):
        text_data = wx.TextDataObject()
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(text_data)
            wx.TheClipboard.Close()
        if success:
            return text_data.GetText()
        return None
    def GetSelectedText(self):
        if self.sel_start is not None and self.sel_end is not None and self.sel_start != self.sel_end:
            text = ""
            screen = self.terminal.GetRawScreen()
            start = self.sel_start[0]*self.cols + self.sel_start[1]
            end   = self.sel_end[0]*self.cols + self.sel_end[1]
            if start > end:
                start, end = end, start
            for i in range(start, end):
                row = int(i/self.cols)
                col = i%self.cols
                text += screen[row][col]
                if col == self.cols-1:
                    text += '\n'
            return text
        return None
    def Copy(self):
        text = self.GetSelectedText()
        if text is not None:
            self.WriteClipboard(text)
            return text
        return None
    def Paste(self):
        text = self.ReadClipboard()
        if text is None:
            return
        os.write(self.io, bytes(text,'utf-8'))
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def PointToCursor(self, point):
        return ( max(min(int(point[1]/self.char_h),self.rows),0),
                 max(min(int(point[0]/self.char_w),self.cols),0) )
    def OnMiddleDown(self, event):
        self.Paste()
        return
    def OnLeftDown(self, event):
        self.SetFocus()
        self.left_down = True
        self.sel_start = self.PointToCursor(event.GetPosition())
        self.sel_end = self.sel_start
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnLeftUp(self, event):
        self.left_down = False
        if self.dbl_click == True:
            self.dbl_click = False
            return
        self.sel_end = self.PointToCursor(event.GetPosition())
        if self.sel_start == self.sel_end:
            self.sel_start = None
            self.sel_end = None
        else:
            self.selected = self.Copy()
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnLeftDouble(self, event):
        row, col = self.PointToCursor(event.GetPosition())
        start = row*self.cols + col
        screen = self.terminal.GetRawScreen()
        sel_start = row, col
        for i in reversed(range(0,start)):
            r = int(i/self.cols)
            c = i%self.cols
            if screen[r][c] not in self.word_chars:
                break
            else:
                sel_start = r, c
        self.sel_start = sel_start
        sel_end = row, col+1
        for i in range(start,self.rows*self.cols):
            r = int(i/self.cols)
            c = i%self.cols
            if screen[r][c] not in self.word_chars:
                break
            else:
                sel_end = r, c+1
        self.sel_end = sel_end
        self.dbl_click = True
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnMove(self, event):
        if self.left_down:
            self.sel_end = self.PointToCursor(event.GetPosition())
            self.Refresh()
            wx.YieldIfNeeded()
        return
    def OnRightDown(self, event):
        self.SetFocus()
        self.PopupMenu(glsTermPanelPopupMenu(self), event.GetPosition())
        return
    def GetFgColor(self, color):
        if color < len(self.color_map_fg):
            return self.color_map_fg[color]
        return self.color_map_fg[0]
    def GetBgColor(self, color):
        if color < len(self.color_map_bg):
            return self.color_map_bg[color]
        return self.color_map_bg[0]
    def SetTextStyle(self, dc, cur_style, style, fgcolor, bgcolor):
        if cur_style != style:
            self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
            if style & self.terminal.RENDITION_STYLE_UNDERLINE:
                self.fontinfo = self.fontinfo.Underlined()
            if style & self.terminal.RENDITION_STYLE_BOLD:
                self.fontinfo = self.fontinfo.Bold()
            if style & self.terminal.RENDITION_STYLE_INVERSE:
                fgcolor, bgcolor = bgcolor, fgcolor
            self.font = wx.Font(self.fontinfo)
            dc.SetFont(self.font)
            dc.SetTextForeground(fgcolor)
            self.SetTextBGColor(dc, None, bgcolor)
        return style
    def SetTextFGColor(self, dc, cur_fgcolor, fgcolor):
        if cur_fgcolor != fgcolor:
            dc.SetTextForeground(fgcolor)
        return fgcolor
    def SetTextBGColor(self, dc, cur_bgcolor, bgcolor):
        if cur_bgcolor != bgcolor:
            self.pen = wx.Pen(bgcolor)
            dc.SetPen(self.pen)
            self.brush = wx.Brush(bgcolor)
            dc.SetBrush(self.brush)
        return bgcolor
    def DrawText(self, dc, text, row, col):
        dc.DrawRectangle(col*self.char_w, row*self.char_h,
                         len(text)*self.char_w, self.char_h)
        dc.DrawText(text, col*self.char_w, row*self.char_h)
        return
    def OnPaint(self, event):
        dc = wx.MemoryDC()
        dc.SelectObject(self.dc_buffer)
        dc.Clear()
        brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.DrawRectangle(0, 0, self.Size[0], self.Size[1])
        scroll = self.scrollbar.GetRange() - self.rows - self.scrollbar.GetThumbPosition()
        # Draw the screen text.
        screen = self.terminal.GetRawScreen()
        rendition = self.terminal.GetRawScreenRendition()
        if scroll > 0 and scroll < self.rows:
            screen = self.scrolled_text[-scroll:] + screen[:-scroll]
            rendition = self.scrolled_rendition[-scroll:] + rendition[:-scroll]
        elif scroll >= self.rows:
            start = len(self.scrolled_text) - scroll
            end = start + self.rows
            screen = self.scrolled_text[start:end]
            rendition = self.scrolled_rendition[start:end]
        cur_style   = 0
        cur_fgcolor = self.GetFgColor(0)
        cur_bgcolor = self.GetBgColor(0)
        self.SetTextStyle(dc, None, cur_style, cur_fgcolor, cur_bgcolor)
        for row in range(len(screen)):
            col_start = 0
            text = ""
            for col in range(min(len(screen[row]),self.cols)):
                rend = rendition[row][col]
                style = rend & 0x000000ff
                fgcolor = (rend & 0x00000f00) >> 8
                bgcolor = (rend & 0x0000f000) >> 12
                fgcolor = self.GetFgColor(fgcolor)
                bgcolor = self.GetBgColor(bgcolor)
                if cur_style != style or cur_fgcolor != fgcolor or cur_bgcolor != bgcolor:
                    self.DrawText(dc, text, row, col_start)
                    col_start = col
                    text = ""
                    cur_style   = self.SetTextStyle(dc, cur_style, style, fgcolor, bgcolor)
                    cur_fgcolor = self.SetTextFGColor(dc, cur_fgcolor, fgcolor)
                    cur_bgcolor = self.SetTextBGColor(dc, cur_bgcolor, bgcolor)
                text += screen[row][col]
            self.DrawText(dc, text, row, col_start)
        # Draw the cursor.
        if scroll == 0:
            self.pen = wx.Pen((255,0,0,128))
            dc.SetPen(self.pen)
            if self.HasFocus():
                self.brush = wx.Brush((255,0,0,64))
            else:
                self.brush = wx.Brush((255,0,0), wx.TRANSPARENT)
        dc.SetBrush(self.brush)
        dc.DrawRectangle(self.cursor_pos[1]*self.char_w, self.cursor_pos[0]*self.char_h,
                         self.char_w, self.char_h)
        # Draw the current selection.
        if self.sel_start is not None and self.sel_end is not None:
            self.pen = wx.Pen((0,0,0), style=wx.TRANSPARENT)
            dc.SetPen(self.pen)
            self.brush = wx.Brush((255,255,0,64))
            dc.SetBrush(self.brush)
            start = self.sel_start
            end   = self.sel_end
            if start[0]*self.cols+start[1] > end[0]*self.cols+end[1]:
                start, end = end, start
            cend = end[1] if start[0] == end[0] else self.cols
            dc.DrawRectangle(start[1]*self.char_w, start[0]*self.char_h,
                             (cend-start[1])*self.char_w, self.char_h)
            for rmid in range(1,max(end[0]-start[0],0)):
                dc.DrawRectangle(0, (start[0]+rmid)*self.char_h,
                                 self.cols*self.char_w, self.char_h)
            if end[0]-start[0] > 0:
                dc.DrawRectangle(0, (end[0])*self.char_h,
                                 end[1]*self.char_w, self.char_h)
        # Switch to the real window dc and draw the buffer.
        del dc
        dc = wx.BufferedPaintDC(self, self.dc_buffer)
        return
    def UpdateScrollbar(self, new_lines=0):
        self.scrollbar.SetSize(self.Size[0]-10, 0, 10, self.Size[1])
        self.scrollbar.SetScrollbar(self.scrollbar.GetThumbPosition()+new_lines, self.rows,
                                    self.rows+len(self.scrolled_text),
                                    10, refresh=True)
        return
    def OnScroll(self, event):
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnSize(self, event):
        self.rows = int((self.Size[1]-10) / self.char_h)
        self.cols = int((self.Size[0]-10) / self.char_w)
        self.UpdateScrollbar()
        # Update terminal size.
        rows, cols = self.terminal.GetSize()
        if rows != self.rows or cols != self.cols:
            self.terminal.Resize(self.rows, self.cols)
        fcntl.ioctl(self.io, termios.TIOCSWINSZ,
        struct.pack("hhhh", self.rows, self.cols, 0, 0))
        # Deselect.
        self.sel_start = None
        self.sel_end = None
        # Resize buffer for painting.
        self.dc_buffer = wx.EmptyBitmap(*self.Size)
        return
    def OnChar(self, event):
        return
    def KeyCodeToSequence(self, key):
        seq = None
        if key < 256:
            ckey = chr(key)
            if wx.WXK_ALT in self.keys_down:
                seq = "\x1b"
                if wx.WXK_SHIFT in self.keys_down:
                    return seq + ckey
                return seq + ckey.lower()
            if wx.WXK_CONTROL in self.keys_down:
                if key == wx.WXK_SPACE:
                    return '\x00'
                if wx.WXK_SHIFT in self.keys_down:
                    if ckey >= 'A' and ckey <= 'Z':
                        print('sending',chr(key))
                        return chr(ord(chr(key))-0x40)
                    if ckey == '-':
                        return '\x1f'
                    if ckey == ',' or ckey == '.':
                        return 
                else:
                    if ckey >= 'A' and ckey <= 'Z':
                        return chr(ord(chr(key).lower())-0x60)
            else:
                if wx.WXK_SHIFT in self.keys_down:
                    if ckey in self.shift_key_map:
                        return self.shift_key_map[ckey]
                    else:
                        return ckey
                else:
                    return ckey.lower()
        else:
            if key in self.special_key_map:
                return self.special_key_map[key]
        return seq
    def OnKeyDown(self, event):
        key = event.GetKeyCode()
        self.keys_down[key] = True
        seq = self.KeyCodeToSequence(key)
        if seq is not None:
            os.write(self.io, bytes(seq,'utf-8'))
        event.Skip()
        return
    def OnKeyUp(self, event):
        key = event.GetKeyCode()
        if key in self.keys_down:
            del self.keys_down[event.GetKeyCode()]
        event.Skip()
        return
    def OnTermScrollUpScreen(self):
        text = "".join(self.terminal.GetRawScreen()[0])
        rendition = self.terminal.GetRawScreenRendition()[0]
        rend = array('L')
        for c in range(self.cols):
            rend.append(rendition[c])
        if len(self.scrolled_text) >= self.max_scroll_history:
            self.scrolled_text.pop(0)
            self.scrolled_rendition.pop(0)
        self.scrolled_text.append(text)
        self.scrolled_rendition.append(rend)
        self.UpdateScrollbar(new_lines=1)
        return
    def OnTermUpdateLines(self):
        self.Refresh()
        text = self.GetSelectedText()
        if text != self.selected and self.left_down == False:
            self.sel_start = None
            self.sel_end = None
            self.selected = None
        wx.YieldIfNeeded()
        return
    def OnTermUpdateCursorPos(self):
        self.cursor_pos = self.terminal.GetCursorPos()
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnTermUpdateWindowTitle(self, title):
        self.callback_title(self, title)
        return
    def OnTermUnhandledEscSeq(self, escSeq):
        print("Unhandled escape sequence: [{}".format(escSeq))
        return
    def MonitorTerminal(self):
        # Monitor the state of the child process and tell parent when closed.
        if self.child_output_notifier_thread_done == True:
            if self.child_output_notifier_thread is not None:
                self.child_output_notifier_thread.join()
                self.child_output_notifier_thread = None
            if self.notified_parent_closed == False:
                self.callback_close(self)
                self.notified_parent_closed = True
        else:
            wx.CallLater(10, self.MonitorTerminal)
        return
    def OnClose(self, event=None):
        self.stop_output_notifier = True
        return
    def OnDestroy(self, event):
        self.stop_output_notifier = True
        if self.child_output_notifier_thread is not None:
            self.child_output_notifier_thread.join()
        return

################################################################

class glsTermNotebook(wx.Window):
    def __init__(self, parent, settings, min_term_size):
        # Call super.
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTermNotebook, self).__init__(parent,style=style)
        self.settings = settings
        self.min_term_size = min_term_size
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.term_notebook = wx.Notebook(self)
        self.term_tabs = [ glsTerminalPanel(self.term_notebook, self.settings,
                                            self.OnTermClose, self.OnTermTitle,
                                            self.min_term_size) ]
        self.term_notebook.AddPage(self.term_tabs[0], "Terminal 1")
        self.term_close_pending = []
        wx.CallLater(10, self.MonitorTerminals)
        box_main.Add(self.term_notebook, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 0)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnNewTerm(self, event):
        # Create a new terminal and add the tab to the notebook.
        terminal = glsTerminalPanel(self.term_notebook, self.settings,
                                    self.OnTermClose, self.OnTermTitle,
                                    self.min_term_size)
        self.term_tabs.append(terminal)
        self.term_notebook.AddPage(terminal, "Terminal " + str(len(self.term_tabs)))
        self.term_notebook.ChangeSelection(len(self.term_tabs)-1)
        return
    def MonitorTerminals(self, event=None):
        # Check for closed terminals and clean up their tabs.
        for terminal in self.term_close_pending:
            for i,t in enumerate(self.term_tabs):
                if terminal == t:
                    self.term_notebook.DeletePage(i)
                    self.term_notebook.SendSizeEvent()
                    self.term_tabs.remove(self.term_tabs[i])
            self.term_close_pending.remove(terminal)
        wx.CallLater(10, self.MonitorTerminals)
        return
    def OnTermClose(self, terminal):
        # Add tab to closed terminal list.
        if terminal not in self.term_close_pending:
            self.term_close_pending.append(terminal)
        return
    def OnTermTitle(self, terminal, title):
        for i,t in enumerate(self.term_tabs):
                if terminal == t:
                    self.term_notebook.SetPageText(i, title)
        return

################################################################

class glsTermsPanel(wx.Window):
    def __init__(self, parent, settings, min_term_size):
        # Call super.
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTermsPanel, self).__init__(parent,style=style)
        self.settings = settings
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(min_term_size[1])
        self.notebooks = [ glsTermNotebook(self.splitter, self.settings, min_term_size),
                           glsTermNotebook(self.splitter, self.settings, min_term_size), ]
        self.splitter.SplitHorizontally(self.notebooks[0], self.notebooks[1])        
        box_main.Add(self.splitter, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 0)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
