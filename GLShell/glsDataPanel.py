import re
import mmap
import wx
import mimetypes
from threading import Thread, Lock
from multiprocessing import Process, Queue

from glsProject import glsFile
from glsGraphPanel import glsGraphPanel

################################################################

class glsSearchProcess(Process):
    def __init__(self, search, out_q):
        Process.__init__(self)
        self.search = search
        self.out_q = out_q
        self.done  = False
        return
    def run(self):
        for result in self.GetResults():
            if self.done:
                break
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
        line_num = 0
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
    def __init__(self, search, callback):
        Thread.__init__(self)
        self.search = search
        self.callback = callback
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
            self.callback(result)
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
        self.results = []
        self.result_files = {}
        return
    def AddResult(self, result):
        pndx, result = result
        nndx, path, line = result
        if line:
            lndx, line = line
        else:
            lndx = 0
        key = (pndx,nndx)
        if key not in self.result_files:
            self.result_files[key] = True
            self.results.append( (path,) )
        if line:
            self.results.append( (path, lndx, line) )
        return

################################################################

class glsSearchResultList(wx.VListBox):
    def __init__(self, parent, search):
        style = wx.LB_NEEDED_SB | wx.LB_MULTIPLE
        self.char_w,self.char_h = 10,10
        super(glsSearchResultList, self).__init__(parent, style=style)
        self.search = search
        self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        self.thread = glsSearchThread(search, self.OnSearchResult)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        self.SetBackgroundColour((0,0,0))
        self.char_w,self.char_h = dc.GetTextExtent("X")
        self.SetItemCount(1)
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
        result = self.search.results[index]
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
            self.DrawHeader(dc, rect)
            return
        path, rows_path, line, rows_line, lndx = self.ResultToStrings(index-1)
        # Draw background.
        if self.IsSelected(index):
            brush = wx.Brush((96,96,96))
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
        # Draw matching line.
        dc.SetTextForeground((128,255,128))
        dc.DrawText(line_raw, rect[0], rect[1])
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
    def OnSearchResult(self, result):
        self.SetItemCount(len(self.search.results) + 1)
        return
    def OnClose(self, event=None):
        self.thread.stop()
        self.thread.join()
        return

################################################################

class glsSearchResultPanel(wx.Window):
    def __init__(self, parent, search):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsSearchResultPanel, self).__init__(parent, style=style)
        self.search = search
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.vlb_results = glsSearchResultList(self, search)
        self.vlb_results.SetMinSize((200,200))
        box_main.Add(self.vlb_results, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return

################################################################

class glsDataPanel(wx.Window):
    def __init__(self, parent, settings):
        style = wx.SIMPLE_BORDER | wx.WANTS_CHARS
        super(glsDataPanel, self).__init__(parent, style=style)
        self.settings = settings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self)
        self.tabs = []
        box_main.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def AddProject(self, project):
        graph_panel = glsGraphPanel(self.notebook, project, self.settings)
        self.tabs.append(graph_panel)
        self.notebook.AddPage(graph_panel, "Graph '%s'"%(project.name))
        graph_panel.StartGraph()
        return
    def GetProjects(self):
        return [ tab for tab in self.tabs if isinstance(tab, glsGraphPanel) ]
    def AddSearch(self, search):
        result_panel = glsSearchResultPanel(self.notebook, search)
        self.tabs.append(result_panel)
        if search.search_type == search.TYPE_FILES:
            type_text = "Files"
        elif search.search_type == search.TYPE_CONTENTS:
            type_text = "Contents"
        self.notebook.AddPage(result_panel, "Search %s '%s'"%(type_text, search.text))
        self.notebook.SetSelection(len(self.tabs)-1)
        return
    def SearchFiles(self, text):
        self.AddSearch(glsSearch(self.GetProjects(), text, glsSearch.TYPE_FILES))
        return
    def SearchContents(self, text):
        self.AddSearch(glsSearch(self.GetProjects(), text, glsSearch.TYPE_CONTENTS))
        return
    def OnClose(self, event):
        for tab in self.tabs:
            if isinstance(tab, glsGraphPanel):
                tab.OnClose(event)
        event.Skip()
        return

################################################################
