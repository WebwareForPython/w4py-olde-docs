from ModelObject import ModelObject
from UserDict import UserDict
from MiscUtils import NoDefault
import re
from MiddleKit import StringTypes

nameRE = re.compile(r'^([A-Za-z_][A-Za-z_0-9]*)$')


class Attr(UserDict, ModelObject):
	"""
	An Attr represents an attribute of a Klass mostly be being a dictionary-like object.
	"""

	def __init__(self, dict):
		UserDict.__init__(self, {})
		for key, value in dict.items():
			if key=='Attribute':
				key = 'Name'
			# @@ 2001-02-21 ce: should we always strip string fields? Probably.
			if isinstance(value, StringTypes) and value.strip()=='':
				value = None
			self[key] = value
		match = nameRE.match(self['Name'])
		if match is None or len(match.groups())!=1:
			raise ValueError, 'Bad name (%r) for attribute: %r.' % (self['Name'], dict)

	def name(self):
		return self.data['Name']

	def isRequired(self):
		""" Returns true if a value is required for this attribute. In Python, that means the value cannot be None. In relational theory terms, that means the value cannot be NULL. """
		if not self.has_key('isRequired'):
			req = 0
		else:
			req = self['isRequired']
			if isinstance(req, StringTypes):
				req = req.lower()
			if req in ['', None, 0, '0', 'false']:
				req = 0
			elif req in [1, '1', 'true']:
				req = 1
			else:
				raise ValueError, 'isRequired should be 0 or 1, but == %r' % req
		return int(req)
		# @@ 2000-11-11 ce: we say int() above, but in the future we
		# should provide specific types for the columns of the model

	def setKlass(self, klass):
		""" Sets the klass that the attribute belongs to. """
		self._klass = klass

	def klass(self):
		"""
		Returns the klass that this attribute is declared in and, therefore, belongs to.
		"""
		return self._klass

	def pyGetName(self):
		""" Returns the name that should be used for the Python "get" accessor method for this attribute. This implementation returns the name as it is, so the get methods are obj.foo(). """
		return self.name()

	def pySetName(self):
		""" Returns the name that should be used for the Python "set" accessor method for this attribute. This implementation returns setName, as in obj.setFoo(). """
		name = self.name()
		return 'set'+name[0].upper()+name[1:]

	def setting(self, name, default=NoDefault):
		"""
		Returns the value of a particular configuration setting taken
		from the model.

		Implementation note: Perhaps a future version should ask the
		klass and so on up the chain.
		"""
		return self.model().setting(name, default)

	def model(self):
		return self._klass.klasses()._model
