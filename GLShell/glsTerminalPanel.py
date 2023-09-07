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

class glsTerminalPanel(wx.Window):
    def __init__(self, parent, settings):
        # Call super.
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTerminalPanel, self).__init__(parent,style=style)
        self.settings = settings
        # Bind events.
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
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
        print("Child PID: %d"%(self.pid))
        fcntl.ioctl(self.io, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.rows, self.cols, 0, 0))
        tcattrib = termios.tcgetattr(self.io)
        tcattrib[3] = tcattrib[3] & ~termios.ICANON
        termios.tcsetattr(self.io, termios.TCSAFLUSH, tcattrib)
        self.child_output_notifier_thread = threading.Thread(
            target = self.ChildOuputNotifier)
        self.output_wait = True
        self.stop_output_notifier = False
        self.child_output_notifier_thread.start()
        self.child_running = True
        self.text = ""
        self.lines_scrolled_up = 0
        self.scrolled_up_lineslen = 0
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
            self.Close()
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
        self.terminal.ProcessInput(output.decode())
        self.output_wait = True
        return
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        dc.SetTextForeground([0,255,0])
        dc.SetTextBackground(wx.NullColour)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.SetFont(self.font)
        screen = self.terminal.GetRawScreen()
        self.text = ""
        for row in screen:
            line = "".join(row)
            self.text += line + "\n"
        dc.DrawText(self.text, 0, 0)
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
            #print("Sending:", end="")
            #PrintStringAsAscii(keystrokes)
            #print("")
            os.write(self.io, bytes(keystrokes,'utf-8'))
        return
    def OnKeyDown(self, event):
        event.Skip()
        return
    def OnKeyUp(self, event):
        event.Skip()
        return
    def OnTermScrollUpScreen(self):
        blankline = "\n"
        for i in range(self.terminal.GetCols()):
            blankline += ' '
        linelen = self.cols
        self.text += blankline
        self.lines_scrolled_up += 1
        self.scrolled_up_lineslen += linelen + 1
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
        print("Unhandled escape sequence: [{}".format(escSeq))
        return
    def OnClose(self, event):
        self.stop_output_notifier = True
        return
    def OnDestroy(self, event):
        self.stop_output_notifier = True
        return
