from Common import *


class SessionStore(Object):
	'''
	SessionStores are dictionary-like objects used by Application to store session state. This class is abstract and it's up to the concrete subclass to implement several key methods that determine how sessions are stored (such as in memory, on disk or in a database).

	Subclasses often encode sessions for storage somewhere. In light of that, this class also defines methods encoder(), decoder() and setEncoderDecoder(). The encoder and decoder default to the load() and dump() functions of the cPickle or pickle module. However, using the setEncoderDecoder() method, you can use the functions from marshal (if appropriate) or your own encoding scheme. Subclasses should use encoder() and decoder() (and not pickle.load() and pickle.dump()).

	Subclasses may rely on the attribute self._app to point to the application.

	Subclasses should be named SessionFooStore since Application expects "Foo" to appear for the "SessionStore" setting and automatically prepends Session and appends Store. Currently, you will also need to add another import statement in Application.py. Search for SessionStore and you'll find the place.

	TO DO

	* Should there be a check-in/check-out strategy for sessions to prevent concurrent requests on the same session? If so, that can probably be done at this level (as opposed to pushing the burden on various subclasses).
	'''


	## Init ##

	def __init__(self, app):
		''' Subclasses must invoke super. '''
		Object.__init__(self)
		self._app = app

		try:
			from cPickle import load, dump
		except ImportError:
			from pickle import load, dump
		self.setEncoderDecoder(dump, load)


	## Access ##

	def application(self):
		return self._app


	## Dictionary-style access ##

	def __len__(self):
		raise SubclassResponsibilityError

	def __getitem__(self, key):
		raise SubclassResponsibilityError

	def __setitem__(self, key, item):
		raise SubclassResponsibilityError

	def __delitem__(self, key):
		raise SubclassResponsibilityError

	def has_key(self, key):
		raise SubclassResponsibilityError

	def keys(self):
		raise SubclassResponsibilityError

	def clear(self):
		raise SubclassResponsibilityError


	## Application support ##

	def storeSession(self, session):
		raise SubclassResponsibilityError

	def storeAllSessions(self):
		raise SubclassResponsibilityError

	def cleanStaleSessions(self):
		"""
		Called by the Application to tell this store to clean out all sessions that
		have exceeded their lifetime.
		"""
		curTime = time.time()
		for key, sess in self.items():
			if (curTime - sess.lastAccessTime()) >= sess.timeout()  or  sess.timeout()==0:
				sess.expiring()
				del self[key]


	## Convenience methods ##

	def items(self):
		return map(lambda key, self=self: (key, self[key]), self.keys())

	def values(self):
		return map(lambda key, self=self: self[key], self.keys())

	def get(self, key, default=None):
		if self.has_key(key):
			return self[key]
		else:
			return default


	## Encoder/decoder ##

	def encoder(self):
		return self._encoder

	def decoder(self):
		return self._decoder

	def setEncoderDecoder(self, encoder, decoder):
		self._encoder = encoder
		self._decoder = decoder


	## As a string ##

	def __repr__(self):
		d = {}
		d.update(self)
		return repr(d)
