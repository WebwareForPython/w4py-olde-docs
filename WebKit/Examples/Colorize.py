from Page import Page
import sys,os,string
try:
	from cStringIO import StringIO
except:
	from StringIO import StringIO

class Colorize(Page):
	"""
	Syntax highlights python source files.  Set a variable 'filename' in the request so I know which file to work on.
	This also demonstrates forwarding.  THe View servlet actually forwards it's request here.
	"""

	def respond(self, transaction):
		"""
		write out a syntax hilighted version of the file.  The filename is an attribute of the request object
		"""
		res=transaction._response
		req=self._request
		if not req.hasField('filename'):
			res.write("No filename given to syntax color!")
			return
		filename = req.relativePath(req.field('filename')+'.py')
		if not os.path.exists(filename):
			res.write(filename+" does not exist.")
			return

		try:
			import py2html
		except:
			import imp
			modinfo=imp.find_module('py2html',["DocSupport/",])
			py2html=imp.load_module('py2html',modinfo[0],modinfo[1],modinfo[2])


		try:
			import PyFontify
		except:
			import imp
			modinfo=imp.find_module('PyFontify',["DocSupport/",])
			PyFontify=imp.load_module('PyFontify',modinfo[0],modinfo[1],modinfo[2])


		myout=StringIO()
		realout=sys.stdout
		sys.stdout=myout

		py2html.main((None,'-stdout','-files',filename))

		res.write(myout.getvalue())

		sys.stdout=realout

		
