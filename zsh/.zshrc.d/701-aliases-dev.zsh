#
# 701-aliases-dev.zsh
#   Development tools and programming language aliases
#

# ============================================================================
# Git
# ============================================================================

abbrev-alias ssh-sign='ssh-keygen -Y sign -f ~/.ssh/kcrt-ssh-ed25519.pem -n file'

# ============================================================================
# Search Tools
# ============================================================================

alias ag='ag -S'
alias grep='grep --color=auto --binary-file=without-match --exclude-dir=.git --exclude-dir=.svn'

# ============================================================================
# Compilers
# ============================================================================

abbrev-alias clang++11='clang++ -O --std=c++11 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias clang++14='clang++ -O --std=c++14 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias clang++17='clang++ -O --std=c++17 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias clang++20='clang++ -O --std=c++20 -Wall --pedantic-errors --stdlib=libc++'

# ============================================================================
# Python
# ============================================================================

abbrev-alias pdb='env python -m pdb'
abbrev-alias oj_test_python='oj test -c "./main.py" -d tests'

# ============================================================================
# Text Processing
# ============================================================================

abbrev-alias textlintjp='textlint --preset preset-japanese --rule spellcheck-tech-word --rule joyo-kanji --rule @textlint-rule/textlint-rule-no-unmatched-pair'
abbrev-alias decryptpdf='gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=unencrypted.pdf -c 3000000 setvmthreshold -f'

# ============================================================================
# Misc Development Tools
# ============================================================================

abbrev-alias parallel='parallel --bar -j8'
abbrev-alias parakeet-mlx-en='uv tool run parakeet-mlx'
abbrev-alias parakeet-mlx-ja='uv tool run parakeet-mlx --model mlx-community/parakeet-tdt_ctc-0.6b-ja'
abbrev-alias ots='pipx run --spec opentimestamps-client ots'
