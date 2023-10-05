import wx
import wx.lib.newevent

################################################################

class glsEventManager():
    initialized = False
    def __init__(self):
        if glsEventManager.initialized:
            return
        glsEventManager.initialized = True
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.ChildExit = evt
        glsEventManager.EVT_CHILD_EXIT = eid
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.OpenDir = evt
        glsEventManager.EVT_OPEN_DIR = eid
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.Search = evt
        glsEventManager.EVT_SEARCH = eid
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.TabClose = evt
        glsEventManager.EVT_TAB_CLOSE = eid
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.TabTitle = evt
        glsEventManager.EVT_TAB_TITLE = eid
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.TabCurrent = evt
        glsEventManager.EVT_TAB_CURRENT = eid
        return

################################################################

glsEvents = glsEventManager()

################################################################
