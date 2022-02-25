#!/usr/bin/env julia

# int -> smaller int
300 % Int8	# => 44
# Int8(300)	# InexactErrror

# str -> int

# int, float -> str

# str -> float

# float -> int
Int(132.0)	# => 132
# Int(132.6)	# => InexactError
round(Int, 132.6)	# => 133 (Int型)
# float, ceil, trunc

# int -> float

# int -> hex string

# float -> hex string

# hex string -> int

# hex string -> float

# int -> bin string

# bin string -> int
