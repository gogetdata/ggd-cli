#!/bin/bash

cleanup() {
	rm -f ottt.sh
}

test -e ssshtest || wget -q https://raw.githubusercontent.com/ryanlayer/ssshtest/master/ssshtest
. ssshtest

echo "
ls -l > output
" > ottt.sh

trap cleanup EXIT


run from_bad_build python -m ggd from-bash --species Homo_sapiens --genome-build BAD --authors asdf \
	--version 1 --keyword xx --summary hello hello-script ottt.sh
assert_exit_code 1

run from_bad_species python -m ggd from-bash --species BAD --genome-build hg19 --authors asdf \
	--version 1 --keyword xx --summary hello hello-script ottt.sh
assert_exit_code 2


run from_good python -m ggd from-bash --species Homo_sapiens --genome-build hg19 --authors asdf \
	--version 1 --keyword xx --summary hello hello-script ottt.sh
assert_exit_code 0

run check_recipe python -m ggd check-recipe hg19-hello-script
assert_exit_code 130
assert_in_stderr "ERROR"
