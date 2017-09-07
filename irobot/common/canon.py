"""
Copyright (c) 2017 Genome Research Ltd.

Author: Christopher Harrison <ch12@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re
from datetime import timedelta
from typing import Optional


_RE_HUMAN_SIZE = re.compile(r"""
    ^(?:                                # Anchor to start of string
        (?:
            (?P<bytes> \d+ )            # One or more digits into "bytes" group
            (?: \s* B )?                # ...optionally followed by suffix
        )
        |                               # OR
        (?:
            (?P<quantity>
                \d+                     # Integer or floating point number
                (?: \. \d+ )?           # into "quantity" group
            )
            \s*
            (?P<multiplier>             # Into "multiplier" group:
                ki? |                   # * Kilo or kibibytes
                Mi? |                   # * Mega or mebibytes
                Gi? |                   # * Giga or gibibytes
                Ti?                     # * Tera or tibibytes
            )
            B
        )
    )$                                  # Anchor to end of string
""", re.VERBOSE)

_RE_DURATION = re.compile(r"""
    ^(?:
        (?P<value>
            \d+
            (?: \. \d+ )?
        )
        \s*
        (?P<unit>
            (?: s (ec (ond)? s?)? )     # s / sec(s) / second(s)
            |
            (?: m (in (ute)? s?)? )     # m / min(s) / minute(s)
        )
    )$
""", re.VERBOSE | re.IGNORECASE)

_RE_IPV4 = re.compile(r"""
    ^(?:
        (?P<dotted_dec>                 # e.g., 222.173.190.239
            \d{1,3}
            (?: \. \d{1,3} ){3}
        )
        |
        (?P<decimal>                    # e.g., 3735928559
            \d +
        )
        |
        (?P<hex>                        # e.g., 0xdeadbeef
            0x [0-9a-f]+
        )
        |
        (?P<dotted_hex>                 # e.g., 0xde.0xad.0xbe.0xef
            0x [0-9a-f]{2}
            (?: \. 0x [0-9a-f]{2} ){3}
        )
        |
        (?P<dotted_oct>                 # e.g., 0336.0255.0276.0357
            0 [0-7]{3}
            (?: \. 0 [0-7]{3} ){3}
        )
    )$
""", re.VERBOSE | re.IGNORECASE)

_RE_FQDN_COMPONENT = re.compile(r"""
    ^                                   # Anchor to start of string
    (?!-)                               # Can't start with a dash
    [a-z0-9-] {1,63}                    # 1-63 alphanumeric / dash characters
    (?<!-)                              # Can't end with a dash
    $                                   # Anchor to end of string
""", re.VERBOSE | re.IGNORECASE)

# Escapable characters (add more as required...)
_RE_ESCAPABLE = re.compile(r"([\x09\x20\x22])")


def path(p:str) -> str:
    """
    Canonicalise paths

    @param   p  Path (string)
    @return  Absolute, normalised path (string)
    """
    return os.path.abspath(
               os.path.normpath(
                   os.path.expanduser(p)))


def human_size(s:str) -> int:
    """
    Canonicalise human size string to integer bytes

    HUMAN_SIZE := INTEGER ["B"]
                | NUMBER ("k" | "M" | "G" | "T") ["i"] "B"

    @param   s  File size with optional suffix (string)
    @return  size in bytes (int)
    """
    match = _RE_HUMAN_SIZE.match(s)

    if not match:
        raise ValueError("Could not parse human size")

    if match.group('bytes'):
        # Whole number of bytes
        return int(match.group('bytes'))

    if match.group('quantity'):
        # Suffixed multiplier
        size = float(match.group('quantity'))
        multipliers = {
            'k': 1000,    'ki': 1024,
            'M': 1000**2, 'Mi': 1024**2,
            'G': 1000**3, 'Gi': 1024**3,
            'T': 1000**4, 'Ti': 1024**4
        }

        return int(size * multipliers[match.group('multiplier')])


def duration(d:str) -> Optional[timedelta]:
    """
    Canonicalise short temporal duration string  to timedelta

    DURATION := "never"
              | NUMERIC ( "s" | "sec" ["ond"] ["s"]
                        | "m" | "min" ["ute"] ["s"] )

    @param   d  Duration (string)
    @return  Parsed duration (timedelta); None for zero duration
    """
    if d.lower() == "never":
        return None

    match = _RE_DURATION.match(d)

    if not match:
        raise ValueError("Could not parse duration")

    unit = match["unit"].lower()[0]
    value = {{"m": "minutes", "s": "seconds"}[unit]: float(match["value"])}

    # n.b., Zero duration is the same as "never"
    return timedelta(**value) or None


def ipv4(ip:str) -> str:
    """
    Canonicalise IPv4 address to dotted decimal

    @param   ip  IPv4 address (string)
    @return  IPv4 bind address in dotted decimal (string)
    """
    match = _RE_IPV4.match(ip)

    if not match:
        raise ValueError("Invalid IPv4 address")

    # Dotted address
    if match["dotted_dec"] or match["dotted_hex"] or match["dotted_oct"]:
        parts = []

        address = match["dotted_dec"] or \
                  match["dotted_hex"] or \
                  match["dotted_oct"]

        base = 10 if match["dotted_dec"] else \
               16 if match["dotted_hex"] else \
                8

        for part in address.split("."):
            int_part = int(part, base)

            if not 0 <= int_part < 256:
                raise ValueError("Invalid IPv4 address")

            parts.append(int_part)

    # Plain address
    if match["decimal"] or match["hex"]:
        base = 10 if match["decimal"] else 16
        value = int(match["decimal"] or match["hex"], base)

        if not 0 <= value < 2**32:
            raise ValueError("IPv4 address out of range")

        parts = [
            (value & 0xff000000) >> 24,
            (value & 0xff0000) >> 16,
            (value & 0xff00) >> 8,
            value & 0xff
        ]

    return ".".join(str(part) for part in parts)


def domain_name(n:str) -> str:
    """
    Canonicalise a domain name to (almost) fully qualified (i.e.,
    omitting the root separator)

    @param   n  Domain name (string)
    @return  Fully qualified domain name (string)
    """
    if n.endswith("."):
        n = n[:-1]

    if all(_RE_FQDN_COMPONENT.match(component) for component in n.split(".")):
        return n.lower()

    raise ValueError("Invalid domain name")


def free_text(t:Optional[str]) -> str:
    """
    Canonicalise free text so special characters are escaped

    @param   t  Free text (string; optional)
    @return  Escaped text (string)
    """
    return _RE_ESCAPABLE.sub(r"\\\1", t or "")
