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

    def type_check(var, *types):
        """
        Poor man's type checking

        @param   var     Variable to check
        @param   *types  Union of types to check against (types)
        """
        assert len(types) > 0, "Expecting at least one type to check against"
        if not any(isinstance(var, t) for t in types):
            raise TypeError("Expecting type of %s, not %s" % (types, type(var)))

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
                # Note that positional values can be provided via
                # keyword values, so we have to extract them first
                argspec = inspect.getargspec(fn)

                pos_values = []
                kw_veto = []
                arg_p = 0
                def_p = 0
                for arg in argspec.args:
                    if arg in kwargs:
                        pos_values.append(kwargs[arg])
                        kw_veto.append(arg)

                    else:
                        if arg_p < len(args):
                            pos_values.append(args[arg_p])
                            arg_p += 1

                            if len(args) - arg_p > len(argspec.defaults or ()):
                                def_p += 1

                        else:
                            pos_values.append(argspec.defaults[def_p])
                            def_p += 1

                assert len(pos_values) == len(argspec.args), "Error mapping values to function signature"

                var_values = args[len(argspec.args):]
                kw_values = {k:v for k, v in kwargs.items() if k not in kw_veto}

                # Type check positional arguments
                for i, arg in enumerate(argspec.args):
                    if arg in typespec:
                        type_check(pos_values[i], typespec[arg])

                # Type check varargs
                if argspec.varargs and argspec.varargs in typespec:
                    type_check_collection(var_values, typespec[argspec.varargs])

                # Type check keywords
                if argspec.keywords and argspec.keywords in typespec:
                    type_check_collection(kw_values, typespec[argspec.keywords])

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
