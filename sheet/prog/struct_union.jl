#!/usr/bin/env julia

struct Person
	name::String
	age::Int
	address::String
end

kcrt = Person("Kyohei", 34, "Sagamihara")
kcrt.age	# => 34
# kcrt.age = 12	# Error! structはimmutable

fieldnames(Person)	# =>  (:name, :age, :address)

println(kcrt) # => Person("Kyohei", 34, "Sagamihara")
Base.show(io::IO, p::Person) = print(io, "I am ", p.name, ".")
println(kcrt) # => I am Kyohei.


mutable struct Person2
	name::String
	age::Int
	address::String
end

tom = Person2("Thomas Alva Edison", 84, "US")
tom.age = 0		# OK


# Union
IntOrStr = Union{Int, String}

local x::IntOrStr
x = 2
x = "Hello"

# Optional
OptionalStr = Union{String, Nothing}
local y::OptionalStr
y = "Hello"
y = nothing


# Template
struct Point{T}
	x::T
	y::T
end

p = Point{Float32}(2.0, 3.0)
q = Point(1, 2)
typeof(q)	# => Point{Int64}
r = Point("Hello", "world")	# this seems very strange...

# 数値に限定
struct Point2{T <: Number}
	x::T
	y::T
end

# 関数テンプレート
function distance(x::T, y::T) where {T}
	if T <: Number
		sqrt(x^2 + y^2)
	else
		"$x to $y"
	end
end
distance(3, 4)	# => 5.0
distance("Japan", "US")	# => Japan to US
