import re
import mmap
import wx
import mimetypes
from time import sleep
from threading import Thread, Lock
from multiprocessing import Process, Queue

from glsProject import glsFile
from glsGraphPanel import glsGraphPanel
from glsIcons import glsIcons

################################################################

class glsSearchProcess(Process):
    def __init__(self, search, out_q):
        Process.__init__(self)
        self.search = search
        self.out_q = out_q
        return
    def run(self):
        for result in self.GetResults():
            self.out_q.put(result)
        self.out_q.put(None)
        return
    def GetResults(self):
        if self.search.search_type == self.search.TYPE_FILES:
            for pndx,project in enumerate(self.search.projects):
                for result in self.SearchFiles(project):
                    yield (pndx, result)
        elif self.search.search_type == self.search.TYPE_CONTENTS:
            for pndx,project in enumerate(self.search.projects):
                for result in self.SearchContents(project):
                    yield (pndx, result)
        return
    def SearchFiles(self, project):
        if self.search.text is None or self.search.text == "":
            return
        stext = self.search.text
        for nndx,node in enumerate(project.project.root.graph.nlist):
            if re.search(stext, node.name):
                yield (nndx, node.abspath, None)
        return
    def LinesOf(self, contents):
        newline = bytes('\n', "utf-8")
        start = 0
        end = contents.find(newline, start)
        line_num = 1
        while end != -1:
            line = contents[start:end]
            yield line_num, line.decode("utf-8")
            line_num += 1
            start = end + 1
            end = contents.find(newline, start)
        if len(contents)-start > 0:
            line = contents[start:]
            yield line_num, line.decode("utf-8")
        return
    def SearchContents(self, project):
        if self.search.text is None or self.search.text == "":
            return
        stext = self.search.text
        for nndx,node in enumerate(project.project.root.graph.nlist):
            if not isinstance(node, glsFile):
                continue
            mimetype = mimetypes.guess_type(node.abspath)[0]
            try:
                with open(node.abspath, 'rb', 0) as f:
                    contents = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                    if mimetype is not None and mimetype.startswith("text/"):
                        for index, line in self.LinesOf(contents):
                            if re.search(stext, line):
                                yield (nndx, node.abspath, (index,line))
                    else:
                        if re.search(bytes(stext,"utf-8"), contents):
                            yield (nndx, node.abspath, None)
            except:
                continue
        return

################################################################

class glsSearchThread(Thread):
    def __init__(self, search, callback_result):
        Thread.__init__(self)
        self.search = search
        self.callback_result = callback_result
        self.in_q = Queue()
        self.done = False
        self.proc = glsSearchProcess(self.search, self.in_q)
        self.proc.start()
        self.start()
        return
    def run(self):
        while not self.done:
            result = self.in_q.get()
            if result is None:
                self.done = True
                break
            self.search.AddResult(result)
            self.callback_result()
        self.proc.join()
        return
    def stop(self):
        self.done = True
        return

################################################################

class glsSearch():
    TYPE_FILES = 1
    TYPE_CONTENTS = 2
    def __init__(self, projects, text, search_type):
        self.projects = projects
        self.text = text
        self.search_type = search_type
        self.lock = Lock()
        self.__results = []
        self.__result_files = {}
        return
    def AddResult(self, result):
        pndx, result = result
        nndx, path, line = result
        if line:
            lndx, line = line
        else:
            lndx = 0
        key = (pndx,nndx)
        with self.lock:
            if key not in self.__result_files:
                self.__result_files[key] = True
                self.__results.append( (path,) )
            if line:
                self.__results.append( (path, lndx, line) )
        return
    def GetResults(self):
        with self.lock:
            return self.__results.copy()
        return

################################################################

