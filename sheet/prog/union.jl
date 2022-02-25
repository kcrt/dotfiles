#!/usr/bin/env julia

IntOrStr = Union{Int, String}

local x::IntOrStr
x = 2
x = "Hello"

OptionalStr = Union{String, Nothing}
local y::OptionalStr = 
# julia helloworld.jl
