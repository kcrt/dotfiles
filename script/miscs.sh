#!/bin/bash

function if_error(){
	# usage: if_error "Cannot execute command"
	if [[ $? -ne 0 ]]; then
		echo_red $1
		exit
	fi
}

function need_app(){
	# usage: need_app "git"

	if [[ ! -x `which $1` ]]; then
		echo_red "'$1' not found!"
		exit
	else
		echo_green "'$1' found."
	fi

}

# usage:
# bench-start
# (heavy work)
# bench-checkpoint "heavy work done"
# (another heavy work)
# bench-end

BENCH_START=0
BENCH_CHECKPOINTSTART=0
function current-milliseconds() {
	if [ "$(uname)" = "Darwin" ]; then
		gdate +%s%3N
	els
		date +%s%3N
	fi
}
function bench-start(){
	echo "--- Benchmark start ---"
	BENCH_START=`current-milliseconds`
	BENCH_CHECKPOINTSTART=BENCH_START
}
function bench-checkpoint(){
	BENCH_END=`current-milliseconds`
	BENCH_DIFF=$(( $BENCH_END - $BENCH_CHECKPOINTSTART ))
	echo "--- Check point $1: $BENCH_DIFF [msec.] ---"
	BENCH_CHECKPOINTSTART=`current-milliseconds`
}
function bench-end(){
	BENCH_END=`current-milliseconds`
	BENCH_DIFF=$(( $BENCH_END - $BENCH_START ))
	echo "--- Benchmark finished: $BENCH_DIFF [msec.] ---"
}
