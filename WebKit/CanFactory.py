
import os
import imp
import sys
import string

class CanFactory:
	"""Creates Cans on demand.  Looks only in the Cans directories.
	Unfortunately, this is a nasty hack, at least as far as directories are concerned.  The situation is that
	we want to be able to store Cans int he session object.  Session objects can be stored in files via pickling.
	When they are unpickled, the class module must be in sys.path.  The solution to this is custom importing,
	and apparently no one has time to get to that.
	So the current situation is that we continue to use a list of Can directories for Can creation, but we
	add that path to sys.path so that unpickling works correctly.
	"""
	def __init__(self, app):
		self._canClasses={}
		self._app = app
		self._canDirs = []
		for i in self._canDirs:
			if not i in sys.path:
				sys.path.append(i)

	def addCanDir(self, newdir):
		"""
		Add the specified directory to the search path for Cans.
		If the given directory is not an absolute path, it will be joined with the WebKit directory.
		"""
		if not os.path.isabs(newdir):
			newdir = self._app.serverSidePath(newdir)
		self._canDirs.append(newdir)
		sys.path.append(newdir)
		print "Help, I'm a HAAAACK! Find me in: ",  #jsl - fix before 0.5 release
		print __file__



	def createCan(self, canName, *args, **kwargs):
		##Looks in the directories specified in the application.canDirs List
		if self._canClasses.has_key(canName):
			klass = self._canClasses[canName]
		else:
			res = imp.find_module(canName, self._canDirs)
			mod = imp.load_module(canName, res[0], res[1], res[2])
			klass = mod.__dict__[canName]
			self._canClasses[canName]=klass				
		
		if len(args)==0 and len(kwargs)==0:
			instance = klass()
		elif len(args)==0:
			instance = apply(klass,kwargs)
		elif len(kwargs)==0:
			instance = apply(klass,args)
		else:
			instance = apply(klass,args,kwargs)
		return instance
	
