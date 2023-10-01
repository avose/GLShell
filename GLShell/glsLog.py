from datetime import datetime

################################################################

class glsLogger():
    def __init__(self):
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        self.log = [ (now, "Begin GLShell Log") ]
        return
    def add(self, text):
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        self.log.append( (now, text) )
        return
    def get(self, index=None):
        if index is not None:
            return self.log[index]
        return self.log
    def count(self):
        return len(self.log)

################################################################

glsLog = glsLogger()

################################################################