class glsSearchResultListPopupMenu(wx.Menu):
    ID_OPEN_NEW = 1000
    ID_OPEN     = 1001
    ID_EXIT     = 1002
    def __init__(self, parent):
        super(glsSearchResultListPopupMenu, self).__init__()
        self.icons = glsIcons()
        item = wx.MenuItem(self, self.ID_OPEN_NEW, 'Open (New Tab)')
        item.SetBitmap(self.icons.Get('monitor_add'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_OPEN, 'Open (Current Tab)')
        item.SetBitmap(self.icons.Get('monitor'))
        self.Append(item)
        item = wx.MenuItem(self, self.ID_EXIT, 'Close')
        item.SetBitmap(self.icons.Get('cross'))
        self.Append(item)
        return

################################################################

class glsSearchResultList(wx.VListBox):
    def __init__(self, parent, search, callback_resultopen, callback_close):
        style = wx.LB_NEEDED_SB
        self.char_w,self.char_h = 10,10
        super(glsSearchResultList, self).__init__(parent, style=style)
        self.callback_close = callback_close
        self.callback_resultopen = callback_resultopen
        self.search = search
        self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        self.thread = glsSearchThread(search, self.OnSearchResult)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnMenuItem)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        self.SetBackgroundColour((0,0,0))
        self.char_w,self.char_h = dc.GetTextExtent("X")
        self.SetItemCount(1)
        self.result_count = 1
        self.closing = False
        self.watcher_done = False
        wx.CallLater(5, self.ResultWatcher)
        return
    def LineWrapText(self, initial_text):
        if initial_text is None or len(initial_text) == 0:
            return ("", 0)
        max_len = max(1, int(self.Size[0]/self.char_w)-2)
        nlines = 1
        text = ""
        while len(initial_text) > max_len:
            text += initial_text[0:max_len] + '\n'
            initial_text = initial_text[max_len:]
            nlines += 1
        text += initial_text
        return (text, nlines)
    def ResultToStrings(self, index):
        result = self.search.GetResults()[index]
        if len(result) == 1:
            path, rows_path = self.LineWrapText(result[0])
            return path, rows_path, "", 0, ""
        path, lndx, line = result
        line, rows_line = self.LineWrapText("        " + line)
        return "", 0, line, rows_line, ("%d: "%(lndx)).ljust(8)
    def HeaderToString(self):
        if self.search.search_type == self.search.TYPE_FILES:
            type_text = "files"
        elif self.search.search_type == self.search.TYPE_CONTENTS:
            type_text = "file contents"
        text = 'Searching %s for: "%s"'%(type_text, self.search.text)
        return self.LineWrapText(text)
    def MeasureHeader(self):
        text, rows = self.HeaderToString()
        return rows * self.char_h
    def DrawHeader(self, dc, rect):
        text, rows = self.HeaderToString()
        dc.SetTextForeground((255,255,0))
        dc.DrawText(text, rect[0], rect[1])
        return
    def OnMeasureItem(self, index):
        if index == 0:
            return self.MeasureHeader()
        path, rows_path, line, rows_line, lndx = self.ResultToStrings(index-1)
        return (rows_path + rows_line) * self.char_h
    def OnDrawItem(self, dc, rect, index):
        dc.Clear()
        dc.SetFont(self.font)
        if not index:
            # Draw header.
            self.DrawHeader(dc, rect)
            return
        path, rows_path, line, rows_line, lndx = self.ResultToStrings(index-1)
        # Draw background.
        if self.IsSelected(index):
            brush = wx.Brush((64,0,64))
        else:
            brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.SetPen(wx.Pen((0,0,0)))
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        if path:
            # Draw path.
            dc.SetTextForeground((255,255,255))
            dc.DrawText(path, rect[0], rect[1])
            return
        # Draw line number.
        dc.SetTextForeground((255,255,0))
        dc.DrawText(lndx, rect[0], rect[1])
        # Extract matching text and remaining text.
        line = line.replace("\n","")
        line_len = len(line)
        new_line = ""
        matches = ""
        match = re.search(self.search.text, line)
        while match:
            for i in range(0, match.start()):
                matches += " "
            matches += line[match.start():match.end()]
            new_line += line[:match.start()]
            for i in range(match.start(), match.end()):
                new_line += " "
            line = line[match.end():]
            match = re.search(self.search.text, line)
        for i in range(0, len(line)):
            matches += " "
        new_line += line
        matches, rows_matches = self.LineWrapText("        "+matches)
        new_line, rows_line = self.LineWrapText("        "+new_line)
        # Draw remaining text.
        dc.SetTextForeground((128,192,128))
        dc.DrawText(new_line, rect[0], rect[1])
        # Draw matching text.
        dc.SetTextForeground((0,255,0))
        dc.DrawText(matches, rect[0], rect[1])
        return
    def OnDrawBackground(self, dc, rect, index):
        dc.Clear()
        pen = wx.Pen((0,0,255))
        dc.SetPen(pen)
        brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        return
    def OnDrawSeparator(self, dc, rect, index):
        return
    def ResultWatcher(self):
        if self.closing:
            self.watcher_done = True
            return
        self.SetItemCount(self.result_count)
        self.Refresh()
        wx.CallLater(50, self.ResultWatcher)
        return
    def OnSearchResult(self):
        self.result_count = len(self.search.GetResults()) + 1
        return
    def OnRightDown(self, event):
        self.PopupMenu(glsSearchResultListPopupMenu(self), event.GetPosition())
        return
    def OnMenuItem(self, event):
        item_id = event.GetId() 
        if item_id == glsSearchResultListPopupMenu.ID_EXIT:
            self.OnClose()
        elif (item_id == glsSearchResultListPopupMenu.ID_OPEN or
              item_id == glsSearchResultListPopupMenu.ID_OPEN_NEW ):
            result = self.GetSelection()
            if result == wx.NOT_FOUND or result == 0:
                return
            result -= 1
            if not result < len(self.search.GetResults()) or not result >= 0:
                return
            result = self.search.GetResults()[result]
            path = result[0]
            if len(result) > 1:
                lndx = result[1]
            else:
                lndx = None
            self.callback_resultopen(item_id, path, lndx)
        return
    def OnClose(self, event=None):
        self.closing = True
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
        if not self.watcher_done:
            wx.CallLater(5, self.OnClose)
            if event is not None:
                event.Veto()
        self.callback_close()
        return

