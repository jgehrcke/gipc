# -*- coding: utf-8 -*-
#
#   Copyright (C) 2012 Jan-Philip Gehrcke
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import logging
import gevent.os
from collections import deque

# Actually, on my system the JSON processor imported by "import json" is 
# faster than the one imported by "import simplejson". The latter has been
# installed via pip and compiled the C extension.
#try:
#    import simplejson as json
#except ImportError:
#    import json
#from collections import deque
import json

log = logging.getLogger()


class GPipeMessenger(object):
    def __init__(self):
        r, w = os.pipe()
        self._reader = _GPipeReader(r)
        self._writer = _GPipeWriter(w)
        
    def get(self):
        return self._reader.get()
        
    def put(self, m):
        self._writer.put(m)


class _GPipeReader(object):
    def __init__(self, pipe_read_end):
        self._r = pipe_read_end
        self.encoded_messages = deque()
        self.rest = ''
        self.read = gevent.os.read

    def get(self):
        while not self.encoded_messages:
            lines = (self.rest + self.read(self._r, 99999)).splitlines(True)
            self.rest = ''
            if not lines[-1].endswith('\n'):
                self.rest = lines.pop()
            self.encoded_messages.extend(lines)
        return json.loads(self.encoded_messages.popleft().decode("utf-8"))      
        
        
class _GPipeWriter(object):
    def __init__(self, pipe_write_end):
        self._w = pipe_write_end
        self.write = gevent.os.write

    def put(self, m):
        # JSON-encode message (among others escapes newlines)
        s = json.dumps(m, ensure_ascii=False).encode("utf-8")+'\n'
        while True:
            # Occasionally, not all bytes are written at once
            diff = len(s) - self.write(self._w, s)
            if not diff:
                break
            s = s[-diff:]


class GePipeReaderGenerator(object):
    def __init__(self, pipe_read_end):
        self._r = pipe_read_end

    def get_message(self):
        encoded_messages = None
        rest = ''
        while True:
            while not encoded_messages:
                lines = (rest + gevent.os.read(self._r, 99999)).splitlines(True)
                rest = ''
                if not lines[-1].endswith('\n'):
                    rest = lines.pop()
                encoded_messages = deque(lines)
            yield json.loads(encoded_messages.popleft().decode("utf-8")) 


if __name__ == "__main__":
    main()
