#
# AjaxPage.py
#
# Written by John Dickinson based on ideas from
# Apple developer code (developer.apple.com)
# and Nevow 0.4.1 (www.nevow.org),
# with minor changes made by Robert Forkel.
#

import StringIO, traceback, time

from ExamplePage import ExamplePage as BaseClass

RESPONSE_TIMEOUT = 100


# PyJavascript and quote_js based on ideas from Nevow 0.4.1 (www.nevow.org)

def quote_js(what):
	"""Return quoted JavaScript string corresponding to the Python object."""
	if isinstance(what, bool):
		ret = str(what).lower()
	elif isinstance(what, (int, long, float, PyJavascript)):
		ret = str(what)
	else:
		ret = "'%s'" % str(what).replace('\\','\\\\').replace('\'','\\\'').replace('\n','\\n')
	return ret


class PyJavascript(object):
	"""This class simply tanslates a Python expression into a JavaScript string."""

	def __init__(self, name):
		self.__name = name

	def __getattr__(self, aname):
		return self.__class__('%s.%s'%(self, aname))

	def __str__(self):
		return self.__name

	def __call__(self, *a, **kw):
		args = ','.join([quote_js(i) for i in a])
		kwargs = ','.join(['%s=%s' % (k,quote_js(v)) for k,v in kw.items()])
		if args and kwargs:
			allargs = '%s,%s' % (args, kwargs)
		elif not kwargs:
			allargs = args
		elif not args:
			allargs = kwargs
		return self.__class__('%s(%s)' % (self, allargs))

	def __getitem__(self,index):
		return self.__class__('%s[%s]' % (self, quote_js(index)))

	def __repr__(self):
		return self.__str__()


class AjaxPage(BaseClass):
	"""A superclass for Webware servlets using Ajax techniques.

	AjaxPage can be used to make coding XMLHttpRequest() applications easier.

	Subclasses should override the method ajax_allowed() which returns a list
	of method names. These method names refer to Webware Servlet methods that
	are able to be called by an Ajax-enabled web page. This is very similar
	in functionality to webware's actions.

	"""

	# Class level variables to help make client code simpler:
	document = PyJavascript('document')
	setTag = PyJavascript('ajax_setTag')
	setClass = PyJavascript('ajax_setClass')
	setValue = PyJavascript('ajax_setValue')
	setReadonly = PyJavascript('ajax_setReadonly')
	alert = PyJavascript('alert')
	generic_ajax = PyJavascript('generic_ajax')
	generic_ajax_form = PyJavascript('generic_ajax_form')
	this = PyJavascript('this')
	_responseQueue = {}

	def writeJavaScript(self):
		BaseClass.writeJavaScript(self)
		self.writeln('<script type="text/javascript" src="ajaxpage.js"></script>')

	def actions(self):
		return BaseClass.actions(self) + ['ajax_controller','ajax_response']

	def ajax_allowed(self):
		return []

	def ajax_response(self):
		who = self.request().remoteAddress()
		start_time = time.time()
		request_count = self.request().fields().get('req_count')
		while True:
			if self._responseQueue.get(who,[]):
				self.write(';'.join([str(val) for req_number, val in self._responseQueue[who]]))
				self._responseQueue[who] = []
				break
			else:
				# Check for timeout,
				if time.time() - start_time > RESPONSE_TIMEOUT:
					break
				# Also check to see if the server wants to shut down:
				if self.application().server().running <= 2:
					self.write(self.alert('The server is shutting down'
						' and your request is not finished. Please try again later.'))
					break

	def ajax_controller(self):
		fields = self.request().fields()
		func = fields.get('f')
		args = fields.get('a', [])
		if type(args) != type([]):
			args = [args]
		req_number = args[-1]
		start_time = time.time()
		val = self.alert('There was some problem!')
		if func in self.ajax_allowed():
			try:
				func_obj = getattr(self,func)
			except AttributeError:
				val = self.alert('%s, although an approved function, was not found' % func)
			else:
				try: # pull off sequence number added to "fix" IE
					val = str(func_obj(*args[:-1]))
				except Exception:
					err = StringIO.StringIO()
					traceback.print_exc(file=err)
					e = err.getvalue()
					val = self.alert('%s was called, but encountered an error: %s'%(func,e))
					err.close()
		else:
			val = self.alert('%s is not an approved function' % func)

		if time.time() - start_time < RESPONSE_TIMEOUT:
			self.write(val)
		else:
			who = self.request().remoteAddress()
			if not self._responseQueue.has_key(who):
				self._responseQueue[who] = [(req_number, val)]
			else:
				self._responseQueue[who].append((req_number, val))

	def ajax_cmdToClient(self, cmd):
		remote_address = self.request().remoteAddress()
		if not self._responseQueue.has_key(remote_address):
			self._responseQueue[remote_address] = []
		self._responseQueue[remote_address].append((None, cmd))

	def preAction(self, action_name):
		if action_name.startswith('ajax_'):
			pass
		else:
			BaseClass.preAction(self,action_name)

	def postAction(self, action_name):
		if action_name.startswith('ajax_'):
			pass
		else:
			BaseClass.postAction(self,action_name)
