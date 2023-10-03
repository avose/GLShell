import os
import re
import wx
import mmap
import mimetypes
from time import sleep
from queue import Empty, Full
from threading import Thread, Lock
from multiprocessing import Process, Queue, Event

from glsDirTree import glsFile
from glsIcons import glsIcons
from glsLog import glsLog

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
            while True:
                if self.event.is_set():
                    self.out_q.put(None)
                    return
                try:
                    self.out_q.put_nowait(result)
                    break
                except Full:
                    sleep(0.01)
        self.out_q.put(None)
        return
    def stop(self):
        self.event.set()
        return
    def GetResults(self):
        for dtndx,dirtree in enumerate(self.search.dirtrees):
            for result in self.SearchDirTree(dirtree):
                yield (dtndx, result)
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
    def SearchContents(self, node):
        if not isinstance(node, glsFile):
            return (False, None)
        mimetype = mimetypes.guess_type(node.abspath)[0]
        try:
            with open(node.abspath, 'rb', 0) as f:
                contents = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                if (node.name.endswith("~") or
                    mimetype is not None and mimetype.startswith("text/")):
                    for index, line in self.LinesOf(contents):
                        if self.search.MatchContent(line):
                            yield (True, (index, line))
                else:
                    if self.search.MatchContent(contents, True):
                        yield (True, None)
        except:
            return (False, None)
        return
    def SearchDirTree(self, dirtree):
        nodes = dirtree.GetNodes()
        if not self.search.has_cont:
            for nndx,node in enumerate(nodes):
                if (self.search.MatchName(node.name) and
                    self.search.MatchType(node.abspath)):
                    yield (nndx, node.abspath, None)
            return
        for nndx,node in enumerate(nodes):
            if (self.search.MatchName(node.name) and
                self.search.MatchType(node.abspath)):
                for match, line_info in self.SearchContents(node):
                    if match:
                        yield (nndx, node.abspath, line_info)
        return

################################################################

class glsMatch():
    def __init__(self, start, end):
        self.ndx_start = int(start)
        self.ndx_end = int(end)
        return
    def start(self):
        return self.ndx_start
    def end(self):
        return self.ndx_end

################################################################

