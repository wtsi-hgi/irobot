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

import unittest
from configparser import ConfigParser

import irobot.config._tree_builder as tree_builder


class TestConfigurationTree(unittest.TestCase):
    def test_base_tree(self):
        tree = tree_builder._TreeNode()
        self.assertIsNone(tree.parent)
        self.assertEqual(tree.root, tree)

        child = tree_builder._TreeNode()
        self.assertIsNone(child.parent)
        tree._add_leaf("foo", child)
        self.assertEqual(child.parent, tree)
        self.assertEqual(child.root, tree)

        child._add_leaf("grandchild", tree_builder._TreeNode())
        self.assertEqual(tree.foo.grandchild.root, tree)

        self.assertTrue("foo" in tree)
        self.assertEqual([x for x in tree], ["foo"])

        self.assertEqual(tree.foo, child)
        self.assertRaises(AttributeError, getattr, tree, "bar")
        self.assertEqual(tree._leaves, getattr(tree, "_leaves"))

        self.assertRaises(KeyError, tree._add_leaf, "foo", tree_builder._TreeNode())

    def test_leaf_values(self):
        leaf = tree_builder.ConfigValue("abc", lambda x: x.upper())
        self.assertEqual(leaf(), "ABC")

    def test_branch_config(self):
        config = tree_builder.Configuration()
        sub_config = tree_builder.Configuration()
        value = tree_builder.ConfigValue("abc", lambda x: x.upper())

        sub_config.add_value("bar", value)
        config.add_config("foo", sub_config)

        self.assertEqual(config.foo.bar, "ABC")

    def test_config_factory(self):
        parser = ConfigParser()
        parser.read_string("""
            [test]
            foo = xyzzy
        """)

        keys = (
            tree_builder.RequiredKey("foo"),
            tree_builder.OptionalKey("bar", int, 123)
        )

        self.assertRaises(TypeError, tree_builder.config_factory, tree_builder.Configuration, parser, "test")

        config = tree_builder.config_factory(tree_builder.Configuration, parser, "test", *keys)
        self.assertEqual(config.foo, "xyzzy")
        self.assertEqual(config.bar, 123)


if __name__ == "__main__":
    unittest.main()
