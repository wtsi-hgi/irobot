#!/usr/bin/gawk -f

# TODO and FIXME reporter for Python source files
# -----------------------------------------------
# MIT License
# Copyright (c) 2017 Genome Research Ltd.
# Author: Christopher Harrison <ch12@sanger.ac.uk>

function print_todo() {
  print "\033[0;34m" FILENAME ": Line " line "\033[0m"
  print gensub(/^((TODO|FIXME)\??)/, "\033[0;31m\\1\033[0m", 1, gensub(/^\s*#? ?/, "", 1, gensub(/\n\s*#? ?/, " ", "g", todo)))
  print ""
}

BEGIN {
  in_todo = 0
  in_docstring = 0

  line = 0
  todo = ""
}

/^\s*"""/ {
  if (gsub(/"""/, "\"\"\"") == 2) {
    # Single-line docstring (assume it doesn't contain a TODO)
    in_docstring = 0
  } else {
    in_docstring = 1 - in_docstring
  }
}

/^\s*(# )?(TODO|FIXME)/ {
  # Multiple, single line TODOs
  if (in_todo) print_todo()

  in_todo = 1
  todo = ""
  line = NR
}

in_todo {
  prefix = (todo == "") ? "" : todo "\n"

  if ($0 ~ /^\s*("""|#)?\s*$/ || $0 ~ /^\s*(\w|@)/) {
    in_todo = 0
    if (in_docstring) todo = prefix $0
    print_todo()
  } else {
    todo = prefix $0
  }
}

END {
  # End of file TODO
  if (in_todo) print_todo()
}
