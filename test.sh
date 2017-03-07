#!/usr/bin/env bash

set -eu -o pipefail

VENV=".venv"
REQUIREMENTS="requirements.txt"

xgrep() {
  # grep with its exit code quashed
  grep $@ || true
}

files_the_same() {
  local file1=$1
  local file2=$2
  local status=0

  set +e
  ! cmp -s "${file1}" "${file2}" && status=1
  set -e

  return ${status}
}

init_venv() {
  set +u
  [ -z "${VIRTUAL_ENV}" ] && source "${VENV}/bin/activate"
  set -u
}

start_venv() {
  if [ ! -e "${VENV}" ]; then
    python3.6 -m venv "${VENV}"
    init_venv
    pip install -r "${REQUIREMENTS}"
  else
    init_venv
  fi
}

update_packages() {
  if (( $(pip list -o | wc -l) )); then
    pip list -o --format=freeze \
    | xgrep -v '^-e' \
    | cut -d= -f1 \
    | xargs pip install -U
  fi
}

update_requirements() {
  local temp_requirements="$(mktemp)"

  join <(pip freeze | awk -F"==" '{print $1 " " $2}' | sort) \
       <(xgrep -v '^-e' "${REQUIREMENTS}" | cut -d= -f1 | sort) \
  | sed "s/ /==/" \
  > "${temp_requirements}"
  
  xgrep '^-e' "${REQUIREMENTS}" >> "${temp_requirements}"

  if ! files_the_same "${REQUIREMENTS}" "${temp_requirements}"; then
    cp "${temp_requirements}" "${REQUIREMENTS}"

    # Commit changes
    git stash
    git add "${REQUIREMENTS}"
    git commit -m "Automatically updated requirements after successful test run"
    git stash apply
  fi

  rm "${temp_requirements}"
}

clean_python_bytecode() {
  find irobot -type f \( -name "*.pyc" -o -name "*.pyo" \) -exec rm {} \+
}

main() {
  local to_test=()
  local updated=0

  start_venv
  clean_python_bytecode

  while (( $# )); do
    case "$1" in
      "-U")
        update_packages 
        updated=1
        ;;

      *)
        to_test+=("irobot.test.$1")
        ;;
    esac
    shift
  done

  clear
  nose2 -F -C --coverage-report=term-missing -v ${to_test[@]:-}

  # All tests passed with updated packages, so let's bump them
  [ -z "${to_test[@]:-}" ] && (( updated )) && update_requirements
}

main "$@"