################################################################

class glsSearchResultPanel(wx.Window):
    def __init__(self, parent, search, callback_resultopen, callback_close):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsSearchResultPanel, self).__init__(parent, style=style)
        self.search = search
        self.callback_close = callback_close
        self.callback_resultopen = callback_resultopen
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.vlb_results = glsSearchResultList(self, search, self.callback_resultopen,
                                               self.OnSearchClose)
        self.vlb_results.SetMinSize((200,200))
        box_main.Add(self.vlb_results, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnSearchClose(self):
        self.callback_close(self)
        return
    def OnClose(self, event):
        if self.vlb_results:
            self.vlb_results.OnClose(event)
        self.vlb_results = None
        return
    def OnDestroy(self, event):
        self.OnClose(event)
        return

################################################################

class glsDataPanel(wx.Window):
    def __init__(self, parent, settings, terms_panel):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsDataPanel, self).__init__(parent, style=style)
        self.settings = settings
        self.terms_panel = terms_panel
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.icons = glsIcons()
        self.image_list = wx.ImageList(16, 16)
        self.image_list.Add(self.icons.Get('chart_organisation'))
        self.image_list.Add(self.icons.Get('magnifier'))
        self.notebook = wx.Notebook(self)
        self.notebook.SetImageList(self.image_list)
        self.tabs = []
        self.tabs_closing = []
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def AddProject(self, project):
        graph_panel = glsGraphPanel(self.notebook, project, self.settings)
        self.tabs.append(graph_panel)
        self.notebook.AddPage(graph_panel, " Graph '%s'"%(project.name))
        self.notebook.SetPageImage(len(self.tabs)-1, 0)
        graph_panel.StartGraph()
        return
    def GetProjects(self):
        return [ tab for tab in self.tabs if isinstance(tab, glsGraphPanel) ]
    def AddSearch(self, search):
        result_panel = glsSearchResultPanel(self.notebook, search, self.OnResultOpen,
                                            self.OnCloseTab)
        self.tabs.append(result_panel)
        if search.search_type == search.TYPE_FILES:
            type_text = "Files"
        elif search.search_type == search.TYPE_CONTENTS:
            type_text = "Contents"
        self.notebook.AddPage(result_panel, " Search %s '%s'"%(type_text, search.text))
        self.notebook.SetSelection(len(self.tabs)-1)
        self.notebook.SetPageImage(len(self.tabs)-1, 1)
        return
    def SearchFiles(self, text):
        self.AddSearch(glsSearch(self.GetProjects(), text, glsSearch.TYPE_FILES))
        return
    def SearchContents(self, text):
        self.AddSearch(glsSearch(self.GetProjects(), text, glsSearch.TYPE_CONTENTS))
        return
    def OnResultOpen(self, action_id, path, line=None):
        if action_id == glsSearchResultListPopupMenu.ID_OPEN_NEW:
            self.terms_panel.EditorStart(path)
            if line is not None:
                self.terms_panel.EditorLineSet(line)
        if action_id == glsSearchResultListPopupMenu.ID_OPEN:
            self.terms_panel.EditorFileOpen(path)
            if line is not None:
                self.terms_panel.EditorLineSet(line)
        return
    def CloseTabs(self):
        for closing in self.tabs_closing:
            for i,t in enumerate(self.tabs):
                if t == closing:
                    self.notebook.DeletePage(i)
                    self.notebook.SendSizeEvent()
                    self.tabs.remove(closing)
                    self.tabs_closing.remove(closing)
        return
    def OnCloseTab(self, tab):
        if tab not in self.tabs_closing:
            self.tabs_closing.append(tab)
        wx.CallLater(10, self.CloseTabs)
        return
    def OnClose(self, event):
        for tab in self.tabs:
            tab.OnClose(event)
        event.Skip()
        return

################################################################
