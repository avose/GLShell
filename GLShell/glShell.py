#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import wx
from threading import Thread

from glsTerminalPanel import glsTerminalPanel
import glsGraphCanvas
import glsProject as glsp
import glsSettings

VERSION = "0.0.1"

class glShell(wx.Frame):
    def __init__(self,app):
        self.app = app
        wx.Frame.__init__(self, None, wx.ID_ANY,
                          "glShell - "+VERSION,
                          size = (1366, 768))
        self.settings = glsSettings.glsSettings()
        self.settings.Load()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.InitUI()
        return
    def OnCharHook(self,event):
        event.DoAllowNextEvent()
        event.Skip()
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
        box_tool = wx.BoxSizer(wx.HORIZONTAL)
        self.bt_run = wx.Button(self, wx.ID_ANY, "New Terminal")
        self.bt_run.Bind(wx.EVT_BUTTON, self.OnNewTerm)
        box_tool.Add(self.bt_run, 0, wx.LEFT | wx.RIGHT, 10)
        box_main.Add(box_tool, 0, wx.ALIGN_RIGHT | wx.ALL, 0)
        # Graph and Terminal side-by-side.
        box_gr_trm = wx.BoxSizer(wx.HORIZONTAL)
        # OpenGL FDP panel.
        self.glpanel = wx.Panel(self, 0)
        self.fdp_canvas = glsGraphCanvas.glsGraphCanvas(self.glpanel, pos=(0,0), size=(644,768))
        box_gr_trm.Add(self.glpanel, 1, wx.EXPAND | wx.ALL);
        # Terminal rendering.
        self.term_notebook = wx.Notebook(self)
        self.term_tabs = [ glsTerminalPanel(self.term_notebook, self.settings, self.OnCloseTerm) ]
        self.term_notebook.AddPage(self.term_tabs[0], "Terminal 1")
        box_gr_trm.Add(self.term_notebook, 1, wx.EXPAND | wx.ALL);
        box_main.Add(box_gr_trm, 0, wx.TOP | wx.BOTTOM, 0)
        self.term_monitor_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.MonitorTerminals, self.term_monitor_timer)
        self.term_monitor_timer.StartOnce()
        self.term_close_pending = []
        # Finalize UI layout.
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnNewTerm(self, event):
        # Create a new terminal and add the tab to the notebook.
        terminal = glsTerminalPanel(self.term_notebook, self.settings, self.OnCloseTerm)
        self.term_tabs.append(terminal)
        self.term_notebook.AddPage(terminal, "Terminal " + str(len(self.term_tabs)))
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
    def OnCloseTerm(self, terminal):
        # Add tab to closed terminal list.
        if terminal not in self.term_close_pending:
            self.term_close_pending.append(terminal)
        return
    def AddProject(self, proj):
        self.project = proj;
        if self.fdp_canvas is not None:
            self.fdp_canvas.AddProject(self.project)
        return
    def OnClose(self, event):
        for t in self.project.threads:
            t.stop()
            t.join()
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
