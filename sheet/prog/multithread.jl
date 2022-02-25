#!/usr/bin/env julia

function producer(c::Channel)
	put!(c, "begin")
	for n in 1:5
		put!(c, 2n)
	end
	put!(c, "end")
end

# Channelコンストラクタ
# 引数がChannel型1つの関数から、その関数のタスクと接続したチャネルを生成する
chnl = Channel(producer)

# put!をtake!で受ける
println(take!(chnl))  # => begin
println(take!(chnl))  # => 2
println(take!(chnl))  # => 4
println(take!(chnl))  # => 6

for x in Channel(producer)
	println(x)
end


# TODO: Task (@task, istaskdone, istaskstarted, state)

