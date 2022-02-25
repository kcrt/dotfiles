#!/usr/bin/env julia


b1 = b"Hello\xDE\xAD\xBE\xEF"
print(typeof(b1))
# Base.CodeUnits{UInt8, String}
b2 = Vector{UInt8}(b1)	# Vectorに変換
