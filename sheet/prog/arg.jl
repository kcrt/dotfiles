#!/usr/bin/env julia

# juliaの実行ファイルやソースコードは含まない [[注意]]
# julia ./arg.jl Hello => ["Hello"]
println(ARGS)

# ソースコードは
println(PROGRAM_FILE)

# 標準ではパースの方法はない
