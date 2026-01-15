#
#	.zshrc
#		Main entry point for modular zsh configuration
#		Written by kcrt <kcrt@kcrt.net>
#				Nanoseconds Hunter "http://www.kcrt.net"
#
#  To edit .zshrc and .zshrc.d files, please check and reuse functions in 000-common.zsh
#
#	参考:
#		http://nijino.homelinux.net/diary/200206.shtml#200206140
#		http://d.hatena.ne.jp/umezo/20100508/1273332857
#		http://www.clear-code.com/blog/2011/9/5.html
#		https://github.com/zplug/zplug/blob/master/doc/guide/ja/README.md
#

ZSHRC_DIR="${ZSHRC_DIR:-${ZDOTDIR:-$HOME}/.zshrc.d}"

# Benchmarking infrastructure
# To check loading time, run `bench-zsh`
if [[ -n "$BENCHMARK_ZSHRC" ]]; then
	function date_in_ms(){
		if [[ "$OSTYPE" = darwin* ]] && command -v udate >/dev/null 2>&1; then
			udate +%s%3N
		elif [[ "$OSTYPE" = darwin* ]]; then
			date +%s000
		else
			date +%s%3N
		fi
	}
	start=$(date_in_ms)
	function end_of(){
		now=$(date_in_ms)
		# show elapsed time in ms with color (aqua)
		echo -e "\e[36m$1 done: $((now - start)) ms\e[m"
		start=${now}
	}
else
	function end_of(){
		:	# do nothing
	}
	alias bench-zsh='time BENCHMARK_ZSHRC=1 zsh -i -c exit'
fi

# Source all .zsh modules in alphabetical order
if [[ -d "${ZSHRC_DIR}" ]]; then
	for config in "${ZSHRC_DIR}"/*.zsh(N); do
		source "${config}"
		# Call end_of with the filename for benchmarking
		end_of "${config:t}"
	done
fi
