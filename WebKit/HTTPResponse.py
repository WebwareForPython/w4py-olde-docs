from Common import *
from Response import Response
from WebKit.Cookie import Cookie

debug = 0

class HTTPResponse(Response):


	## Init ##

	def __init__(self, transaction, strmOut, headers=None):
		""" Initializes the request. """

		Response.__init__(self, transaction, strmOut)

		self._committed = 0

		if headers is None:
			self._headers = {}#{'Content-type': 'text/html'}
			self.setHeader('Content-type','text/html')
		else:
			self._headers = headers

		self._cookies   = {}


	## Headers ##

	def header(self, name, default=Tombstone):
		""" Returns the value of the specified header. """
		if default is Tombstone:
			return self._headers[string.lower(name)]
		else:
			return self._headers.get(string.lower(name), default)

	def hasHeader(self, name):
		return self._headers.has_key(string.lower(name))

	def setHeader(self, name, value):
		"""
		Sets a specific header by name.
		-  parameters:
		name: Header Name
		value: Header Value
		"""
		assert self._committed==0, "Headers have already been sent"
		self._headers[string.lower(name)] = value


	def addHeader(self, name, value):
		"""
		Adds a specific header by name.
		"""
		print "addHeader is deprecated.  Use setHeader()."
		assert self._committed==0
		self.setHeader(name, value)

	def headers(self, name=None):
		""" Returns a dictionary-style object of all Header objects contained by this request. """
		return self._headers

	def clearHeaders(self):
		""" Clears all the headers. You might consider a setHeader('Content-type', 'text/html') or something similar after this. """
		assert self._committed==0
		self._headers = {}


	## Cookies ##

	def cookie(self, name):
		""" Returns the value of the specified cookie. """
		return self._cookies[name]

	def hasCookie(self, name):
		"""
		Returns true if the specified cookie is present.
		"""
		return self._cookies.has_key(name)

	def setCookie(self, name, value):
		"""
		Sets the named cookie to a value.
		"""
		assert self._committed==0, "Headers have already been sent"
		self.addCookie(Cookie(name, value))

	def addCookie(self, cookie):
		"""
		Adds a cookie that will be sent with this response.
		cookie is a Cookie object instance.  See WebKit.Cookie.
		"""
		assert self._committed==0
		assert isinstance(cookie, Cookie)
		self._cookies[cookie.name()] = cookie

	def cookies(self):
		"""
		Returns a dictionary-style object of all Cookie objects that will be sent
		with this response.
		"""
		return self._cookies

	def clearCookies(self):
		""" Clears all the cookies. """
		assert self._committed==0
		self._cookies = {}


	## Status ##

	def setStatus(self, code, msg=''):
		""" Set the status code of the response, such as 200, 'OK'. """
		assert self._committed==0, "Headers already sent."
		self.setHeader('Status', str(code) + ' ' + msg)


	## Special responses ##

	def sendError(self, code, msg=''):
		"""
		Sets the status code to the specified code and message.
		"""
		assert self._committed==0, "Response already partially sent"
		self.setStatus(code, msg)

	def sendRedirect(self, url):
		"""
		This method sets the headers and content for the redirect, but does
		NOT change the cookies. Use clearCookies() as appropriate.

		@@ 2002-03-21 ce: I thought cookies were ignored by user agents if a
		redirect occurred. We should verify and update code or docs as appropriate.
		"""
		# ftp://ftp.isi.edu/in-notes/rfc2616.txt
		# Sections: 10.3.3 and others

		assert self._committed==0, "Headers already sent"

   		self.setHeader('Status', '302 Redirect')
	   	self.setHeader('Location', url)
		self.setHeader('Content-type', 'text/html')

		self.write('<html> <body> This page has been redirected to <a href="%s">%s</a>. </body> </html>' % (url, url))


	## Output ##

	def write(self, charstr=None):
		"""
		Write charstr to the response stream.
		"""
		if charstr: self._strmOut.write(charstr)
		if not self._committed and self._strmOut._needCommit:
			self.commit()

	def flush(self, autoFlush=1):
		"""
		Send all accumulated response data now.
		Commits the response headers and tells the underlying stream to flush.
		if autoFlush is 1, the responseStream will flush itself automatically from now on.
		"""
		if not self._committed:
			self.commit()
		self._strmOut.flush()
		self._strmOut.autoCommit(1)


	def isCommitted(self):
		"""
		Has the reponse already been partially or completely sent?
		If this returns true, no new headers/cookies can be added to the response.
		"""
		return self._committed

	def deliver(self):
		"""
		The final step in the processing cycle.
		Not used for much with responseStreams added.
		"""
		if debug: print "HTTPResponse deliver called"
		self.recordEndTime()
		if not self._committed: self.commit()

	def commit(self):
		"""
		Write out all headers to the reponse stream, and tell the underlying
		response stream it can start sending data.
		"""
		if debug: print "HTTPResponse commit"
		self.recordSession()
		self.writeHeaders()
		self._committed = 1
		self._strmOut.commit()

	def writeHeaders(self):
		"""
		Write headers to the response stream.  Used internally.
		"""
		if self._committed:
			print "response.writeHeaders called when already committed"
			return
		headers = []
		headerstring = ''
		for key, value in self._headers.items():
			headers.append((key, value))
		for cookie in self._cookies.values():
			headers.append(('Set-Cookie', cookie.headerValue()))
		for i in headers:
			hdrstr = i[0] + ': ' + i[1] + '\r\n'
			if string.lower(i[0]) == 'status':
				headerstring = string.join((hdrstr, headerstring),'')
			else:
				headerstring = string.join((headerstring, hdrstr),'')
		headerstring = string.join((headerstring,'\r\n'),'')
		self._strmOut.prepend(headerstring)

	def recordSession(self):
		""" Invoked by commit() to record the session id in the response (if a session exists). This implementation sets a cookie for that purpose. For people who don't like sweets, a future version could check a setting and instead of using cookies, could parse the HTML and update all the relevant URLs to include the session id (which implies a big performance hit). Or we could require site developers to always pass their URLs through a function which adds the session id (which implies pain). Personally, I'd rather just use cookies. You can experiment with different techniques by subclassing Session and overriding this method. Just make sure Application knows which "session" class to use. """
		sess = self._transaction._session
		if debug: prefix = '>> recordSession:'
		if sess:
			cookie = Cookie('_SID_', sess.identifier())
			cookie.setPath('/')
			if sess.isExpired() or sess.timeout() == 0:
				# Invalid -- tell client to forget the cookie.
				cookie.setMaxAge(0)
				cookie.setExpires(-365*24*60*60)
			self.addCookie(cookie)
			if debug: print prefix, 'setting sid =', sess.identifier()
		else:
			if debug: print prefix, 'did not set sid'

	def reset(self):
		"""
		Resets the response (such as headers, cookies and contents).
		"""

		assert self._committed == 0
		self._headers = {}
	   	self.setHeader('Content-type','text/html')
		self._cookies = {}
		self._strmOut.clear()


	def rawResponse(self):
		""" Returns the final contents of the response. Don't invoke this method until after deliver().
		Returns a dictionary representing the response containing only strings, numbers, lists, tuples, etc. with no backreferences. That means you don't need any special imports to examine the contents and you can marshal it. Currently there are two keys. 'headers' is list of tuples each of which contains two strings: the header and it's value. 'contents' is a string (that may be binary (for example, if an image were being returned)). """

		headers = []
		for key, value in self._headers.items():
			headers.append((key, value))
		for cookie in self._cookies.values():
			headers.append(('Set-Cookie', cookie.headerValue()))
		return {
			'headers': headers,
			'contents': self._strmOut.buffer()
		}

	def size(self):
		"""
		Returns the size of the final contents of the response. Don't invoke this
		method until after deliver().
		"""
		return self._strmOut.size()

##	def appendRawResponse(self, rawRes):
##		"""
##		Appends the contents of the raw response (as returned by some transaction's rawResponse() method) to this response.
##		The headers of the receiving response take precedence over the appended response.
##		This method was built primarily to support Application.forwardRequest().
##		"""
##		assert self._committed==0
##		headers = rawRes.get('headers', [])
##		for key, value in headers:
##			if not self._headers.has_key(key):
##				self._headers[key] = value
##		self.write(rawRes['contents'])

	def mergeTextHeaders(self, headerstr):
		"""
		Given a string of headers (separated by newlines), merge them into our headers.
		"""
		linesep = "\n"

		lines = string.split(headerstr,"\n")
		for i in lines:
			sep = string.find(i, ":")
			if sep:
				self.setHeader(i[:sep], string.rstrip(i[sep+1:]))


	## Exception reporting ##

	exceptionReportAttrNames = Response.exceptionReportAttrNames + ['committed', 'headers', 'cookies']
