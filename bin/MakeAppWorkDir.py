#!/usr/bin/env python
#----------------------------------------------------------------------
#
# A script to build a WebKit work directory outside of the WebWare tree
#
# By Robin Dunn
#
#----------------------------------------------------------------------

"""
MakeAppWorkDir.py


INTRODUCTION

This utility builds a directory tree that can be used as the current
working directory of an instance of the WebKit applicaiton server.  By
using a separate directory tree like this your applicaion can run
without needing write access, etc. to the WebWare directory tree, and
you can also run more than one application server at once using the
same WebWare code.  This makes it easy to reuse and keep WebWare
updated without disturbing your applicaitons.


COMMAND LINE USAGE

	python MakeAppWorkDir.py SomeDir

"""

#----------------------------------------------------------------------

import sys, os, string
import glob, shutil

#----------------------------------------------------------------------

class MakeAppWorkDir:
	"""Make a new application runtime directory for Webware.

	This class breaks down the steps needed to create a new runtime
	directory for webware.  That includes all the needed
	subdirectories, default configuration files, and startup scripts.
	Each step can be overridden in a derived class if needed.
	"""

	def __init__(self, webWareDir, workDir, verbose=1, sampleContext="MyContext"):
		"""Initializer for MakeAppWorkDir.  Pass in at least the
		Webware directory and the target working directory.  If you
		pass None for sampleContext then the default context will the
		the WebKit/Examples directory as usual.
		"""
		self._webWareDir = webWareDir
		self._webKitDir = os.path.join(webWareDir, "WebKit")
		self._workDir = os.path.abspath(workDir)
		self._verbose = verbose
		self._substVals = {
		    "WEBWARE": string.replace(self._webWareDir, '\\', '/'),
		    "WEBKIT":  string.replace(self._webKitDir,	'\\', '/'),
		    "WORKDIR": string.replace(self._workDir,	'\\', '/'),
		    "DEFAULT": "%s/Examples" % string.replace(self._webKitDir,	'\\', '/'),
		    }
		self._sample = sampleContext
		if sampleContext is not None:
			self._substVals["DEFAULT"] = sampleContext


	def buildWorkDir(self):
		"""These are all the (overridable) steps needed to make a new runtime direcotry."""
		self.makeDirectories()
		self.copyConfigFiles()
		self.copyOtherFiles()
		self.makeLauncherScripts()
		self.makeDefaultContext()
		self.printCompleted()



	def makeDirectories(self):
		"""Creates all the needed directories if they don't already exist."""
		self.msg("Creating directory tree at %s" % self._workDir)

		theDirs = [ self._workDir,
			    os.path.join(self._workDir, "Cache"),
			    os.path.join(self._workDir, "Cans"),  # TODO: should this one be here?
			    os.path.join(self._workDir, "Configs"),
			    os.path.join(self._workDir, "ErrorMsgs"),
			    os.path.join(self._workDir, "Logs"),
			    os.path.join(self._workDir, "Sessions"),
			    ]

		for aDir in theDirs:
			if os.path.exists(aDir):
				self.msg("\t%s already exists." % aDir)
			else:
				os.mkdir(aDir)
				self.msg("\t%s created." % aDir)

		# Copy the contents of the Cans directory from WebKit/Cans
		for name in glob.glob(os.path.join(self._webKitDir, "Cans", "*.py")):
			newname = os.path.join(self._workDir, "Cans", os.path.basename(name))
			shutil.copyfile(name, newname)

		self.msg("\n")


	def copyConfigFiles(self):
		"""
		Make a copy of the config files in the Configs directory.
		"""
		configs = glob.glob(os.path.join(self._webKitDir, "Configs", "*.config"))
		for name in configs:
			newname = os.path.join(self._workDir, "Configs", os.path.basename(name))
			shutil.copyfile(name, newname)


	def copyOtherFiles(self):
		"""
		Make a copy of any other necessary files in the new work dir.
		"""
		self.msg("Copying files.")
		otherFiles = [("404Text.txt",   0),
					  ("AppServer",     1),
					  ("AppServer.bat", 1),
					  ("HTTPServer",    1),
					  ("HTTPServer.bat",1),
					  ("OneShot.cgi",   0),
					  ("WebKit.cgi",    0),
					  ]
		for name, doChmod in otherFiles:
			oldname = os.path.join(self._webKitDir, name)
			newname = os.path.join(self._workDir, os.path.basename(name))
			self.msg("\t%s" % newname)
			shutil.copyfile(oldname, newname)
			if doChmod:
				os.chmod(newname, 0755)
		self.msg("\n")


	def makeLauncherScripts(self):
		"""
		Using templates loacted below, make the Launcher script for
		launching the AppServer in various ways.  Also makes writes
		the Webware and the runtime directories into the CGI adapter
		scripts.
		"""
		self.msg("Creating launcher scripts.")
		scripts = [ ("Launch.py", _Launch_py),
			    ]
		for name, template in scripts:
			filename = os.path.join(self._workDir, name)
			open(filename, "w").write(template % self._substVals)
			os.chmod(filename, 0755)
			self.msg("\t%s created." % filename)

		for name in ["OneShot.cgi", "WebKit.cgi"]:
			filename = os.path.join(self._workDir, name)
			content = open(filename).readlines()
			output  = open(filename, "wt")
 			for line in content:
				s = string.split(line)
				if s and s[0] == 'WebwareDir' and s[2] == 'None':
					line = "WebwareDir = '%(WEBWARE)s'\n" % self._substVals
				elif s and s[0] == 'AppWorkDir' and s[2] == 'None':
					line = "AppWorkDir = '%(WORKDIR)s'\n" % self._substVals
				output.write(line)
			output.close()
			os.chmod(filename, 0755)
			self.msg("\t%s updated." % filename)

		self.msg("\n")


	def makeDefaultContext(self):
		"""
		Make a very simple context for the newbie user to play with.
		"""
		if self._sample is not None:
			self.msg("Creating default context.")
			name = os.path.join(self._workDir, self._sample)
			if not os.path.exists(name):
				os.mkdir(name)
			name2 = os.path.join(name, 'Main.py')
			open(name2, "w").write(_Main_py % self._substVals)
			name2 = os.path.join(name, '__init__.py')
			open(name2, "w").write(_init_py)

			self.msg("Updating config for default context.")
			filename = os.path.join(self._workDir, "Configs", "Application.config")
			content = open(filename).readlines()
			output  = open(filename, "wt")
			for line in content:
				pos = string.find(line, "##MAWD")
				if pos != -1:
					line = "\t\t\t\t\t\t\t '%(CTX)s':     '%(CTX)s',\n"\
							"\t\t\t\t\t\t\t 'default':       '%(CTX)s',\n"\
							% {'CTX' : self._sample}

				output.write(line)
		self.msg("\n")



	def printCompleted(self):
		print """\n\n
Congratulations, you've just created a runtime working directory for
Webware.  To get started quickly you can run these commands:

	cd %(WORKDIR)s
	HTTPServer

and then point your browser to http://localhost:8086/.	The page you
see is generated from the code in the %(DEFAULT)s directory and is
there for you to play with and to build upon.

For a more robust solution, run the AppServer script and then copy
WebKit.cgi to your web server's cgi-bin directory, or anywhere else
that it will execute CGIs from.	 There are also several adapters in
the  Webware/WebKit directory that allow you to connect from the web
server to the WebKit AppServer without using CGI.

Have fun!
""" % self._substVals


	def msg(self, text):
		if self._verbose:
			print text





