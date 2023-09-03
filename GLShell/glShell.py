#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import pty
import threading
import select
import wx
import fcntl
import termios
import struct
import tty
from threading import Thread

import fdpCanvas
import glsProject as glsp
import TermEmulator
import glsSettings

ID_TERMINAL = 1

def PrintStringAsAscii(s):
    import string
    for ch in s:
        if ch in string.printable:
            print(ch, end="")
        else:
            print(ord(ch), end="")
    return

class glShell(wx.Frame):
    fdp_canvas = None
    def __init__(self,app):
        self.app = app
        wx.Frame.__init__(self, None, wx.ID_ANY, "TermEmulator Demo", \
                          size = (1366, 768))
        self.settings = glsSettings.glsSettings()
        self.settings.Load()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.InitUI()
        return
    def InitMenuBar(self):
        menubar = wx.MenuBar() 
        # File menue.
        fileMenu = wx.Menu() 
        newitem = wx.MenuItem(fileMenu, wx.ID_NEW, text = "New", kind = wx.ITEM_NORMAL) 
        fileMenu.Append(newitem)
        openitem = wx.MenuItem(fileMenu, wx.ID_OPEN, text = "Open", kind = wx.ITEM_NORMAL) 
        fileMenu.Append(openitem) 
        saveitem = wx.MenuItem(fileMenu, wx.ID_SAVE, text = "Save", kind = wx.ITEM_NORMAL) 
        fileMenu.Append(saveitem) 
        saveasitem = wx.MenuItem(fileMenu, wx.ID_SAVEAS, text = "Save as", kind = wx.ITEM_NORMAL) 
        fileMenu.Append(saveasitem) 
        closeitem = wx.MenuItem(fileMenu, wx.ID_CLOSE, text = "Close", kind = wx.ITEM_NORMAL) 
        fileMenu.Append(closeitem) 
        fileMenu.AppendSeparator()
        quit = wx.MenuItem(fileMenu, wx.ID_EXIT, '&Quit') 
        fileMenu.Append(quit) 
        menubar.Append(fileMenu, '&File')
        # Edit menue.
        editMenu = wx.Menu() 
        copyItem = wx.MenuItem(editMenu, wx.ID_COPY, text = "Copy", kind = wx.ITEM_NORMAL)
        editMenu.Append(copyItem) 
        cutItem = wx.MenuItem(editMenu, wx.ID_CUT, text = "Cut", kind = wx.ITEM_NORMAL) 
        editMenu.Append(cutItem) 
        pasteItem = wx.MenuItem(editMenu, wx.ID_PASTE, text = "Paste", kind = wx.ITEM_NORMAL) 
        editMenu.Append(pasteItem)
        editMenu.AppendSeparator()
        self.ID_SETTINGS = 1337
        settingsItem = wx.MenuItem(editMenu, self.ID_SETTINGS, text = "Settings",
                                   kind = wx.ITEM_NORMAL) 
        editMenu.Append(settingsItem) 
        menubar.Append(editMenu, '&Edit')
        # Connect menus to menu bar.
        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.MenuHandler)
        self.settings_frame = None
        return
    def MenuHandler(self,event):
        id = event.GetId() 
        if id == wx.ID_EXIT:
            sys.exit()
        elif id == self.ID_SETTINGS:
            if self.settings_frame is None:
                self.settings_frame = glsSettings.SettingsFrame(self, self.settings)
                self.settings_frame.Show()
                self.settings_frame.Raise()
            else:
                self.settings_frame.Raise()
        return
    def InitUI(self):
        # Setup menu bar.
        self.InitMenuBar()
        # Main box.
        box_main = wx.BoxSizer(wx.VERTICAL)
        # Toolbar box.
        self.tool_panel = wx.Panel(self)
        self.tool_panel.SetBackgroundColour(wx.Colour(64,64,64))
        box_tool = wx.BoxSizer(wx.HORIZONTAL)
        self.bt_run = wx.Button(self.tool_panel, wx.ID_ANY, "Run")
        self.bt_run.Bind(wx.EVT_BUTTON, self.OnRun, id = self.bt_run.GetId())
        box_tool.Add(self.bt_run, 0, wx.LEFT | wx.RIGHT, 10)
        box_main.Add(self.tool_panel, 0, wx.ALIGN_RIGHT, wx.TOP | wx.BOTTOM, 0)
        # Graph and Terminal side-by-side.
        box_gr_trm = wx.BoxSizer(wx.HORIZONTAL)
        # OpenGL FDP panel.
        self.glpanel = wx.Panel(self, 0)
        self.fdp_canvas = fdpCanvas.fdpCanvas(self.glpanel, pos=(0,0), size=(644,768))
        box_gr_trm.Add(self.glpanel, 1, wx.EXPAND | wx.ALL);
        # Terminal rendering.
        self.txtCtrlTerminal = wx.TextCtrl(self, ID_TERMINAL, 
                                           style = wx.TE_MULTILINE 
                                                   | wx.TE_DONTWRAP)
        self.txtCtrlTerminal.SetDefaultStyle(
            wx.TextAttr(wx.GREEN, wx.BLACK))
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL,
                       wx.FONTWEIGHT_NORMAL, False)
        self.txtCtrlTerminal.SetFont(font)
        self.txtCtrlTerminal.Bind(wx.EVT_CHAR, self.OnTerminalChar,
                                  id = ID_TERMINAL)
        self.txtCtrlTerminal.Bind(wx.EVT_KEY_DOWN, self.OnTerminalKeyDown,
                                  id = ID_TERMINAL)
        self.txtCtrlTerminal.Bind(wx.EVT_KEY_UP, self.OnTerminalKeyUp,
                                  id = ID_TERMINAL)
        box_gr_trm.Add(self.txtCtrlTerminal, 1, wx.EXPAND | wx.ALL);
        box_main.Add(box_gr_trm, 0, wx.TOP | wx.BOTTOM, 0)       
        # Size and scrolling.
        self.SetSizerAndFit(box_main)
        self.termRows = self.settings.term_rows
        self.termCols = self.settings.term_cols
        self.FillScreen()
        self.linesScrolledUp = 0
        self.scrolledUpLinesLen = 0
        # Terminal Emulator.
        self.termEmulator = TermEmulator.V102Terminal(self.termRows,
                                                      self.termCols)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_SCROLL_UP_SCREEN,
                                      self.OnTermEmulatorScrollUpScreen)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UPDATE_LINES,
                                      self.OnTermEmulatorUpdateLines)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UPDATE_CURSOR_POS,
                                      self.OnTermEmulatorUpdateCursorPos)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UPDATE_WINDOW_TITLE,
                                      self.OnTermEmulatorUpdateWindowTitle)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UNHANDLED_ESC_SEQ,
                                      self.OnTermEmulatorUnhandledEscSeq)
        # State and update.
        self.isRunning = False
        self.UpdateUI()
        self.Show(True)
        return
    def AddProject(self,proj):
        self.project = proj;
        if self.fdp_canvas is not None:
            self.fdp_canvas.AddProject(self.project)
        return
    def FillScreen(self):
        """
        Fills the screen with blank lines so that we can update terminal
        dirty lines quickly.
        """
        text = ""
        for i in range(self.termRows):
            for j in range(self.termCols):
                text += ' '
            text += '\n'
            
        text = text.rstrip('\n')
        self.txtCtrlTerminal.SetValue(text)
        return
    def UpdateUI(self):
        self.bt_run.Enable(not self.isRunning)
        self.txtCtrlTerminal.Enable(self.isRunning)
        return
    def OnRun(self, event):
        path = self.settings.shell_path
        basename = os.path.basename(path)
        arglist = [ basename ]
        arguments = self.settings.shell_args
        if arguments != "":
            for arg in arguments.split(' '):
                arglist.append(arg)
        self.termRows = self.settings.term_rows
        self.termCols = self.settings.term_cols
        rows, cols = self.termEmulator.GetSize()
        if rows != self.termRows or cols != self.termCols:
            self.termEmulator.Resize (self.termRows, self.termCols)
        processPid, processIO = pty.fork()
        if processPid == 0: # child process
            os.execl(path, *arglist)
        print("Child process pid {}".format(processPid))
        # Sets raw mode
        #tty.setraw(processIO)
        # Sets the terminal window size
        fcntl.ioctl(processIO, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.termRows, self.termCols, 0, 0))
        tcattrib = termios.tcgetattr(processIO)
        tcattrib[3] = tcattrib[3] & ~termios.ICANON
        termios.tcsetattr(processIO, termios.TCSAFLUSH, tcattrib)
        self.processPid = processPid
        self.processIO = processIO
        self.processOutputNotifierThread = threading.Thread(
            target = self.__ProcessOuputNotifierRun)
        self.waitingForOutput = True
        self.stopOutputNotifier = False
        self.processOutputNotifierThread.start()
        self.isRunning = True
        self.UpdateUI()
        return
    def OnResize(self, event):        
        self.termRows = self.settings.term_rows
        self.termCols = self.settings.term_cols
        # Resize emulator
        self.termEmulator.Resize(self.termRows, self.termCols)
        # Resize terminal
        fcntl.ioctl(self.processIO, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.termRows, self.termCols, 0, 0))
        self.FillScreen()
        self.UpdateDirtyLines(range(self.termRows))
        return
    def __ProcessIsAlive(self):
        try:
            pid, status = os.waitpid(self.processPid, os.WNOHANG)
            if pid == self.processPid and os.WIFEXITED(status):
                return False
        except:
            return False
        return True
    def __ProcessOuputNotifierRun(self):
        inpSet = [ self.processIO ]
        while (not self.stopOutputNotifier and self.__ProcessIsAlive()):
            if self.waitingForOutput:
                inpReady, outReady, errReady = select.select(inpSet, [], [], 0)
                if self.processIO in inpReady:
                    self.waitingForOutput = False
                    wx.CallAfter(self.ReadProcessOutput)
        if not self.__ProcessIsAlive():
            self.isRunning = False
            wx.CallAfter(self.ReadProcessOutput)
            wx.CallAfter(self.UpdateUI)
            print("Process exited")
        print("Notifier thread exited")
        return
    def SetTerminalRenditionStyle(self, style):
        fontStyle = wx.FONTSTYLE_NORMAL
        fontWeight = wx.FONTWEIGHT_NORMAL
        underline = False
        if style & self.termEmulator.RENDITION_STYLE_BOLD:
            fontWeight = wx.FONTWEIGHT_BOLD
        elif style & self.termEmulator.RENDITION_STYLE_DIM:
            fontWeight = wx.FONTWEIGHT_LIGHT
        if style & self.termEmulator.RENDITION_STYLE_ITALIC:
            fontStyle = wx.FONTSTYLE_ITALIC
        if style & self.termEmulator.RENDITION_STYLE_UNDERLINE:
            underline = True
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, fontStyle, fontWeight,
                       underline)
        self.txtCtrlTerminal.SetFont(font)
        return
    def SetTerminalRenditionForeground(self, fgcolor):
        if fgcolor != 0:
            if fgcolor == 1:
                self.txtCtrlTerminal.SetForegroundColour((0, 0, 0))
            elif fgcolor == 2:
                self.txtCtrlTerminal.SetForegroundColour((255, 0, 0))
            elif fgcolor == 3:
                self.txtCtrlTerminal.SetForegroundColour((0, 255, 0))
            elif fgcolor == 4:
                self.txtCtrlTerminal.SetForegroundColour((255, 255, 0))
            elif fgcolor == 5:
                self.txtCtrlTerminal.SetForegroundColour((0, 0, 255))
            elif fgcolor == 6:
                self.txtCtrlTerminal.SetForegroundColour((255, 0, 255))
            elif fgcolor == 7:
                self.txtCtrlTerminal.SetForegroundColour((0, 255, 255))                
            elif fgcolor == 8:
                self.txtCtrlTerminal.SetForegroundColour((255, 255, 255))
        else:
            self.txtCtrlTerminal.SetForegroundColour((0, 255, 0))
        return
    def SetTerminalRenditionBackground(self, bgcolor):
        if bgcolor != 0:
            if bgcolor == 1:
                self.txtCtrlTerminal.SetBackgroundColour((0, 0, 0))
            elif bgcolor == 2:
                self.txtCtrlTerminal.SetBackgroundColour((255, 0, 0))
            elif bgcolor == 3:
                self.txtCtrlTerminal.SetBackgroundColour((0, 255, 0))
            elif bgcolor == 4:
                self.txtCtrlTerminal.SetBackgroundColour((255, 255, 0))
            elif bgcolor == 5:
                self.txtCtrlTerminal.SetBackgroundColour((0, 0, 255))
            elif bgcolor == 6:
                self.txtCtrlTerminal.SetBackgroundColour((255, 0, 255))
            elif bgcolor == 7:
                self.txtCtrlTerminal.SetBackgroundColour((0, 255, 255))                
            elif bgcolor == 8:
                self.txtCtrlTerminal.SetBackgroundColour((255, 255, 255))
        else:
            self.txtCtrlTerminal.SetBackgroundColour((0, 0, 0))
        return
    def GetTextCtrlLineStart(self, lineNo):
        lineStart = self.scrolledUpLinesLen        
        lineStart += (self.termCols + 1) * (lineNo - self.linesScrolledUp)
        return lineStart
    def UpdateCursorPos(self):
        row, col = self.termEmulator.GetCursorPos()
        lineNo = self.linesScrolledUp + row
        insertionPoint = self.GetTextCtrlLineStart(lineNo)
        insertionPoint += col 
        self.txtCtrlTerminal.SetInsertionPoint(insertionPoint)
        return
    def UpdateDirtyLines(self, dirtyLines = None):
        text = ""
        curStyle = 0
        curFgColor = 0
        curBgColor = 0
        self.SetTerminalRenditionStyle(curStyle)
        self.SetTerminalRenditionForeground(curFgColor)
        self.SetTerminalRenditionBackground(curBgColor)
        screen = self.termEmulator.GetRawScreen()
        screenRows = self.termEmulator.GetRows()
        screenCols = self.termEmulator.GetCols()
        if dirtyLines == None:
            dirtyLines = self.termEmulator.GetDirtyLines()
        disableTextColoring = not self.settings.term_color
        for row in dirtyLines:
            text = ""
            # finds the line starting and ending index
            lineNo = self.linesScrolledUp + row
            lineStart = self.GetTextCtrlLineStart(lineNo)
            #lineText = self.txtCtrlTerminal.GetLineText(lineNo)
            #lineEnd = lineStart + len(lineText)
            lineEnd = lineStart + self.termCols
            # delete the line content
            self.txtCtrlTerminal.Replace(lineStart, lineEnd, "")
            self.txtCtrlTerminal.SetInsertionPoint(lineStart)
            for col in range(screenCols):
                style, fgcolor, bgcolor = self.termEmulator.GetRendition(row,
                                                                         col)
                if not disableTextColoring and (curStyle != style 
                                                or curFgColor != fgcolor \
                                                or curBgColor != bgcolor):
                    if text != "":
                        self.txtCtrlTerminal.WriteText(text)
                        text = ""
                    if curStyle != style:
                        curStyle = style
                        #print("Setting style {}".format(curStyle))
                        if style == 0:
                            self.txtCtrlTerminal.SetForegroundColour((0, 255, 0))
                            self.txtCtrlTerminal.SetBackgroundColour((0, 0, 0))
                        elif style & self.termEmulator.RENDITION_STYLE_INVERSE:
                            self.txtCtrlTerminal.SetForegroundColour((0, 0, 0))
                            self.txtCtrlTerminal.SetBackgroundColour((255, 255, 255))
                        else:
                            # skip other styles since TextCtrl doesn't support
                            # multiple fonts(bold, italic and etc)
                            pass
                    if curFgColor != fgcolor:
                        curFgColor = fgcolor
                        #print("Setting foreground {}".format(curFgColor))
                        self.SetTerminalRenditionForeground(curFgColor)
                    if curBgColor != bgcolor:
                        curBgColor = bgcolor
                        #print("Setting background {}".format(curBgColor))
                        self.SetTerminalRenditionBackground(curBgColor)
                text += screen[row][col]
            self.txtCtrlTerminal.WriteText(text)
        return
    def OnTermEmulatorScrollUpScreen(self):
        blankLine = "\n"
        for i in range(self.termEmulator.GetCols()):
            blankLine += ' '
        #lineLen =  len(self.txtCtrlTerminal.GetLineText(self.linesScrolledUp))
        lineLen = self.termCols
        self.txtCtrlTerminal.AppendText(blankLine)
        self.linesScrolledUp += 1
        self.scrolledUpLinesLen += lineLen + 1
        return
    def OnTermEmulatorUpdateLines(self):
        self.UpdateDirtyLines()
        wx.YieldIfNeeded()
        return
    def OnTermEmulatorUpdateCursorPos(self):
        self.UpdateCursorPos()
        return
    def OnTermEmulatorUpdateWindowTitle(self, title):
        self.SetTitle(title)
        return
    def OnTermEmulatorUnhandledEscSeq(self, escSeq):
        print("Unhandled escape sequence: [{}".format(escSeq))
        return
    def ReadProcessOutput(self):
        #!!avose: bytes
        output = bytes("",'utf8')
        try:
            while True:
                data = os.read(self.processIO, 512)
                datalen = len(data)
                output += data
                if datalen < 512:
                    break
        except:
            #!!avose: bytes
            output = bytes("",'utf8')
        #print("Received: ", end="")
        #PrintStringAsAscii(output)
        #print(output)
        #print("")
        self.termEmulator.ProcessInput(output.decode())
        # resets text control's foreground and background
        #!!avose:
        self.txtCtrlTerminal.SetForegroundColour((0, 255, 0))
        self.txtCtrlTerminal.SetBackgroundColour((0, 0, 0))
        self.waitingForOutput = True
        return
    def OnTerminalKeyDown(self, event):
        #print("KeyDown {}".format(event.GetKeyCode()))
        event.Skip()
        return
    def OnTerminalKeyUp(self, event):
        #print("KeyUp {}".format(event.GetKeyCode()))
        event.Skip()
        return
    def OnTerminalChar(self, event):
        if not self.isRunning:
            return
        ascii = event.GetKeyCode()
        #print("ASCII = {}".format(ascii))
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
            os.write(self.processIO, bytes(keystrokes,'utf-8'))
        return
    def OnClose(self, event):
        if self.isRunning:
            self.stopOutputNotifier = True
            self.processOutputNotifierThread.join(None)
        event.Skip()
        return

if __name__ == '__main__':
    proj_path = sys.argv[1] if len(sys.argv) == 2 else "."
    project = glsp.glsProject(paths=[proj_path])
    app = wx.App(0);
    gl_shell = glShell(app)
    app.SetTopWindow(gl_shell)
    gl_shell.AddProject(project)
    app.MainLoop()