class glsSearch():
    def __init__(self, dirtrees, name_text, name_regx=False,
                 cont_text=None, cont_regx=False,
                 files=False, dirs=False):
        self.dirtrees = dirtrees
        self.name_text = name_text
        self.name_regx = name_regx
        self.cont_text = cont_text
        self.cont_regx = cont_regx
        self.incl_dirs = dirs
        self.incl_files = files
        if self.name_text is None or self.name_text == "":
            self.has_name = False
            if self.name_regx:
                self.name_text = '.*'
        else:
            self.has_name = True
        if self.cont_text is None or self.cont_text == "":
            self.has_cont = False
        else:
            self.has_cont = True
            self.cont_text_bytes = bytes(self.cont_text,"utf-8")
        self.results = []
        self.result_files = {}
        return
    def MatchType(self, path):
        if not self.incl_dirs and os.path.isdir(path):
            return False
        if not self.incl_files and os.path.isfile(path):
            return False
        return True
    def MatchName(self, name):
        if not self.has_name:
            return True
        if self.name_regx:
            return re.search(self.name_text, name)
        return name.find(self.name_text) != -1
    def MatchContent(self, content, isbytes=False):
        if not self.has_cont:
            return True
        stext = self.cont_text_bytes if isbytes else self.cont_text
        if self.cont_regx:
            return re.search(stext, content)
        return content.find(stext) != -1
    def IndexName(self, name):
        if not self.has_name:
            return None
        if self.name_regx:
            return re.search(self.name_text, name)
        start = name.find(self.name_text)
        if start == -1:
            return None
        end = start + len(self.name_text)
        return glsMatch(start, end)
    def IndexContent(self, content):
        if not self.has_cont:
            return None
        if self.cont_regx:
            return re.search(self.cont_text, content)
        start = content.find(self.cont_text)
        if start == -1:
            return None
        end = start + len(self.cont_text)
        return glsMatch(start, end)
    def AddResult(self, result):
        dtndx, result = result
        nndx, path, line = result
        if line:
            lndx, line = line
        else:
            lndx = 0
        key = (dtndx,nndx)
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
    def __init__(self, parent, open_available):
        super(glsSearchResultListPopupMenu, self).__init__()
        item = wx.MenuItem(self, self.ID_OPEN_NEW, 'Open (New Tab)')
        item.SetBitmap(glsIcons.Get('monitor_add'))
        self.Append(item)
        if not open_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_OPEN, 'Open (Current Tab)')
        item.SetBitmap(glsIcons.Get('monitor'))
        self.Append(item)
        if not open_available:
            item.Enable(False)
        item = wx.MenuItem(self, self.ID_EXIT, 'Close')
        item.SetBitmap(glsIcons.Get('magnifier_zoom_out'))
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
        glsLog.add("Search Start: name=('%s',%s) text=('%s',%s)"%
                   (self.search.name_text,
                    "regex" if self.search.name_regx else "str",
                    self.search.cont_text,
                    "regex" if self.search.cont_regx else "str"))
        self.proc.start()
        self.closing = False
        self.result_poll_done = False
        wx.CallLater(10, self.PollResults)
        return
    def ExtractMatchingText(self, line, match_func):
        line = line.replace("\n","")
        line_len = len(line)
        new_line = ""
        matches = ""
        match = match_func(line)
        while match:
            for i in range(0, match.start()):
                matches += " "
            matches += line[match.start():match.end()]
            new_line += line[:match.start()]
            for i in range(match.start(), match.end()):
                new_line += " "
            line = line[match.end():]
            match = match_func(line)
        for i in range(0, len(line)):
            matches += " "
        new_line += line
        matches, rows_matches = self.LineWrapText(matches)
        new_line, rows_line = self.LineWrapText(new_line)
        return new_line, matches
    def LineWrapText(self, initial_text, isline=False):
        if initial_text is None or len(initial_text) == 0:
            return ("", 0)
        max_len = max(1, int(self.Size[0]/self.char_w)-2)
        nlines = 1
        text = ""
        initial_text = initial_text.replace("\t","    ")
        while len(initial_text) > max_len:
            text += initial_text[0:max_len] + '\n'
            if isline:
                initial_text = "        " + initial_text[max_len:]
            else:
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
        line, rows_line = self.LineWrapText("        " + line, True)
        return "", 0, line, rows_line, ("%d: "%(lndx)).ljust(8)
    def HeaderToString(self):
        if self.proc is not None:
            text = "Searching:"
        else:
            text = "Searched:"
        if self.search.name_text:
            text += " name='%s'%s"%(self.search.name_text,
                                    ' (regex)' if self.search.name_regx else '')
        if self.search.cont_text:
            text += " contents='%s'%s"%(self.search.cont_text,
                                        ' (regex)' if self.search.cont_regx else '')
        return self.LineWrapText(text)
    def MeasureHeader(self):
        text, rows = self.HeaderToString()
        return (rows+1) * self.char_h
    def DrawHeader(self, dc, rect):
        brush = wx.Brush((0,0,0))
        dc.SetBrush(brush)
        dc.SetPen(wx.Pen((0,150,150)))
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        header, rows = self.HeaderToString()
        if self.search.has_name:
            def match_name_query(text):
                start = text.find(self.search.name_text)
                if start == -1:
                    return None
                end = start + len(self.search.name_text)
                return glsMatch(start, end)
            header, matches = self.ExtractMatchingText(header, match_name_query)
            dc.SetTextForeground((255,175,125))
            dc.DrawText(matches, rect[0], rect[1])
        if self.search.has_cont:
            def match_cont_query(text):
                start = text.find(self.search.cont_text)
                if start == -1:
                    return None
                end = start + len(self.search.cont_text)
                return glsMatch(start, end)
            header, matches = self.ExtractMatchingText(header, match_cont_query)
            dc.SetTextForeground((0,255,0))
            dc.DrawText(matches, rect[0], rect[1])
        dc.SetTextForeground((0,255,255))
        dc.DrawText(header, rect[0], rect[1])
        dc.SetTextForeground((0,255,255))
        dc.DrawText("Results:  %d"%len(self.search.GetResults()),
                    rect[0], rect[1] + self.char_h*rows)
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
        if path:
            dc.SetPen(wx.Pen((75,75,75)))
            dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
            # Draw path.
            if not self.search.has_name:
                dc.SetTextForeground((255,255,255))
                dc.DrawText(path, rect[0], rect[1])
            else:
                line, matches = self.ExtractMatchingText(path, self.search.IndexName)
                dc.SetTextForeground((255,255,255))
                dc.DrawText(line, rect[0], rect[1])
                dc.SetTextForeground((255,175,125))
                dc.DrawText(matches, rect[0], rect[1])
            return
        dc.SetPen(wx.Pen((0,0,75)))
        dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])
        # Draw line number.
        dc.SetTextForeground((255,255,0))
        dc.DrawText(lndx, rect[0], rect[1])
        dc.SetPen(wx.Pen((150,150,0)))
        dc.DrawLine(rect[0] + int(7.5*self.char_w), rect[1],
                    rect[0] + int(7.5*self.char_w), rect[1]+rect[3])
        # Draw matching line with highlight.
        line, matches = self.ExtractMatchingText(line, self.search.IndexContent)
        dc.SetTextForeground((128,192,128))
        dc.DrawText(line, rect[0], rect[1])
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
    def OnRightDown(self, event):
        popup = glsSearchResultListPopupMenu(self, (self.GetSelection() != wx.NOT_FOUND and
                                                    self.GetSelection() != 0))
        self.PopupMenu(popup, event.GetPosition())
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
                result = self.in_q.get_nowait()
                if result is None:
                    if self.proc is not None:
                        self.proc.join()
                        self.proc = None
                    break
                results.append(result)
                if len(results) >= 10000:
                    break
                if not len(results)%1000:
                    wx.YieldIfNeeded()
                if self.closing:
                    self.result_poll_done = True
                    return
        except Empty:
            pass
        self.ProcessResults(results)
        if self.proc is None:
            self.result_poll_done = True
            self.Refresh()
            log = "Search Done:"
            log += " name=('%s',%s)"%(self.search.name_text,
                                      "regex" if self.search.name_regx else "str")
            log += " text=('%s',%s)"%(self.search.cont_text,
                                      "regex" if self.search.cont_regx else "str")
            log += " " + str(len(self.search.GetResults())) + " results\n"
            log += "\n".join([dt.abspath for dt in self.search.dirtrees])
            glsLog.add(log)
            wx.YieldIfNeeded()
            return
        wx.CallLater(150, self.PollResults)
        return
    def OnClose(self, event=None):
        self.closing = True
        if self.proc:
            # !!avose: Printouts confirm the child process exiting,
            # !!avose: but there are still issues with joining.
            self.proc.stop()
            self.proc.join(timeout=0.1)
            if self.proc.is_alive():
                self.proc.terminate()
            self.proc.join(timeout=0.1)
            if self.proc.is_alive():
                self.proc.kill()
            self.proc.join()
            self.proc = None
        if not self.result_poll_done:
            wx.CallLater(10, self.OnClose)
            if event is not None:
                event.Veto()
            return
        self.callback_close()
        return
    def OnDestroy(self, event):
        self.OnClose()
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
