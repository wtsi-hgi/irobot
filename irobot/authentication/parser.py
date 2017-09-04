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
from typing import Callable, Dict, Iterator, List, Mapping, Optional, Tuple
from typing.re import Pattern

# Authentication Grammar
# per RFC7235: https://tools.ietf.org/html/rfc7235#section-2.1
#
#   AUTH_HANDLERS := AUTH_HANDLER *( OWS "," OWS AUTH_HANDLER )
#   AUTH_HANDLER  := TOKEN [ OWS ( TOKEN68 / PARAMS ) ]
#   PARAMS        := PARAM ( OWS "," OWS PARAM )*
#   PARAM         := TOKEN OWS "=" OWS ( TOKEN / QUOTED_STRING )
#   TOKEN         := 1*( ALPHA / DIGIT / "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~" )
#   TOKEN68       := 1*( ALPHA / DIGIT / "-" / "_" / "~" / "+" / "/" ) *"="
#   QUOTED_STRING := QUOTE *( TEXT / ESCAPED ) QUOTE
#   TEXT          := %x09 / %x20-21 / %x23-5B / %x5D-7E / %x80-FF
#   ESCAPED       := "\" ( %x09 / %x20-7E / %x80-FF )
#   QUOTE         := %x22
#   ALPHA         := %x41-5A / %x61-7A
#   DIGIT         := %x30-39
#   OWS           := *( %x09 / %x20 )


class ParseError(Exception):
    """ Raised on parsing error """


_ParseT = Tuple[str, str]
_Parser = Callable[[str], _ParseT]

def _make_terminal(pattern:Pattern) -> _Parser:
    """
    Make a terminal grammar node parser

    @param   pattern  Pattern to match
    @return  Parser that matches pattern
    """
    def _parser(s:str) -> _ParseT:
        match = pattern.match(s)

        if not match:
            raise ParseError()

        index = match.end()
        return s[:index], s[index:]

    return _parser

def _make_alternation(*parsers:_Parser) -> _Parser:
    """
    Make an alternation parser from parsers

    @param   parsers  Parsers to match (at least one)
    @return  Parser that matches alternation
    """
    assert parsers

    def _parser(s:str) -> _ParseT:
        for parser in parsers:
            try:
                return parser(s)
            except ParseError:
                pass

        raise ParseError()

    return _parser

def _make_sequence(parser:_Parser, minimum:int = 0, maximum:Optional[int] = None) -> _Parser:
    """
    Make a sequence parser from parsers

    @note    _make_sequence(parser, maximum=1) makes an optional parser

    @param   parser   Parser to match
    @param   minimum  Minimum number of matches
    @param   maximum  Maximum number of matches (optional)
    @return  Parser that matches sequence
    """
    if maximum:
        assert maximum >= minimum

    def _parser(s:str) -> _ParseT:
        matched     = ""
        remainder   = s
        num_matched = 0

        while True:
            try:
                match, remainder = parser(remainder)
                matched += match
                num_matched += 1

                if (not remainder) or (maximum and num_matched == maximum):
                    break

            except ParseError:
                if num_matched < minimum:
                    raise

                break

        return matched, remainder

    return _parser

def _make_juxtaposition(*parsers:_Parser) -> _Parser:
    """
    Make a juxtaposition parser from parsers

    @param   parsers  Parsers to match (at least one)
    @return  Parser that matches juxtaposition
    """
    assert parsers

    def _parser(s:str) -> _ParseT:
        matched   = ""
        remainder = s

        for parser in parsers:
            try:
                match, remainder = parser(remainder)
                matched += match

            except ParseError:
                raise

        return matched, remainder

    return _parser


_OWS     = _make_terminal(re.compile(r"[\t ]*"))
_DIGIT   = _make_terminal(re.compile(r"[0-9]"))
_ALPHA   = _make_terminal(re.compile(r"[a-zA-Z]"))
_QUOTE   = _make_terminal(re.compile(r"\""))
_EQUALS  = _make_terminal(re.compile(r"="))
_ESCAPED = _make_terminal(re.compile(r"\\[\x09\x20-\x7e\x80-\xff]"))
_TEXT    = _make_terminal(re.compile(r"[\x09\x20\x21\x23-\x5b\x5d-\x7e\x80-\xff]"))

