'''
TestCommon.py

This is just a convenience module for the various test modules (TestFoo.py).
'''


import os, string, sys, time


from FixPath import *

try:
	import MiddleKit
except ImportError:
	FixPathForMiddleKit()
	import MiddleKit

try:
	import MiscUtils
except ImportError:
	FixPathForMiscUtils()
	import MiscUtils


from MiddleKit.Core.Klasses import Klasses
