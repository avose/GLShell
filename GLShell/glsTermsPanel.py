import os
import wx
import pty
import tty
import fcntl
import termios
import struct
import select
import string
import cProfile
import threading
import traceback
import numpy as np
from time import sleep
from array import *
from datetime import datetime

from glsPlaceHolder import glsPlaceHolder
from glsStatusBar import glsLog
from glsSettings import glsSettings
from glsKeyPress import glsKeyPress
from glsEvents import glsEvents
from glsIcons import glsIcons

import TermEmulator

################################################################

class glsTermPanelPopupMenu(wx.Menu):
    ID_NEW_TERM        = 1000
    ID_NEW_DIR         = 1001
    ID_COPY            = 1002
    ID_PASTE           = 1003
    ID_SEARCH_CONTENTS = 1004
    ID_SEARCH_FILES    = 1005
    ID_NAME            = 1006
    ID_FONT_UP         = 1007
    ID_FONT_DOWN       = 1008
    ID_EXIT            = 1009
    def __init__(self, parent, selection_available, paste_available):
        super(glsTermPanelPopupMenu, self).__init__()
        item = wx.MenuItem(self, self.ID_NEW_TERM, 'New Terminal')
        item.SetBitmap(glsIcons.Get('monitor_add'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_NEW_DIR, 'Open Directory')
        item.SetBitmap(glsIcons.Get('chart_organisation_add'))
        self.Append(item)
        if not selection_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_COPY, 'Copy')
        item.SetBitmap(glsIcons.Get('page_copy'))
        self.Append(item)
        if not selection_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_PASTE, 'Paste')
        item.SetBitmap(glsIcons.Get('page_paste'))
        self.Append(item)
        if not paste_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_SEARCH_CONTENTS, 'Search Contents')
        item.SetBitmap(glsIcons.Get('magnifier_zoom_in'))
        self.Append(item)
        if not selection_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_SEARCH_FILES, 'Search Files')
        item.SetBitmap(glsIcons.Get('magnifier'))
        self.Append(item)
        if not selection_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_NAME, 'Set Tab Name')
        item.SetBitmap(glsIcons.Get('pencil'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_FONT_UP, 'Zoom In')
        item.SetBitmap(glsIcons.Get('font_add'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_FONT_DOWN, 'Zoom OUT')
        item.SetBitmap(glsIcons.Get('font_delete'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_EXIT, 'Close Terminal')
        item.SetBitmap(glsIcons.Get('cross'))
        self.Append(item)
        return

################################################################

class glsTerminalPanel(wx.Window):
    # Color table for 256-color mode.
    # Inspired by:
    # https://github.com/terminalguide/terminalguide/
    # https://github.com/selectel/pyte
    # Indices 0-7 alias 8 standard FG colors.
    # Indices 8-15 alias 8 standard bright FG colors.
    COLORS_256 = [ (  0,   0,   0),
                   (205,   0,   0),
                   (  0, 205,   0),
                   (205, 205,   0),
                   (  0,   0, 238),
                   (205,   0, 205),
                   (  0, 205, 205),
                   (229, 229, 229),
                   (127, 127, 127),
                   (255,   0,   0),
                   (  0, 255,   0),
                   (255, 255,   0),
                   ( 92,  92, 255),
                   (255,   0, 255),
                   (  0, 255, 255),
                   (255, 255, 255), ]
    # Indices 16-231 form a 6x6x6 RGB color cube.
    COLOR_INTENSITY = (0, 95, 135, 175, 215, 255)
    for i in range(216):
        COLORS_256.append( (COLOR_INTENSITY[(i//36)%6],
                            COLOR_INTENSITY[(i//6)%6],
                            COLOR_INTENSITY[i%6]) )
    # Indices 232-255 form a grey ramp; no black or white.
    for i in range(24):
        rgb = i*10 + 8
        COLORS_256.append( (rgb, rgb, rgb) )

    def __init__(self, parent, min_size):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        # Give the term panel a default size to avoid errors on creation.
        # This also appears to influence some aspects of minimum size.
        super(glsTerminalPanel, self).__init__(parent, size=(200,100), style=style)
        self.profiler = cProfile.Profile()
        self.pcount = 0
        self.SetMinSize(min_size)
        self.SetCursor(wx.Cursor(wx.CURSOR_IBEAM))
        glsSettings.AddWatcher(self.OnChangeSettings)
        self.word_chars = glsSettings.Get('term_wchars')
        self.color_en = glsSettings.Get('term_color')
        self.color_fg = glsSettings.Get('term_fgcolor')
        self.color_bg = glsSettings.Get('term_bgcolor')
        self.SetBackgroundColour(self.color_bg)
        # Bind events.
        self.keys_down = {}
        self.key_press = glsKeyPress(self.keys_down)
        self.Bind(wx.EVT_MENU, self.OnMenuItem)
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
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(glsEvents.EVT_CHILD_EXIT, self.OnChildOutputThreadExit)
        self.dbl_click = False
        self.left_down = False
        self.sel_start = None
        self.sel_end = None
        self.selected = None
        self.select_delay = 0.15
        # Set font.
        self.font_name = glsSettings.Get('term_font')
        self.font_base = glsSettings.Get('term_font_size')
        self.char_w = None
        self.char_h = None
        self.font_zoom = 0
        self.font_min = 6
        self.font_max = 32
        self.font_step = 2
        self.SetFont()
        # Add scrollbar.
        self.scroll_outp = glsSettings.Get('term_scroll_output')
        self.scroll_keyp = glsSettings.Get('term_scroll_keypress')
        self.scroll_delta = 4
        self.scrollbar_w = 12
        self.scrollbar = wx.ScrollBar(self, pos=(self.Size[0]-self.scrollbar_w, 0),
                                      size=(self.scrollbar_w, self.Size[1]),
                                      style=wx.SB_VERTICAL)
        self.scrollbar.Bind(wx.EVT_SCROLL, self.OnScroll)
        self.scrolled_text = []
        self.scrolled_rendition = []
        self.max_scroll_history = 10000
        # Setup terminal emulator.
        self.rows = int((self.Size[1]) / self.char_h)
        self.cols = int((self.Size[0]-self.scrollbar_w) / self.char_w)
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
        self.terminal.SetCallback(self.terminal.CALLBACK_UPDATE_MODE,
                                  self.OnTermUpdateMode)
        self.terminal.SetCallback(self.terminal.CALLBACK_UPDATE_CURSOR,
                                  self.OnTermUpdateCursor)
        self.terminal.SetCallback(self.terminal.CALLBACK_SEND_DATA,
                                  self.OnTermSendData)
        self.cursor_style = self.terminal.CURSOR_STYLE_DEFAULT
        self.modes = dict(self.terminal.modes)
        # Start child process.
        self.path = glsSettings.Get('shell_path')
        basename = os.path.basename(self.path)
        arglist = [ basename ]
        arguments = glsSettings.Get('shell_args')
        if arguments != "":
            for arg in arguments.split(' '):
                arglist.append(arg)
        self.pid, self.io = pty.fork()
        os.environ["TERM"] = glsSettings.Get('term_type')
        if self.pid == 0:
            # Child process.
            os.execl(self.path, *arglist)
        glsLog.add("Terminal Child PID: "+str(self.pid))
        fcntl.ioctl(self.io, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.rows, self.cols, 0, 0))
        tcattrib = termios.tcgetattr(self.io)
        tcattrib[3] = tcattrib[3] & ~termios.ICANON
        termios.tcsetattr(self.io, termios.TCSAFLUSH, tcattrib)
        self.notified_parent_closed = False
        self.child_output_notifier_thread = threading.Thread(
            target = self.ChildOuputNotifier)
        self.output_wait = True
        self.stop_output_notifier = False
        self.child_output_notifier_thread.start()
        self.child_running = True
        # Setup buffer for double-buffered rendering.
        self.dc_buffer = wx.Bitmap(*self.Size)
        # Update scrollbar.
        self.UpdateScrollbar()
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
        while not self.stop_output_notifier and self.ChildIsAlive():
            if self.output_wait:
                inp_ready, out_ready, err_ready = select.select(inp_set, [], [], 0.01)
                if self.io in inp_ready:
                    self.output_wait = False
                    if self:
                        wx.CallAfter(self.ReadProcessOutput)
            else:
                sleep(0.001)
        if not self.ChildIsAlive():
            self.child_running = False
            if self:
                wx.CallAfter(self.ReadProcessOutput)
        if self:
            wx.PostEvent(self, glsEvents.ChildExit(wx.ID_ANY))
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
        if output == bytes("",'utf8'):
            self.output_wait = True
            return
        if self.scroll_outp:
            self.ScrollToEnd()
        try:
            output = output.decode()
            #self.profiler.enable()
            self.terminal.ProcessInput(output)
            #self.profiler.disable()
            #self.pcount += 1
        except:
            glsLog.add("Terminal: Exception in ProcessInput()!\n%s"%
                       (traceback.format_exc()))
        self.output_wait = True
        #print(self.pcount)
        #if self.pcount % 50 == 0:
        #    self.profiler.print_stats()
        return
    def ZoomIn(self):
        self.font_zoom += self.font_step
        if self.font_base + self.font_zoom > self.font_max:
            self.font_zoom = self.font_max - self.font_base
        if self.SetFont():
            self.OnSize()
        self.Refresh()
        return
    def ZoomOut(self):
        self.font_zoom -= self.font_step
        if self.font_base + self.font_zoom < self.font_min:
            self.font_zoom = -(self.font_base - self.font_min)
        if self.SetFont():
            self.OnSize()
        self.Refresh()
        return
    def SetFont(self):
        self.font_size = self.font_base + self.font_zoom
        self.font_size = min(max(self.font_size, self.font_min), self.font_max)
        self.fontinfo = wx.FontInfo(self.font_size).FaceName(self.font_name)
        self.font = wx.Font(self.fontinfo)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        w,h = dc.GetTextExtent("X")
        if (self.char_w is None or self.char_w != w or
            self.char_h is None or self.char_h != h):
            resize = True
        else:
            resize = False
        self.char_w = w
        self.char_h = h
        return resize
    def OnChangeSettings(self):
        self.scroll_outp = glsSettings.Get('term_scroll_output')
        self.scroll_keyp = glsSettings.Get('term_scroll_keypress')
        self.word_chars  = glsSettings.Get('term_wchars')
        self.color_en    = glsSettings.Get('term_color')
        self.color_fg    = glsSettings.Get('term_fgcolor')
        self.color_bg    = glsSettings.Get('term_bgcolor')
        self.font_name   = glsSettings.Get('term_font')
        self.font_base   = glsSettings.Get('term_font_size')
        if self.SetFont():
            self.OnSize()
        self.SetBackgroundColour(self.color_bg)
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnSetFocus(self, event=None):
        self.terminal.SetFocus(True)
        self.Refresh()
        self.SetCurrent()
        wx.YieldIfNeeded()
        return
    def OnKillFocus(self, event):
        self.terminal.SetFocus(False)
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def SearchSelectionFiles(self):
        text = self.GetSelectedText()
        evt = glsEvents.Search(id=wx.ID_ANY, name=text, content=None)
        wx.PostEvent(self.Parent, evt)
        return
    def SearchSelectionContents(self):
        text = self.GetSelectedText()
        evt = glsEvents.Search(id=wx.ID_ANY, name=None, content=text)
        wx.PostEvent(self.Parent, evt)
        return
    def OpenSelectionDir(self):
        evt = glsEvents.OpenDir(wx.ID_ANY, path=self.GetSelectedText())
        wx.PostEvent(self.Parent, evt)
        return
    def OnMenuItem(self, event):
        id = event.GetId() 
        if id == glsTermPanelPopupMenu.ID_COPY:
            self.Copy()
        elif id == glsTermPanelPopupMenu.ID_PASTE:
            self.Paste()
        elif id == glsTermPanelPopupMenu.ID_NEW_TERM:
            self.Parent.Parent.OnNewTerm()
        elif id == glsTermPanelPopupMenu.ID_NEW_DIR:
            self.OpenSelectionDir()
        elif id == glsTermPanelPopupMenu.ID_EXIT:
            self.OnClose()
        elif id == glsTermPanelPopupMenu.ID_SEARCH_FILES:
            self.SearchSelectionFiles()
        elif id == glsTermPanelPopupMenu.ID_SEARCH_CONTENTS:
            self.SearchSelectionContents()
        elif id == glsTermPanelPopupMenu.ID_NAME:
            with wx.TextEntryDialog(self, "Enter tab name:",
                                    caption="Enter Tab Name") as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
            self.SetTitle(dlg.GetValue())
        elif id == glsTermPanelPopupMenu.ID_FONT_UP:
            self.ZoomIn()
        elif id == glsTermPanelPopupMenu.ID_FONT_DOWN:
            self.ZoomOut()
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
        if (self.sel_start is None or self.sel_end is None or
            self.sel_start == self.sel_end):
            return None
        text = ""
        screen, rend = self.GetScrolledScreen()
        start = self.sel_start[0]*self.cols + self.sel_start[1]
        end   = self.sel_end[0]*self.cols + self.sel_end[1]
        max_ndx = self.rows*self.cols - 1
        start = min(max(start, 0), max_ndx)
        end = min(max(end, 0), max_ndx)
        if start > end:
            start, end = end, start
        for i in range(start, end):
            row, col = divmod(i, self.cols)
            if row < len(screen) and col < len(screen[row]):
                text += screen[row][col]
        return text
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
        self.terminal.PasteText(text)
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
        self.SetCurrent()
        self.SetFocus()
        self.left_down = True
        self.left_down_time = datetime.now()
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
        if (self.sel_start == self.sel_end or
            (datetime.now()-self.left_down_time).total_seconds() < self.select_delay):
            self.sel_start = None
            self.sel_end = None
        else:
            self.selected = self.Copy()
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnLeftDouble(self, event):
        self.SetCurrent()
        row, col = self.PointToCursor(event.GetPosition())
        screen, rend = self.GetScrolledScreen()
        if row >= len(screen) or col >= len(screen[row]):
            return
        if screen[row][col] not in self.word_chars:
            self.sel_start = None
            self.sel_end = None
            return
        start = row*self.cols + col
        sel_start = row, col
        for i in reversed(range(0,start)):
            r, c = divmod(i, self.cols)
            if row < len(screen) and col < len(screen[row]):
                if screen[r][c] not in self.word_chars:
                    break
                else:
                    sel_start = r, c
        self.sel_start = sel_start
        sel_end = row, col+1
        for i in range(start,self.rows*self.cols):
            r, c = divmod(i, self.cols)
            if row < len(screen) and col < len(screen[row]):
                if screen[r][c] not in self.word_chars:
                    break
                else:
                    sel_end = r, c+1
        self.sel_end = sel_end
        self.dbl_click = True
        if self.sel_start == self.sel_end:
            self.sel_start = None
            self.sel_end = None
        else:
            self.selected = self.Copy()
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnMove(self, event):
        if (self.left_down and
            (datetime.now()-self.left_down_time).total_seconds() > self.select_delay):
            self.sel_end = self.PointToCursor(event.GetPosition())
            self.Refresh()
            wx.YieldIfNeeded()
        return
    def OnRightDown(self, event):
        self.SetCurrent()
        self.SetFocus()
        avail_selection = self.GetSelectedText() != None
        avail_paste = self.ReadClipboard() != None
        self.PopupMenu(glsTermPanelPopupMenu(self, avail_selection, avail_paste),
                       event.GetPosition())
        return
    def ScrollToEnd(self):
        self.scrollbar.SetThumbPosition(self.scrollbar.GetRange())
        self.scrollbar.Refresh()
        self.Refresh()
        return
    def OnWheel(self, event):
        self.SetCurrent()
        self.SetFocus()
        if wx.WXK_SHIFT in self.keys_down:
            pos = self.scrollbar.GetThumbPosition()
            pmax = self.scrollbar.GetRange()
            if event.GetWheelRotation() < 0:
                self.scrollbar.SetThumbPosition(min(pmax, pos + self.scroll_delta))
            else:
                self.scrollbar.SetThumbPosition(max(0, pos - self.scroll_delta))
        else:
            if event.GetWheelRotation() < 0:
                for i in range(self.scroll_delta):
                    self.SendText(self.key_press.special_key_map[wx.WXK_DOWN], True)
            else:
                for i in range(self.scroll_delta):
                    self.SendText(self.key_press.special_key_map[wx.WXK_UP], True)
        self.scrollbar.Refresh()
        self.Refresh()
        return
    def GetColors(self, fgndx, bgndx):
        if self.color_en:
            if fgndx == 0:
                fgcolor = self.color_fg
            else:
                fgcolor = self.COLORS_256[fgndx]
            if bgndx == 0:
                bgcolor = self.color_bg
            else:
                bgcolor = self.COLORS_256[bgndx]
        else:
            fgcolor = self.color_fg
            bgcolor = self.color_bg
        if abs(sum(np.subtract(fgcolor, bgcolor))) < 64:
            fgcolor = tuple(np.subtract((255, 255, 255), fgcolor))
        return fgcolor, bgcolor
    def SetTextStyle(self, dc, cur_style, style, fgcolor, bgcolor):
        if cur_style != style:
            self.fontinfo = wx.FontInfo(self.font_size).FaceName(self.font_name)
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
    def GetScrolledScreen(self):
        screen = self.terminal.GetScreen()
        rendition = self.terminal.GetRendition()
        scroll = self.scroll
        if scroll > 0 and scroll < self.rows:
            screen = self.scrolled_text[-scroll:] + screen[:-scroll]
            rendition = self.scrolled_rendition[-scroll:] + rendition[:-scroll]
        elif scroll >= self.rows:
            start = len(self.scrolled_text) - scroll
            end = start + self.rows
            screen = self.scrolled_text[start:end]
            rendition = self.scrolled_rendition[start:end]
        return screen, rendition
    def DrawScreen(self, dc):
        screen, rendition = self.GetScrolledScreen()
        cur_style = 0
        cur_fgcolor_ndx = 0
        cur_bgcolor_ndx = 0
        cur_fgcolor, cur_bgcolor = self.GetColors(cur_fgcolor_ndx, cur_bgcolor_ndx)
        self.SetTextStyle(dc, None, cur_style, cur_fgcolor, cur_bgcolor)
        for row in range(len(screen)):
            col_start = 0
            text = ""
            for col in range(min(len(screen[row]),self.cols)):
                rend = rendition[row][col]
                style = rend & 0x0000ffff
                fgcolor_ndx = (rend>>16) & 255
                bgcolor_ndx = (rend>>24) & 255
                if (cur_style != style or
                    cur_fgcolor_ndx != fgcolor_ndx or
                    cur_bgcolor_ndx != bgcolor_ndx):
                    self.DrawText(dc, text, row, col_start)
                    col_start = col
                    text = ""
                    fgcolor, bgcolor = self.GetColors(fgcolor_ndx, bgcolor_ndx)
                    cur_style   = self.SetTextStyle(dc, cur_style, style, fgcolor, bgcolor)
                    cur_fgcolor = self.SetTextFGColor(dc, cur_fgcolor, fgcolor)
                    cur_bgcolor = self.SetTextBGColor(dc, cur_bgcolor, bgcolor)
                    cur_fgcolor_ndx = fgcolor_ndx
                    cur_bgcolor_ndx = bgcolor_ndx
                text += screen[row][col]
            self.DrawText(dc, text, row, col_start)
        return
    def DrawCursor(self, dc):
        if (not self.modes[self.terminal.MODE_DECTCEM] or
            self.cursor_style == self.terminal.CURSOR_STYLE_INVISIBLE):
            return
        if self.scroll >= self.rows:
            return
        new_cr = min(max(self.cursor_pos[0], 0), self.rows-1)
        new_cc = min(max(self.cursor_pos[1], 0), self.cols-1)
        self.cursor_pos = (new_cr, new_cc)
        cursor_pos = [new_cr + self.scroll, new_cc]
        if cursor_pos[0] >= self.rows:
            return
        if self.HasFocus():
            self.pen = wx.Pen((0,255,0,175))
            self.brush = wx.Brush((0,255,0))
        else:
            self.pen = wx.Pen((255,128,0,128))
            self.brush = wx.Brush((255,128,0))
        dc.SetBrush(self.brush)
        dc.SetPen(self.pen)
        if (self.cursor_style == self.terminal.CURSOR_STYLE_DEFAULT or
            self.cursor_style == self.terminal.CURSOR_STYLE_BLOCK):
            dc.DrawRectangle(cursor_pos[1]*self.char_w, cursor_pos[0]*self.char_h,
                             self.char_w, self.char_h)
            screen, rend = self.GetScrolledScreen()
            self.fontinfo = wx.FontInfo(self.font_size).FaceName(self.font_name).Bold()
            self.font = wx.Font(self.fontinfo)
            dc.SetFont(self.font)
            dc.SetTextForeground((0,0,0))
            dc.DrawText(screen[cursor_pos[0]][cursor_pos[1]],
                        cursor_pos[1]*self.char_w, cursor_pos[0]*self.char_h)
        elif self.cursor_style == self.terminal.CURSOR_STYLE_BAR:
            dc.DrawRectangle(cursor_pos[1]*self.char_w, cursor_pos[0]*self.char_h,
                             2, self.char_h)
        elif self.cursor_style == self.terminal.CURSOR_STYLE_UNDERLINE:
            dc.DrawRectangle(cursor_pos[1]*self.char_w, (cursor_pos[0]+1)*self.char_h-2,
                             self.char_w, 2)
        return
    def DrawSelection(self, dc):
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
        return
    def OnPaint(self, event):
        # Draw with double buffering.
        dc = wx.MemoryDC()
        dc.SelectObject(self.dc_buffer)
        dc.Clear()
        dc.SetPen(wx.Pen(self.color_bg))
        dc.SetBrush(wx.Brush(self.color_bg))
        dc.DrawRectangle(0, 0, self.Size[0], self.Size[1])
        scroll = self.scrollbar.GetRange() - self.rows - self.scrollbar.GetThumbPosition()
        self.scroll = scroll
        self.DrawScreen(dc)
        self.DrawCursor(dc)
        self.DrawSelection(dc)
        del dc
        dc = wx.BufferedPaintDC(self, self.dc_buffer)
        return
    def UpdateScrollbar(self, new_lines=0):
        self.scrollbar.SetSize(self.Size[0]-self.scrollbar_w, 0, self.scrollbar_w,
                               self.Size[1])
        scroll = self.scrollbar.GetRange() - self.rows - self.scrollbar.GetThumbPosition()
        if scroll and not self.scroll_outp:
            new_lines = 0
        self.scrollbar.SetScrollbar(self.scrollbar.GetThumbPosition() + new_lines,
                                    self.rows, self.rows + len(self.scrolled_text),
                                    self.scrollbar_w, refresh=True)
        self.scrollbar.Refresh()
        self.Refresh()
        return
    def OnScroll(self, event):
        self.SetCurrent()
        self.scrollbar.Refresh()
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnSize(self, event=None):
        self.rows = int((self.Size[1]) / self.char_h)
        self.cols = int((self.Size[0]-self.scrollbar_w) / self.char_w)
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
        self.dc_buffer = wx.Bitmap(*self.Size)
        self.scrollbar.Refresh()
        self.Refresh()
        return
    def SendText(self, text, user=True):
        if user and self.scroll_keyp:
            self.ScrollToEnd()
        if text is None or text == "":
            return
        os.write(self.io, bytes(text,'utf-8'))
        return
    def OnChar(self, event):
        return
    def OnKeyDown(self, event):
        key = event.GetKeyCode()
        self.keys_down[key] = True
        seq = self.key_press.KeyCodeToSequence(key)
        self.SendText(seq, True)
        event.Skip()
        return
    def OnKeyUp(self, event):
        key = event.GetKeyCode()
        if key in self.keys_down:
            del self.keys_down[event.GetKeyCode()]
        event.Skip()
        return
    def OnTermScrollUpScreen(self):
        if not self:
            return
        text = "".join(self.terminal.GetScreen()[0])
        rendition = self.terminal.GetRendition()[0]
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
        if not self:
            return
        self.Refresh()
        text = self.GetSelectedText()
        if text != self.selected and self.left_down == False:
            self.sel_start = None
            self.sel_end = None
            self.selected = None
        wx.YieldIfNeeded()
        return
    def OnTermUpdateCursorPos(self):
        if not self:
            return
        self.cursor_pos = self.terminal.GetCursorPos()
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def OnTermUpdateWindowTitle(self, title):
        if not self:
            return
        text = ""
        for c in title:
            if not c.isprintable():
                break
            text += c
        self.SetTitle(text)
        return
    def OnTermUpdateMode(self, modes):
        if not self:
            return
        self.modes = dict(modes)
        return
    def OnTermUpdateCursor(self, style):
        if not self:
            return
        self.cursor_style = style
        return
    def OnTermSendData(self, data):
        if not self:
            return
        self.SendText(data, False)
        return
    def SetCurrent(self):
        evt = glsEvents.TabCurrent(wx.ID_ANY, terminal=self)
        wx.PostEvent(self.Parent, evt)
        return
    def SetTitle(self, title):
        evt = glsEvents.TabTitle(id=wx.ID_ANY, title=title, terminal=self)
        wx.PostEvent(self.Parent, evt)
        return
    def OnChildOutputThreadExit(self, event):
        if self.child_output_notifier_thread is not None:
            self.child_output_notifier_thread.join()
            self.child_output_notifier_thread = None
        if not self.notified_parent_closed:
            evt = glsEvents.TabClose(wx.ID_ANY, terminal=self)
            wx.PostEvent(self.Parent, evt)
            self.notified_parent_closed = True
        return
    def OnClose(self, event=None):
        self.stop_output_notifier = True
        glsSettings.RemoveWatcher(self.OnChangeSettings)
        return
    def OnDestroy(self, event):
        self.stop_output_notifier = True
        glsSettings.RemoveWatcher(self.OnChangeSettings)
        if self.child_output_notifier_thread is not None:
            self.child_output_notifier_thread.join()
        return

################################################################

class glsTermNotebook(wx.Window):
    ICON_TERM      = 0
    ICON_PLACEHLDR = 1
    def __init__(self, parent, min_term_size, callback_placeholder):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTermNotebook, self).__init__(parent, style=style)
        self.callback_placeholder = callback_placeholder
        self.current = False
        self.Bind(glsEvents.EVT_TAB_TITLE, self.OnTermTitle)
        self.Bind(glsEvents.EVT_TAB_CLOSE, self.OnTermClose)
        self.Bind(glsEvents.EVT_TAB_CURRENT, self.OnTermCurrent)
        self.min_term_size = min_term_size
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(glsIcons.Get('monitor'))
        self.image_list.Add(glsIcons.Get('error'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = []
        self.OnNewTerm()
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnNewTerm(self):
        self.RemovePlaceHolder()
        terminal = glsTerminalPanel(self.notebook, self.min_term_size)
        self.tabs.append(terminal)
        self.notebook.AddPage(terminal, " Terminal " + str(len(self.tabs)))
        self.notebook.ChangeSelection(len(self.tabs)-1)
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_TERM)
        return terminal
    def CloseTerminal(self, terminal):
        if terminal is None:
            return
        for i,t in enumerate(self.tabs):
            if terminal == t:
                self.notebook.DeletePage(i)
                self.notebook.SendSizeEvent()
                self.tabs.remove(self.tabs[i])
        self.AddPlaceHolder()
        return
    def OnTermClose(self, event):
        self.CloseTerminal(event.terminal)
        return
    def OnTermTitle(self, event):
        title = event.title
        if not len(title):
            return
        if len(title) > 24:
            title = title[:24]
        terminal = event.terminal
        for i,t in enumerate(self.tabs):
            if terminal == t:
                self.notebook.SetPageText(i, " "+title)
        return
    def OnTermCurrent(self, event):
        self.SetCurrent(True)
        return
    def RemovePlaceHolder(self):
        if len(self.tabs) != 1 or not isinstance(self.tabs[0], glsPlaceHolder):
            return
        self.notebook.DeletePage(0)
        self.notebook.SendSizeEvent()
        self.tabs.remove(self.tabs[0])
        self.callback_placeholder(False)
        return
    def AddPlaceHolder(self):
        if len(self.tabs):
            return
        placeholder = glsPlaceHolder(self.notebook, "All Terminal Tabs Are Closed")
        self.tabs.append(placeholder)
        self.notebook.AddPage(placeholder, " No Terminals")
        self.notebook.SetPageImage(len(self.tabs)-1, self.ICON_PLACEHLDR)
        self.notebook.SetSelection(len(self.tabs)-1)
        self.callback_placeholder(True)
        return
    def IsCurrent(self):
        return self.current
    def SetCurrent(self, state):
        self.current = state
        if self.current:
            evt = glsEvents.TabCurrent(wx.ID_ANY, notebook=self)
            wx.PostEvent(self.Parent, evt)
        return
    def GetCurrentTerm(self):
        current = self.notebook.GetSelection()
        if (current >= 0 and current < len(self.tabs) and
            not isinstance(self.tabs[current], glsPlaceHolder)):
            return self.tabs[current]
        return None
    def SendText(self, text):
        if text is None or text == "":
            return
        current = self.GetCurrentTerm()
        current.SendText(text)
        return

################################################################

class glsTermsPanel(wx.Window):
    ID_OPEN_DIR    = 1000
    ID_OPEN_FILE   = 1001
    ID_SEARCH_FILE = 1002
    ID_SEARCH_CNTS = 1003
    ID_TERM_NEW    = 1004
    ID_COPY        = 1005
    ID_PASTE       = 1006
    ID_VERTICAL    = 1007
    ID_HORIZONTAL  = 1008
    ID_ZOOM_IN     = 1009
    ID_ZOOM_OUT    = 1010
    ID_EXIT        = 1011
    def __init__(self, parent, min_term_size, callback_layout):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsTermsPanel, self).__init__(parent,style=style)
        self.callback_layout = callback_layout
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.VetoEvent)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.VetoEvent)
        self.Bind(glsEvents.EVT_TAB_CURRENT, self.OnCurrentNotebook)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
        tools = [ (self.ID_EXIT, "Close Tab", 'cross', self.OnToolCloseTab),
                  (self.ID_TERM_NEW, "New Terminal", 'monitor_add', self.OnToolTermNew),
                  (self.ID_HORIZONTAL, "Split Horizontal", 'application_tile_vertical',
                   self.OnToolHorizontal),
                  (self.ID_VERTICAL, "Split Vertical", 'application_tile_horizontal',
                   self.OnToolVertical),
                  (self.ID_OPEN_DIR, "Open Directory", 'chart_organisation_add', self.OnToolOpenDir),
                  (self.ID_SEARCH_FILE, "Search Files", 'magnifier', self.OnToolSearchFiles),
                  (self.ID_SEARCH_CNTS, "Search Contents", 'magnifier_zoom_in',
                   self.OnToolSearchContents),
                  (self.ID_COPY, "Copy", 'page_copy', self.OnToolCopy),
                  (self.ID_PASTE, "Paste", 'page_paste', self.OnToolPaste),
                  (self.ID_ZOOM_OUT, "Zoom Out", 'font_delete', self.OnToolZoomOut),
                  (self.ID_ZOOM_IN, "Zoom In", 'font_add', self.OnToolZoomIn) ]
        for tool in tools:
            tid, text, icon, callback = tool
            self.toolbar.AddTool(tid, text, glsIcons.Get(icon), wx.NullBitmap,
                                 wx.ITEM_NORMAL, text, text, None)
            self.Bind(wx.EVT_TOOL, callback, id=tid)
        self.toolbar.Realize()
        box_main.Add(self.toolbar, 0, wx.EXPAND)
        self.min_term_size = min_term_size
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(self.min_term_size[1])
        self.notebooks = []
        for n in range(2):
            notebook = glsTermNotebook(self.splitter, self.min_term_size,
                                       self.OnPlaceHolder)
            self.notebooks.append(notebook)
        self.notebooks_active = len(self.notebooks)
        self.split_mode = wx.SPLIT_HORIZONTAL
        self.splitter.SplitHorizontally(self.notebooks[0], self.notebooks[1])        
        box_main.Add(self.splitter, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 0)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        wx.CallAfter(self.OnToolHorizontal)
        return
    def VetoEvent(self, event):
        return
    def OnToolOpenDir(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.OpenSelectionDir()
        return
    def OnToolTermNew(self, event):
        self.TerminalStart()
        return
    def OnToolSearchFiles(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.SearchSelectionFiles()
        return
    def OnToolSearchContents(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.SearchSelectionContents()
        return
    def OnToolPaste(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.Paste()
        return
    def OnToolCopy(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.Copy()
        return
    def OnToolZoomIn(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.ZoomIn()
        return
    def OnToolZoomOut(self, event):
        term = self.GetCurrentTerm()
        if term is not None:
            term.ZoomOut()
        return
    def Resize(self, split_mode):
        pad = 50
        if split_mode == wx.SPLIT_HORIZONTAL:
            splitter_size = (self.min_term_size[0] + pad,
                             self.min_term_size[1]*2 +
                             self.splitter.GetSashSize() + pad)
            min_pane_size = self.min_term_size[1]
        elif split_mode == wx.SPLIT_VERTICAL:
            splitter_size = (self.min_term_size[0]*2 +
                             self.splitter.GetSashSize() + pad,
                             self.min_term_size[1] + pad)
            min_pane_size = self.min_term_size[0]
        else:
            splitter_size = (self.min_term_size[0] + pad,
                             self.min_term_size[1] + pad)
            min_pane_size = 0
        if split_mode is None:
            self.splitter.Unsplit()
        else:
            self.splitter.SetSplitMode(split_mode)
            self.splitter.SetMinimumPaneSize(min_pane_size)
            self.splitter.SetMinSize(splitter_size)
            self.splitter.Layout()
        self.Layout()
        self.Refresh()
        self.callback_layout((splitter_size[0],
                              splitter_size[1] + self.toolbar.Size[1] + pad))
        return
    def OnToolHorizontal(self, event=None):
        self.split_mode = wx.SPLIT_HORIZONTAL
        self.Resize(self.split_mode)
        for nb in self.notebooks:
            if nb.GetCurrentTerm() is None:
                nb.OnNewTerm()
        return
    def OnToolVertical(self, event=None):
        self.split_mode = wx.SPLIT_VERTICAL
        self.Resize(self.split_mode)
        for nb in self.notebooks:
            if nb.GetCurrentTerm() is None:
                nb.OnNewTerm()
        return
    def OnToolCloseTab(self, event):
        self.TerminalClose()
        return
    def OnPlaceHolder(self, placeholder):
        orig_active = self.notebooks_active
        if placeholder:
            self.notebooks_active -= 1
        else:
            self.notebooks_active += 1
        if self.notebooks_active == 2:
            if self.split_mode == wx.SPLIT_HORIZONTAL:
                self.splitter.SplitHorizontally(self.notebooks[0], self.notebooks[1])
            elif self.split_mode == wx.SPLIT_VERTICAL:
                self.splitter.SplitVertically(self.notebooks[0], self.notebooks[1])
        elif orig_active == 2 and self.notebooks_active == 1:
            if self.notebooks[0].GetCurrentTerm() is not None:
                active = 0
                inactive = 1
            else:
                active = 1
                inactive = 0
            self.notebooks = [self.notebooks[active], self.notebooks[inactive]]
            self.Resize(None)
            self.notebooks[0].Show()
            self.notebooks[1].Hide()
            self.notebooks[0].SetCurrent(True)
            window = self.splitter.GetWindow1()
            self.splitter.ReplaceWindow(window, self.notebooks[0])
        elif self.notebooks_active == 0:
            self.Resize(None)
        return
    def OnCurrentNotebook(self, event):
        notebook = event.notebook
        for nb in self.notebooks:
            if nb != notebook:
                nb.SetCurrent(False)
        return
    def GetCurrentNotebook(self):
        for nb in self.notebooks:
            if nb.IsCurrent():
                return nb
        if len(self.notebooks):
            self.notebooks[0].SetCurrent(True)
            return self.notebooks[0]
        return None
    def GetCurrentTerm(self):
        notebook = self.GetCurrentNotebook()
        if notebook is not None:
            return notebook.GetCurrentTerm()
        return None
    def EditorLineSet(self, line):
        term = self.GetCurrentTerm()
        if term is None:
            return
        command = glsSettings.Get('edit_line')
        command = command.replace("{LINE}",str(line))
        glsLog.add("EditorLineSet(): "+str(line))
        term.SendText(command)
        return
    def EditorFileOpen(self, path):
        term = self.GetCurrentTerm()
        if term is None:
            return
        command = glsSettings.Get('edit_open')
        command = command.replace("{FILE}",str(path))
        glsLog.add("EditorFileOpen(): "+str(path))
        term.SendText(command)
        return
    def EditorStart(self, path):
        notebook = self.GetCurrentNotebook()
        if notebook is None:
            return
        term = notebook.OnNewTerm()
        command = glsSettings.Get('edit_path') + " '%s'\x0a"%(path)
        glsLog.add("EditorStart(): "+command)
        term.SendText(command)
        return
    def TerminalStart(self):
        notebook = self.GetCurrentNotebook()
        if notebook is None:
            return
        notebook.OnNewTerm()
        return
    def TerminalClose(self):
        notebook = self.GetCurrentNotebook()
        if notebook is None:
            return
        term = notebook.GetCurrentTerm()
        if term is not None:
            notebook.CloseTerminal(term)
        return

################################################################