_QUOTED_STRING = _make_juxtaposition(
    _QUOTE,
    _make_sequence(_make_alternation(_TEXT, _ESCAPED)),
    _QUOTE
)

_TOKEN = _make_sequence(
    _make_alternation(
        _ALPHA,
        _DIGIT,
        _make_terminal(re.compile(r"[!#$%&'*+.^_`|~-]"))
    ),
    minimum=1
)

_TOKEN68 = _make_juxtaposition(
    _make_sequence(
        _make_alternation(
            _ALPHA,
            _DIGIT,
            _make_terminal(re.compile(r"[-_~+/]"))
        ),
        minimum=1
    ),
    _make_sequence(_EQUALS)
)

_LIST_SEPARATOR = _make_juxtaposition(
    _OWS,
    _make_terminal(re.compile(r",")),
    _OWS
)


_PARAM_SEPARATOR = _make_juxtaposition(_OWS, _EQUALS, _OWS)
_PARAM_VALUE = _make_alternation(_TOKEN, _QUOTED_STRING)

def _param(s:str) -> Tuple[str, str, str]:
    """
    Key-Value parameter parser

    @param   s  Input string
    @return  Tuple of parameter key, parameter value and remaining string
    """
    param_key,   remainder = _TOKEN(s)
    _equals,     remainder = _PARAM_SEPARATOR(remainder)
    param_value, remainder = _PARAM_VALUE(remainder)

    return param_key, param_value, remainder

def _params(s:str) -> Tuple[Dict[str, str], str]:
    """
    Parameter group parser

    @param   s  Input string
    @return  Dictionary of parameters and remaining string
    """
    parameters:Dict[str, str] = {}

    param_key, param_value, remainder = _param(s)
    parameters[param_key] = param_value

    if remainder:
        while True:
            try:
                _comma, remainder = _LIST_SEPARATOR(remainder)
            except ParseError:
                break

            param_key, param_value, remainder = _param(remainder)
            parameters[param_key] = param_value

            if not remainder:
                break

    return parameters, remainder


class AuthHandler(Mapping[str, str]):
    """ Authentication handler model """
    _method:str
    _payload:str
    _params:Dict[str, str]

    def __init__(self, auth_method:str, *, payload:Optional[str] = None, params:Optional[Dict[str, str]] = None) -> None:
        """
        Constructor

        @note    payload and params should be mutually exclusive

        @param   auth_method  Authentication method (string)
        @param   payload      Payload (string)
        @param   params       Parameters (dictionary)
        """
        assert not (payload and params)

        self._method  = auth_method
        self._payload = payload
        self._params  = params or {}

    def __repr__(self) -> str:
        output = f"<{self._method}"

        if self._payload:
            output += f" {self._payload}"
        else:
            for k, v in self._params.items():
                output += f" {k}={v}"

        return f"{output}>"

    def __getitem__(self, param:str) -> str:
        return self._params[param]

    def __iter__(self) -> Iterator[str]:
        return iter(self._params)

    def __len__(self) -> int:
        return len(self._params)

    @property
    def auth_method(self) -> str:
        return self._method

    @property
    def payload(self) -> str:
        return self._payload

def _auth_handler(s:str) -> Tuple[AuthHandler, str]:
    """
    Authentication handler parser

    @param   s
    @return  Tuple of authentication handler and remaining string
    """
    auth_method, remainder = _TOKEN(s)

    try:
        _, remainder = _OWS(remainder)

        try:
            params, remainder = _params(remainder)
            return AuthHandler(auth_method, params=params), remainder

        except ParseError:
            payload, remainder = _TOKEN68(remainder)
            return AuthHandler(auth_method, payload=payload), remainder

    except ParseError:
        return AuthHandler(auth_method), remainder

def auth_parser(auth_header:str) -> List[AuthHandler]:
    """
    Authentication header parser

    @param   auth_header   Authentication header (string)
    @return  List of authentication handlers
    """
    auth_handlers:List[AuthHandler] = []

    handler, remainder = _auth_handler(auth_header)
    auth_handlers.append(handler)

    while remainder:
        _, remainder = _LIST_SEPARATOR(remainder)
        handler, remainder = _auth_handler(remainder)
        auth_handlers.append(handler)

    return auth_handlers
