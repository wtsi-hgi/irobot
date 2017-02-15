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

import re


def parse_human_size(size:str) -> int:
    """
    Parse human size string := INTEGER ["B"]
                             | NUMBER ("k" | "M" | "G" | "T") ["i"] "B"

    @param   size  File size with optional suffix (string)
    @return  size in bytes (int)
    """
    match = re.match(r"""
        ^(?:                       # Anchor to start of string
            (?:
                (?P<bytes> \d+ )   # One or more digits into "bytes" group
                (?: \s* B )?       # ...optionally followed by suffix
            )
            |                      # OR
            (?:
                (?P<quantity>
                    \d+            # Integer or floating point number
                    (?: \. \d+ )?  # into "quantity" group
                )
                \s*
                (?P<multiplier>    # Into "multiplier" group:
                    ki? |          # * Kilo or kibibytes
                    Mi? |          # * Mega or mebibytes
                    Gi? |          # * Giga or gibibytes
                    Ti?            # * Tera or tibibytes
                )
                B
            )
        )$                         # Anchor to end of string
    """, size, re.VERBOSE)

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
