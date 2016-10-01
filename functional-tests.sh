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
assert_exit_code 2
assert_in_stderr "ERROR"

###test search
run bad_search_no_args python -m ggd search 
assert_exit_code 2

run bad_search_invalid_recipe python -m ggd search "BAD"
assert_exit_code 1

run good_search_simple python -m ggd search "hg19*"
assert_exit_code 0
assert_in_stdout "hg19-repeatmasker"

run bad_search_invalid_build python -m ggd search "hg19*" -g "BAD"
assert_exit_code 1

run bad_search_invalid_species python -m ggd search "hg19*" -s "BAD"
assert_exit_code 2

run good_search python -m ggd search "hg19-*" -s "Homo_sapiens" -g "hg19" 
assert_exit_code 0
assert_in_stdout "hg19-repeatmasker"

###test list-files (depends on the hg19-hello-script)
run bad_list_no_args python -m ggd list_files
assert_exit_code 2

run bad_list_invalid_recipe python -m ggd list-files "BAD"
assert_exit_code 1
assert_in_stderr "No matching files found"

run good_list_simple python -m ggd list-files "hg19*"
assert_exit_code 0
assert_in_stdout "output"
assert_in_stdout "hg19-hello-script"

run bad_list_invalid_build python -m ggd list-files "hg19*" -g "BAD"
assert_exit_code 1

run bad_list_invalid_species python -m ggd list-files "hg19*" -s "BAD"
assert_exit_code 2

run bad_list_invalid_pattern python -m ggd list-files "hg19*" -p "BAD"
assert_exit_code 1

run good_list python -m ggd list-files "hg19*" -s "Homo_sapiens" -g "hg19" 
assert_exit_code 0
assert_in_stdout "output"
assert_in_stdout "hg19-hello-script"


run good_list python -m ggd show-env 
assert_exit_code 0
assert_in_stdout "ggd_hg19_hello_script"

#have to find the current conda env name to test show-env
conda_info=$(conda info --envs)
while IFS=$'\n' read -ra conda_info; do
    for line in "${conda_info[@]}"; do
        if grep -q "*" <<<$line; then
            IFS=' ' read -r -a parsed_stuff <<< "$line"
            env_name="${parsed_stuff[0]}"
        fi
    done
done <<< "$conda_info"

source activate "$env_name"
run good_env_var ls "$ggd_hg19_hello_script"
assert_exit_code 0
assert_in_stdout "output"

source deactivate "$env_name"
run ls "$ggd_hg19_hello_script"
assert_exit_code 127
