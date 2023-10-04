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
        glsEventManager.OpenDir = evt
        glsEventManager.EVT_OPEN_DIR = eid
        evt, eid = wx.lib.newevent.NewCommandEvent()
        glsEventManager.Search = evt
        glsEventManager.EVT_SEARCH = eid
        return

################################################################

glsEvents = glsEventManager()

################################################################
