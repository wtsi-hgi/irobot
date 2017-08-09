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

from configparser import ConfigParser
from typing import Any, Callable, Dict, Iterable, NamedTuple, Optional


class _TreeNode(object):
    """ Generic tree node """
    _parent:Optional["_TreeNode"]
    _leaves:Dict[str, "_TreeNode"]

    def __init__(self, parent:Optional["_TreeNode"] = None) -> None:
        self._parent = parent
        self._leaves = {}

    def __contains__(self, name:str) -> bool:
        return name in self._leaves

    def __iter__(self) -> Iterable:
        return iter(self._leaves)

    def __getattr__(self, name:str) -> Any:
        if name in self._leaves:
            return self._leaves[name]

        if not hasattr(self, name):
            raise AttributeError(f"{self.__class__.__name__} has no {name} attribute")

        return getattr(self, name)

    @property
    def parent(self) -> Optional["_TreeNode"]:
        return self._parent

    @parent.setter
    def parent(self, node:"_TreeNode") -> None:
        self._parent = node

    @property
    def root(self) -> "_TreeNode":
        """ The root node (which may be itself) """
        parent = self.parent or self

        while parent:
            me = parent
            parent = me.parent

        return me

    def _add_leaf(self, name:str, leaf:"_TreeNode") -> None:
        """
        Add a leaf to the current node

        @param   name    Identity (string)
        @param   leaf    Leaf node (_TreeNode)
        """
        if name in self._leaves:
            raise KeyError(f"{name} already exists in configuration")

        leaf.parent = self
        self._leaves[name] = leaf


class ConfigValue(_TreeNode):
    """ Configuration values; i.e., genuine leaf nodes """
    _raw_value:str
    _transformer:Callable[[str], Any]

    def __init__(self, raw_value:Optional[str], transformer:Callable[[str], Any]) -> None:
        super().__init__()
        self._raw_value = raw_value
        self._transformer = transformer

    def __call__(self) -> Any:
        return self._transformer(self._raw_value)


class Configuration(_TreeNode):
    """ Configuration container """
    def __getattr__(self, name:str) -> Any:
        """ Return the transformed value, for any ConfigValue leaf """
        if name in self._leaves and isinstance(self._leaves[name], ConfigValue):
            return self._leaves[name]()

        return super().__getattr__(name)

    def add_config(self, name:str, config:"Configuration") -> None:
        """ Add subconfiguration """
        self._add_leaf(name, config)

    def add_value(self, name:str, value:ConfigValue) -> None:
        """ Add configuration value """
        self._add_leaf(name, value)


class _ConfigKey(NamedTuple):
    key:str
    transformer:Callable[[str], Any] = lambda x: x
    default:Any = None

class RequiredKey(_ConfigKey):
    """ Required configuration key mapping """
    pass

class OptionalKey(_ConfigKey):
    """ Optional configuration key mapping """
    pass


def config_factory(config:ConfigParser, section:str, *mappings) -> Configuration:
    """
    Build a configuration object from a section of a parsed file

    @param   config    Parsed configuration file (ConfigParser)
    @param   section   Section name (string)
    @param   mappings  Tuple of mappings (RequiredKey or OptionalKey)
    @return  Built configuration
    """
    if not mappings:
        raise TypeError("You must supply at least one mapping")

    built_config = Configuration()

    for mapping in mappings:
        key = mapping.key

        if isinstance(mapping, RequiredKey):
            value = config.get(section, key)

        if isinstance(mapping, OptionalKey):
            value = config.get(section, key, fallback=mapping.default)

        conf_value = ConfigValue(value, mapping.transformer)
        built_config.add_value(key, conf_value)

    return built_config
