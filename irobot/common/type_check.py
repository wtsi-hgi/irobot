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

if __debug__:
    def type_check(var, *args):
        """
        Poor man's type checking

        @param   var    Variable to check
        @param   *args  Union of types to check against
        """
        assert len(args) > 0, "Expecting at least one type to check against"
        if not any(isinstance(var, t) for t in args):
            raise TypeError("Expecting one of %s, not %s" % (args, type(var)))

else:
    def type_check(*args, **kwargs):
        """ Pass-through """
        pass
