#!/usr/bin/env python3

def checks(s):
    print(s + " is " + ("true" if eval(s) else "false"))

checks("0")
checks("1")
checks("0.0")
checks("1.0")
checks("float('nan')")
checks("float('inf')")
checks("'0'")
checks("'1'")
checks("'A'")
checks("''")
checks("'true'")
checks("'false'")
checks("[]")
checks("{}")
checks("()")
checks("None")

# python3 helloworld.py または ./helloworld.py で実行
