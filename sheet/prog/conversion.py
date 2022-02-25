#!/usr/bin/env python3

# str -> int
int("132")      # => 132

# int, float -> str
str(132)        # => "132"
str(132.5)      # => "132.5"

# str -> float
float("132.5")  # 132.5

# float -> int
int(132.5)      # => 132
132.5 // 1      # => 132.0 (float)

# int -> float
float(132)      # => 132.0
132 * 1.0       # => 132.0

# int -> hex string
hex(1024)       # => 0x400

# float -> hex string
3.5.hex()       # => '0x1.c000000000000p+1'

# hex string -> int
int("400", 16)      # => 1024
int("0x400", 16)    # 0xはつけてもつけなくても良い

# hex string -> float
float.fromhex("0x11.11")    # => 17.06640625

# int -> bin string
bin(1024)                   # => '0b10000000000'

# bin string -> int
int("10000000000", 2)       # => 1024
int("0b10000000000", 2)     # => 1024 (0bはなくても大丈夫)
