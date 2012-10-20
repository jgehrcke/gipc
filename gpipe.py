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
try:
    import simplejson as json
except ImportError:
    import json

log = logging.getLogger()

def pipe(raw=False):
    r, w = os.pipe()
    return _GPipeReader(r, raw), _GPipeWriter(w, raw)


class _GPipeReader(object):
    def __init__(self, pipe_read_end, raw=False):
        self._r = pipe_read_end
        self.messages = deque()
        self.residual = ''
        self.raw = raw

    def close(self):
        os.close(self._r)

    def get(self):
        while not self.messages:
            # TODO: Research reasonable buffer size
            lines = (self.residual +
                gevent.os.read(self._r, 99999)).splitlines(True)
            self.residual = ''
            if not lines[-1].endswith('\n'):
                self.residual = lines.pop()
            self.messages.extend(lines)
        if self.raw:
            return self.messages.popleft()
        # Each encoded msg has trailing \n. Could be removed with rstrip().
        # However, it looks like the JSON decoder ignores it.
        return json.loads(self.messages.popleft())


class _GPipeWriter(object):
    def __init__(self, pipe_write_end, raw=False):
        self._w = pipe_write_end
        self.raw = raw    

    def close(self):
        os.close(self._w)

    def put(self, m):
        if not self.raw:
            # JSON-encode message. Among others: escapes newlines, returns
            # bytestring
            m = json.dumps(m)+'\n'
        # else: user has to insert msg delimiter, i.e. newline character
        while True:
            # Occasionally, not all bytes are written at once
            diff = len(m) - gevent.os.write(self._w, m)
            if not diff:
                break
            m = m[-diff:]


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
