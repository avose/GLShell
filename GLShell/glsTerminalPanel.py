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

import TermEmulator

def PrintStringAsAscii(s):
    for ch in s:
        if ch in string.printable:
            print(ch, end="")
        else:
            print(ord(ch), end="")
    return

class glsTermPanelPopupMenu(wx.Menu):
    def __init__(self, parent):
        super(glsTermPanelPopupMenu, self).__init__()
        self.parent = parent
        item = wx.MenuItem(self, wx.ID_COPY,  'Copy')
        self.Append(item)
        item = wx.MenuItem(self, wx.ID_PASTE, 'Paste')
        self.Append(item)
        item = wx.MenuItem(self, wx.ID_ANY,   'Search Text')
        self.Append(item)
        item = wx.MenuItem(self, wx.ID_ANY,   'Search File')
        self.Append(item)
        return

class glsTerminalPanel(wx.Window):
    color_map_fg = ( ( 0,   255,   0),
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
    def __init__(self, parent, settings, close_handler):
        # Call super.
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTerminalPanel, self).__init__(parent,style=style)
        self.settings = settings
        self.close_handler = close_handler
        # Bind events.
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        wx.CallLater(10, self.MonitorTerminal)       
        # Set background and font.
        self.SetBackgroundColour(wx.BLACK)
        self.fontinfo = wx.FontInfo(10).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        w,h = dc.GetTextExtent("X")
        self.char_w = w
        self.char_h = h
        # Setup terminal emulator.
        self.rows = self.settings.term_rows
        self.cols = self.settings.term_cols
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
        self.text  = ""
        self.style = []
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
    def OnRightDown(self, event):
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
            self.fontinfo = wx.FontInfo(10).FaceName("Monospace")
            if style & self.terminal.RENDITION_STYLE_UNDERLINE:
                self.fontinfo = self.fontinfo.Underlined()
            if style & self.terminal.RENDITION_STYLE_BOLD:
                self.fontinfo = self.fontinfo.Bold()
            if style & self.terminal.RENDITION_STYLE_INVERSE:
                tcolor = bgcolor
                bgcolor = fgcolor
                fgcolor = tcolor
            self.font = wx.Font(self.fontinfo)
            dc.SetFont(self.font)
            dc.SetTextForeground(self.GetFgColor(fgcolor))
            self.SetTextBGColor(dc, None, bgcolor)
        return style
    def SetTextFGColor(self, dc, cur_fgcolor, fgcolor):
        if cur_fgcolor != fgcolor:
            dc.SetTextForeground(self.GetFgColor(fgcolor))
        return fgcolor
    def SetTextBGColor(self, dc, cur_bgcolor, bgcolor):
        if cur_bgcolor != bgcolor:
            self.brush = wx.Brush(self.GetBgColor(bgcolor))
            dc.SetBrush(self.brush)
        return bgcolor
    def DrawText(self, dc, text, row, col):
        dc.DrawRectangle(col*self.char_w, row*self.char_h,
                         len(text)*self.char_w, self.char_h)
        dc.DrawText(text, col*self.char_w, row*self.char_h)
        return
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        screen = self.terminal.GetRawScreen()
        cur_style   = 0
        cur_fgcolor = 0
        cur_bgcolor = 0
        self.SetTextStyle(dc, None, cur_style, cur_fgcolor, cur_bgcolor)
        for row in range(self.rows):
            col_start = 0
            text = ""
            for col in range(self.cols):
                style, fgcolor, bgcolor = self.terminal.GetRendition(row, col)
                if cur_style != style or cur_fgcolor != fgcolor or cur_bgcolor != bgcolor:
                    self.DrawText(dc, text, row, col_start)
                    col_start = col
                    text = ""
                    cur_style   = self.SetTextStyle(dc, cur_style, style, fgcolor, bgcolor)
                    cur_fgcolor = self.SetTextFGColor(dc, cur_fgcolor, fgcolor)
                    cur_bgcolor = self.SetTextBGColor(dc, cur_bgcolor, bgcolor)
                text += screen[row][col]
            self.DrawText(dc, text, row, col_start)
        return
    def OnSize(self, event):
        self.rows = int(self.Size[1] / self.char_h)
        self.cols = int(self.Size[0] / self.char_w)
        rows, cols = self.terminal.GetSize()
        if rows != self.rows or cols != self.cols:
            self.terminal.Resize(self.rows, self.cols)
        fcntl.ioctl(self.io, termios.TIOCSWINSZ,
        struct.pack("hhhh", self.rows, self.cols, 0, 0))
        return
    def OnChar(self, event):
        ascii = event.GetKeyCode()
        keystrokes = None
        if ascii < 256:
             keystrokes = chr(ascii)
        elif ascii == wx.WXK_UP:
            keystrokes = "\033[A"
        elif ascii == wx.WXK_DOWN:
            keystrokes = "\033[B"
        elif ascii == wx.WXK_RIGHT:
            keystrokes = "\033[C"
        elif ascii == wx.WXK_LEFT:
            keystrokes = "\033[D"
        if keystrokes != None:
            os.write(self.io, bytes(keystrokes,'utf-8'))
        return
    def OnKeyDown(self, event):
        event.Skip()
        return
    def OnKeyUp(self, event):
        event.Skip()
        return
    def OnTermScrollUpScreen(self):
        return
    def OnTermUpdateLines(self):
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnTermUpdateCursorPos(self):
        row, col = self.terminal.GetCursorPos()
        return
    def OnTermUpdateWindowTitle(self, title):
        return
    def OnTermUnhandledEscSeq(self, escSeq):
        #print("Unhandled escape sequence: [{}".format(escSeq))
        return
    def MonitorTerminal(self):
        # Monitor the state of the child process and tell parent when closed.
        if self.child_output_notifier_thread_done == True:
            if self.child_output_notifier_thread is not None:
                self.child_output_notifier_thread.join()
                self.child_output_notifier_thread = None
            if self.notified_parent_closed == False:
                self.close_handler(self)
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
