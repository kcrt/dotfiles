#!/usr/bin/env python3

import json
from collections import OrderedDict

# object -> str
myobj = {"Hello": "World", "Good": ["Morning", "Afternoon"]}
json.dumps(myobj)
json.dumps(myobj, indent=4)

# str -> object
mystr = '{"b": 1, "a": 2}'
json.loads(mystr)
json.loads(mystr, object_pairs_hook=OrderedDict)  # 順番も保持

# read json file
with open("./sample.json") as fp:
    json.load(fp)
    # object_pairs_hook=OrderedDict

# write json file
with open("./sample_out.json", "w") as fp:
    json.dump(myobj, fp, indent=4)
