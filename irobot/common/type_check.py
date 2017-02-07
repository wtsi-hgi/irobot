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

import inspect
from functools import wraps
from types import NoneType


if __debug__:
    from collections import Iterable, Mapping, namedtuple

    _ArgVals = namedtuple("ArgVals", ["args", "varargs", "keywords"])

    def type_check(var, *types):
        """
        Poor man's type checking

        @param   var     Variable to check
        @param   *types  Union of types to check against (types)
        """
        assert len(types) > 0, "Expecting at least one type to check against"
        if not any(isinstance(var, t) for t in types):
            raise TypeError("Expecting one of %s, not %s" % (types, type(var)))

    def type_check_collection(collection, *types):
        """
        Type checking for homogeneous collections

        @param   collection  Collection to check (iterable)
        @param   *types      Union of types to check against (types)
        """
        type_check(collection, Iterable)
        assert len(types) > 0, "Expecting at least one type to check against"

        if isinstance(collection, Mapping):
            collection = collection.values()

        for item in collection:
            type_check(item, *types)

    def type_check_arguments(**typespec):
        """
        Type checking decorator for function arguments

        @note    This decorator must be applied to the function first

        @param   *typespec  Mapping of function arguments to types
        """
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                # Map wrapper arguments to function signature
                argspec = inspect.getargspec(fn)
                posargs = len(argspec.args)
                argvals = _ArgVals(
                            args=(args[:posargs] + (argspec.defaults or ()))[:posargs],
                            varargs=args[posargs:],
                            keywords=kwargs
                          )

                # Type check positional arguments
                for i, arg in enumerate(argspec.args):
                    if arg in typespec:
                        type_check(argvals.args[i], typespec[arg])

                # Type check varargs
                if argspec.varargs and argspec.varargs in typespec:
                    type_check_collection(argvals.varargs, typespec[argspec.varargs])

                # Type check keywords
                if argspec.keywords and argspec.keywords in typespec:
                    type_check_collection(argvals.keywords, typespec[argspec.keywords])

                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def type_check_return(*types):
        """
        Type checking decorator for function return value

        @param   *types  Union of types to check against (types)
                         (Defaults to NoneType if none given)
        """
        expected = types or (NoneType,)

        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                output = fn(*args, **kwargs)

                checker = type_check_collection \
                          if isinstance(output, Iterable) \
                          else type_check

                checker(output, *expected)
                return output

            return wrapper

        return decorator


else:
    def type_check(*args, **kwargs):
        """ Pass-through """
        pass

    def type_check_collection(*args, **kwargs):
        """ Pass-through """
        pass

    def type_check_arguments(*args, **kwargs):
        """ Pass-through """
        return lambda fn: fn

    def type_check_return(*args, **kwargs):
        """ Pass-through """
        return lambda fn: fn
