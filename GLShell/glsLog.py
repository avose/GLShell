from datetime import datetime

from glsSettings import glsSettings

################################################################

class glsLogManager():
    __log = None
    def __init__(self):
        if glsLogManager.__log is None:
            now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            glsLogManager.__log = [ (now, "Begin GLShell Log") ]
        return
    def add(self, text):
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        glsLogManager.__log.append( (now, text) )
        return
    def debug(self, text, level):
        if glsSettings.Get('log_level') >= level:
            self.add("(debug-#%d) %s"%(level, text))
        return
    def get(self, index=None):
        if index is not None:
            return glsLogManager.__log[index]
        return glsLogManager.__log.copy()
    def count(self):
        return len(glsLogManager.__log)

################################################################

glsLog = glsLogManager()

################################################################
