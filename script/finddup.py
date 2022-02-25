#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import md5
from subprocess import Popen, PIPE

if(len(sys.argv) != 2):
	sys.stderr.write("finddup.py path_to_find\n")
	sys.exit(1)
else:
	path = sys.argv[1]
	if(path[-1] == "/" and path != "/"):
		path[-1] = [];
sys.stderr.write("going to find '%s'...\n" % path)

cfile = 0
filelistbysize = {}
for dpath, dnames, fnames in os.walk(path):
	if(dpath.find('Backups.backupdb') != -1):
		continue
	if(dpath.find('MobileBackups') != -1):
		continue
	if(dpath.find('.git') != -1):
		continue
	for filename in fnames:
		fullname = dpath + '/' + filename
		if(not os.path.isfile(fullname)):
			continue
		cfile += 1
		if(cfile % 1000 == 0):
			sys.stderr.write(".")
		if(cfile % 10000 == 0):
			sys.stderr.write(".%d [%s]\n" % (cfile, dpath))
		filesize = os.stat(fullname).st_size
		if(filesize <= 1024 * 1024 * 5):
			continue
		if(not filelistbysize.has_key(filesize)):
			filelistbysize[filesize] = [];
		filelistbysize[filesize].append(fullname);

sys.stderr.write("Find the Same, in larger than 5MB files\n")
for filesize,filelist in sorted(filelistbysize.iteritems()):
	if(len(filelist) == 1):
		continue
	filelistbymd5 = {}
	for filename in filelist:
		md5 = Popen(["shasum", filename], stdout=PIPE).stdout.read().rstrip("\n")
                md5 = md5.split(" ")[0]
		if(not filelistbymd5.has_key(md5)):
			filelistbymd5[md5] = [];
		filelistbymd5[md5].append(filename);
	for xmd5, xfilelist in filelistbymd5.iteritems():
		if(len(xfilelist) != 1):
                        sys.stderr.write("filesize %d: %d same size files.\n" % (filesize, len(filelist)))
			print u"{}MB".format(round(filesize / 1024 / 1024,2))
			for f in xfilelist:
				print "  ",
				print f
