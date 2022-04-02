#!/bin/sh
set -e
compiler=$1
${compiler} -march=native "-###" -E - < /dev/null 2>&1 | sed -ne 's/.*cc1 .*-march=\([^ "]*\)[ "].*/\1/p'
