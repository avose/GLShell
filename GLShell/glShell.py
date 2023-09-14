#!/usr/bin/env python3
#
# GLShell - OpenGL-Enhanced Integrated Development Environment
# Copyright (C) 2023 Aaron D Vose
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307  USA
#
# Aaron D Vose
# avose@aaronvose.net
#
# Initially forked from:
# TermEmulator - Emulator for VT100 terminal programs
# Copyright (C) 2008 Siva Chandran P
#
# Siva Chandran P
# siva.chandran.p@gmail.com

from __future__ import print_function

import os
import sys
import wx
from threading import Thread

from glsTermsPanel import glsTermsPanel
from glsGraphPanel import glsGraphPanel
from glsToolBar import glsToolBar
import glsProject as glsp
import glsSettings
import glsHelp

VERSION = "0.0.3"

################################################################

class glShell(wx.Frame):
    ID_LICENSE = 1000
    def __init__(self, app, settings):
        self.settings = settings
        self.settings.AddWatcher(self.OnChangeSettings)
        self.app = app
        wx.Frame.__init__(self, None, wx.ID_ANY,
                          "GLShell - "+VERSION,
                          size = (1366, 768))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.InitUI()
        return
    def OnChangeSettings(self, settings):
        return
    def OnClose(self, event):
        self.settings.RemoveWatcher(self.OnChangeSettings)
        return
    def OnDestroy(self, event):
        self.settings.RemoveWatcher(self.OnChangeSettings)
        return
    def OnCharHook(self,event):
        event.DoAllowNextEvent()
        event.Skip()
        return
    def InitMenuBar(self):
        menubar = wx.MenuBar() 
        # File menu.
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
        # Edit menu.
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
        # Help menu.
        helpMenu = wx.Menu() 
        aboutItem = wx.MenuItem(helpMenu, wx.ID_ABOUT, text = "About", kind = wx.ITEM_NORMAL)
        helpMenu.Append(aboutItem)
        licenseItem = wx.MenuItem(helpMenu, self.ID_LICENSE, text = "License", kind = wx.ITEM_NORMAL)
        helpMenu.Append(licenseItem)
        menubar.Append(helpMenu, '&Help')
        # Connect menus to menu bar.
        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.MenuHandler)
        self.settings_frame = None
        self.about_frame = None
        self.license_frame = None
        return
    def MenuHandler(self, event):
        id = event.GetId() 
        if id == wx.ID_EXIT:
            self.OnClose(event)
            return
        if id == self.ID_SETTINGS:
            if self.settings_frame is None:
                self.settings_frame = glsSettings.SettingsFrame(self, self.settings)
                self.settings_frame.Show()
                self.settings_frame.Raise()
            else:
                self.settings_frame.Raise()
        elif id == wx.ID_ABOUT:
            if self.about_frame is None:
                self.about_frame = glsHelp.glsAboutFrame(self)
            else:
                self.about_frame.Raise()                
        elif id == self.ID_LICENSE:
            if self.license_frame is None:
                self.license_frame = glsHelp.glsLicenseFrame(self)
            else:
                self.license_frame.Raise()                
        return
    def InitUI(self):
        # Setup menu bar.
        self.InitMenuBar()
        # Main box.
        box_main = wx.BoxSizer(wx.VERTICAL)
        # Toolbar.
        self.toolbar = glsToolBar(self, self.settings)
        box_main.Add(self.toolbar, 0, wx.EXPAND)
        # Graph and Terminal side-by-side.
        self.min_term_size = (320, 92)
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(self.min_term_size[0])
        # OpenGL FDP panel.
        self.graph_panel = glsGraphPanel(self.splitter, self.settings, self.OnCloseGraph)
        # Terminals.
        self.terms_panel = glsTermsPanel(self.splitter, self.settings, self.min_term_size)
        # Finalize UI layout.
        box_main.Add(self.splitter, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 0)
        self.splitter.SplitVertically(self.graph_panel, self.terms_panel)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnCloseGraph(self, graph):
        return
    def AddProject(self, proj):
        self.project = proj;
        if self.graph_panel is not None:
            self.graph_panel.AddProject(self.project)
        return
    def OnSearchFiles(self, text):
        self.project.search_files(text)
        return
    def OnSearchContents(self, text):
        self.project.search_contents(text)
        return
    def OnClose(self, event):
        if self.settings_frame is not None:
            self.settings_frame.OnClose(event)
        if self.about_frame is not None:
            self.about_frame.OnClose(event)
        if self.license_frame is not None:
            self.license_frame.OnClose(event)
        for t in self.project.threads:
            t.stop()
            t.join()
        event.Skip()
        return

################################################################

if __name__ == '__main__':
    settings = glsSettings.glsSettings()
    settings.Load()
    proj_path = sys.argv[1] if len(sys.argv) == 2 else "."
    project = glsp.glsProject(settings, paths=[proj_path])
    app = wx.App(0);
    gl_shell = glShell(app, settings)
    app.SetTopWindow(gl_shell)
    gl_shell.AddProject(project)
    app.MainLoop()

################################################################
