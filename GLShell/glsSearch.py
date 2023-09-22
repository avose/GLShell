import re
import mmap
import wx
import mimetypes
from threading import Thread, Lock
from multiprocessing import Process, Queue, Event

from glsProject import glsFile
from glsIcons import glsIcons

################################################################

class glsSearchProcess(Process):
    def __init__(self, search, out_q):
        Process.__init__(self)
        self.search = search
        self.out_q = out_q
        self.event = Event()
        return
    def run(self):
        for result in self.GetResults():
            if self.event.is_set():
                return
            self.out_q.put(result)
        self.out_q.put(None)
        return
    def stop(self):
        self.event.set()
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
                    if (node.name.endswith("~") or
                        mimetype is not None and mimetype.startswith("text/")):
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
    def GetResults(self):
        return self.results
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
        item.SetBitmap(self.icons.Get('zoom_out'))
        self.Append(item)
        return

################################################################

class glsSearchResultList(wx.VListBox):
    def __init__(self, parent, search, callback_resultopen, callback_close):
        style = wx.LB_NEEDED_SB
        self.char_w,self.char_h = 10,10
        self.search = search
        self.proc = None
        super(glsSearchResultList, self).__init__(parent, style=style)
        self.callback_close = callback_close
        self.callback_resultopen = callback_resultopen
        self.fontinfo = wx.FontInfo(11).FaceName("Monospace")
        self.font = wx.Font(self.fontinfo)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnMenuItem)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        dc = wx.MemoryDC()
        dc.SetFont(self.font)
        self.SetBackgroundColour((0,0,0))
        self.char_w,self.char_h = dc.GetTextExtent("X")
        self.SetItemCount(1)
        self.in_q = Queue()
        self.proc = glsSearchProcess(self.search, self.in_q)
        self.proc.start()
        self.closing = False
        self.result_poll_done = False
        wx.CallLater(10, self.PollResults)
        return
    def LineWrapText(self, initial_text):
        if initial_text is None or len(initial_text) == 0:
            return ("", 0)
        max_len = max(1, int(self.Size[0]/self.char_w)-2)
        nlines = 1
        text = ""
        initial_text = initial_text.replace("\t","    ")
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
        if self.proc is not None:
            text = "(active) " + text
        else:
            text = "(finished) " + text
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
    def ProcessResults(self, results):
        if results is None or len(results) == 0:
            return
        for result in results:
            self.search.AddResult(result)
        self.SetItemCount(len(self.search.GetResults()) + 1)
        self.Refresh()
        wx.YieldIfNeeded()
        return
    def PollResults(self):
        if self.closing:
            self.result_poll_done = True
            return
        results = []
        try:
            while True:
                result = self.in_q.get()
                if result is None:
                    if self.proc is not None:
                        self.proc.join()
                        self.proc = None
                    break
                results.append(result)
        except Empty:
            pass
        self.ProcessResults(results)
        if self.proc is None:
            self.result_poll_done = True
            self.Refresh()
            wx.YieldIfNeeded()
            return
        wx.CallLater(150, self.PollResults)
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
        if self.proc:
            self.proc.stop()
            self.proc.join()
            self.proc = None
        if not self.result_poll_done:
            wx.CallLater(10, self.OnClose)
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
    def OnClose(self, event=None):
        if self.vlb_results:
            self.vlb_results.OnClose()
        self.vlb_results = None
        return
    def OnDestroy(self, event):
        self.OnClose()
        return

################################################################
