#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import defaultdict
import sys
import os
from subprocess import Popen, PIPE

if(len(sys.argv) != 2):
    sys.stderr.write("finddup.py path_to_find\n")
    sys.exit(1)
else:
    path = sys.argv[1]
    if(path[-1] == "/" and path != "/"):
        path = path[:-1]
sys.stderr.write("going to find '%s'...\n" % path)

n_file = 0
filelistbysize = defaultdict(list)
ignore_list = ['Backups.backupdb', 'MobileBackups', '.git']
for dpath, dnames, fnames in os.walk(path):
    if(any([dpath.find(x) != -1 for x in ignore_list])):
        # skip
        continue
    for filename in fnames:
        fullname = dpath + '/' + filename
        if(not os.path.isfile(fullname)):
            continue
        n_file += 1
        if(n_file % 1000 == 0):
            sys.stderr.write(".")
            sys.stderr.flush()
        if(n_file % 10000 == 0):
            sys.stderr.write(".%d [%s]\n" % (n_file, dpath))
        filesize = os.stat(fullname).st_size
        if(filesize <= 1024 * 1024 * 5):
            continue
        filelistbysize[filesize].append(fullname)

sys.stderr.write("\nFind the Same, in files larger than 5MiB\n")
for filesize, filelist in sorted(filelistbysize.items()):
    if(len(filelist) == 1):
        continue
    if(len(filelist) > 30):
        print(f"Skipping size {filesize}: too many files ({len(filelist)})")
        continue
    filelist_by_hash = defaultdict(list)
    for filename in filelist:
        filehash = Popen(["shasum", filename],
                         stdout=PIPE).stdout.read().rstrip(b"\n").decode()
        filehash = filehash.split(" ")[0]
        filelist_by_hash[filehash].append(filename)
    for xmd5, xfilelist in filelist_by_hash.items():
        if(len(xfilelist) != 1):
            sys.stderr.write(
                f"filesize {filesize}: {len(filelist)} same files.\n")
            print(u"{}MB".format(round(filesize / 1024 / 1024, 2)))
            for f in xfilelist:
                print(f"   {f}")