#----------------------------------------------------------------------
# A template for the launcher script

_Launch_py = """\
#!/usr/bin/env python

import os, sys

webwarePath = '%(WEBWARE)s'
appWorkPath = '%(WORKDIR)s'


def main(args):
	# ensure Webware is on sys.path
	sys.path.insert(0, webwarePath)

	# import the master launcher
	import WebKit.Launch

	if len(args) < 2:
		WebKit.Launch.usage()

	# Go!
	WebKit.Launch.launchWebKit(args[1], appWorkPath, args[2:])


if __name__=='__main__':
	main(sys.argv)
"""

#----------------------------------------------------------------------
# This is used to create a very simple sample context for the new
# work dir to give the newbie something easy to play with.

_init_py = """
def contextInitialize(appServer, path):
	# You could put initialization code here to be executed when
	# the context is loaded into WebKit.
	pass
"""

_Main_py = """
from WebKit.Page import Page

class Main(Page):

	def title(self):
		return 'My Sample Context'

	def writeBody(self):
		self.writeln('<h1>Welcome to Webware!</h1>')
		self.writeln('''
		This is a sample context generated for you and has purposly been kept very simple
		to give you something to play with to get yourself started.  The code that implements
		this page is located in <b>%%s</b>.
		''' %% self.request().serverSidePath())

		self.writeln('''
		<p>
		There are more examples and documentaion in the Webware distribution, which you
		can get to from here:<p><ul>
		''')

		adapterName = self.request().adapterName()
		ctxs = self.application().contexts().keys()
		ctxs = filter(lambda ctx: ctx!='default', ctxs)
		ctxs.sort()
		for ctx in ctxs:
			self.writeln('<li><a href="%%s/%%s/">%%s</a>' %% (adapterName, ctx, ctx))

		self.writeln('</ul>')

"""

#----------------------------------------------------------------------


if __name__ == "__main__":
	if len(sys.argv) != 2:
		print __doc__
		sys.exit(1)

	# this assumes that this script is still located in Webware/bin
	p = os.path
	webWareDir = p.abspath(p.join(p.dirname(sys.argv[0]), ".."))

	mawd = MakeAppWorkDir(webWareDir, sys.argv[1])
	mawd.buildWorkDir()
