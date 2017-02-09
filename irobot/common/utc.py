"""
Copyright (c) 1990-2017 Python Software Foundation

UTC timezone instance, copied on 2017-02-09 from:
https://docs.python.org/2/library/datetime.html#tzinfo-objects
"""

from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)

class UTC(tzinfo):
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()
