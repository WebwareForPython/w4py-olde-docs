from CodeGenerator import CodeGenerator
from MiscUtils import AbstractError
from time import asctime, localtime, time
import string
import os, sys
from types import *

try:
	from mx import DateTime
except ImportError:
	DateTime = None


class PythonGenerator(CodeGenerator):

	def defaultConfig(self):
		return {
			'DestDir': 'GeneratedPy',
		}

	def generate(self, dirname):
		self.requireDir(dirname)
		# @@ 2000-10-17 ce: ACK! Get rid of all these hard coded 'GeneratedPy' strings
		# @@ 2000-10-16 ce: should delete GeneratedPy/
		self.requireDir(os.path.join(dirname, 'GeneratedPy'))
		self.writeInfoFile(os.path.join(dirname, 'GeneratedPy', 'Info.text'))
		self._model.writePy(self, dirname)


class Model:

	def writePy(self, generator, dirname):
		if self.hasSetting('Package'):
			filename = os.path.join(dirname, '__init__.py')
			if not os.path.exists(filename):
				open(filename, 'w').write('#')

		for klass in self._allKlassesInOrder:
			filename = os.path.join(dirname, klass.name()+'.py')
			klass.writePyStubIfNeeded(generator, filename)

			filename = os.path.join(dirname, 'GeneratedPy', 'Gen'+klass.name()+'.py')
			klass.writePy(generator, filename)

		filename = os.path.join(dirname, 'GeneratedPy', '__init__.py')
		open(filename, 'w').write('# __init__.py\n')


class ModelObject:

	def writePy(self, generator, out=sys.stdout):
		""" Writes the Python code to define a table for the class. The target can be a file or a filename. """
		if type(out) is StringType:
			out = open(out, 'w')
			close = 1
		else:
			close = 0
		self._writePy(generator, out)
		if close:
			out.close()


class Klass:

	def writePyStubIfNeeded(self, generator, filename):
		if not os.path.exists(filename):
			# Grab values for use in writing file
			basename = os.path.basename(filename)
			name = self.name()
			superclassModule = 'GeneratedPy.Gen' + name
			superclassName = 'Gen' + name

			# Write file
			file = open(filename, 'w')
			file.write(PyStubTemplate % locals())
			file.close()

	def _writePy(self, generator, out):
		self._pyGenerator = generator
		self._pyOut = out
		self.writePyFileDocString()
		self.writePyAttrCaches()
		self.writePyImports()
		self.writePyClassDef()

	def writePyFileDocString(self):
		wr = self._pyOut.write
		out = self._pyOut
		wr("""'''\n""")
		wr('Gen%s.py\n' % self.name())
		wr('%s\n' % asctime(localtime(time())))
		wr('Generated by MiddleKit.\n') # @@ 2000-10-01 ce: Put the version number here
		wr("""'''\n""")

	def writePyAttrCaches(self):

		wr = self._pyOut.write
		wr('''
# MK attribute caches for setFoo() methods
''')
		for attr in self.allAttrs():
			wr('_%sAttr = None\n' % attr.name())
		wr('\n')

	def writePyImports(self):
		wr = self._pyOut.write
		wr('import types\n')
		if DateTime:
			wr('from mx import DateTime\n')
		supername = self.supername()
		if supername=='MiddleObject':
			wr('\n\nfrom MiddleKit.Run.MiddleObject import MiddleObject\n')
		else:
			pkg = self._klasses._model.setting('Package', '')
			if pkg:
				pkg += '.'
			#backPath = repr('../' * (pkg.count('.')+1))
			backPath = 'dirname(__file__)'
			for i in xrange(pkg.count('.')+1):
				backPath = 'dirname(%s)' % backPath
			wr('''\
import sys
from os.path import dirname
sys.path.insert(0, %(backPath)s)
from %(pkg)s%(supername)s import %(supername)s
del sys.path[0]

''' % locals())

	def writePyClassDef(self):
		wr = self._pyOut.write
		wr('\n\nclass Gen%s(%s):\n' % (self.name(), self.supername()))
		self.writePyInit()
		self.writePyReadStoreData()
		self.writePyAccessors()
		wr('\n')

	def maxAttrNameLen(self):
		maxLen = 0
		for attr in self.attrs():
			if maxLen<len(attr.name()):
				maxLen = len(attr.name())
		return maxLen

	def writePyInit(self):
		wr = self._pyOut.write
		wr('\n\tdef __init__(self):\n')
		wr('\t\t%s.__init__(self)\n' % self.supername())
		maxLen = self.maxAttrNameLen()
		for attr in self.attrs():
			name = string.ljust(attr.name(), maxLen)
			wr('\t\tself._%s = %r\n' % (name, attr.defaultValue()))
		wr('\n')

	def writePyReadStoreData(self):
		wr = self._pyOut.write
		statements = [attr.pyReadStoreDataStatement() for attr in self.attrs()]
		statements = [s for s in statements if s]
		if statements:
			wr('''
	def readStoreData(self, store, row):
		if not self._mk_inStore:
''')
			for s in statements:
				wr(s)
			wr('\t\t%s.readStoreData(self, store, row)\n\n' % self.supername())

	def writePyAccessors(self):
		""" Write Python accessors for attributes simply by asking each one to do so. """
		out = self._pyOut
		for attr in self.attrs():
			attr.writePyAccessors(out)


class Attr:

	def defaultValue(self):
		""" Returns the default value as a legal Pythonic value. """
		if self.has_key('Default'):
			default = self['Default']
			if type(default) is type(''):
				default = default.strip()
			if not default:
				return None
			else:
				return self.stringToValue(default)
		else:
			return None

	def stringToValue(self, string):
		# @@ 2000-11-25 ce: consider moving this to Core
		# @@ 2000-11-25 ce: also, this might be usable in the store
		"""
		Returns a bona fide Python value given a string. Invokers should never pass None or blank strings.
		Used by at least defaultValue().
		Subclass responsibility.
		"""
		raise AbstractError

	def pyReadStoreDataStatement(self):
		return None

	def writePyAccessors(self, out):
		self.writePyGet(out)
		self.writePySet(out)

	def writePyGet(self, out):
		out.write('''
	def %s(self):
		return self._%s
''' % (self.pyGetName(), self.name()))

	def writePySet(self, out):
		name = self.name()
		pySetName = self.pySetName()
		capName = string.upper(name[0]) + name[1:]
		values = locals()
		out.write('\n\tdef %(pySetName)s(self, value):\n' % values)
		self.writePySetChecks(out)
		self.writePySetAssignment(out.write, name)

	def writePySetAssignment(self, write, name):
		write('''
		# set the attribute
		origValue = self._%(name)s
		self._%(name)s = value

		# MiddleKit machinery
		self._mk_changed = 1  # @@ original semantics, but I think this should be under "if not self._mk_initing..."
		if not self._mk_initing and self._mk_serialNum>0 and value is not origValue:
			global _%(name)sAttr
			if _%(name)sAttr is None:
				_%(name)sAttr = self.klass().lookupAttr('%(name)s')
				if not _%(name)sAttr.shouldRegisterChanges():
					_%(name)sAttr = 0
			if _%(name)sAttr:
				# Record that it has been changed
				if self._mk_changedAttrs is None:
					self._mk_changedAttrs = {} # maps name to attribute
				self._mk_changedAttrs['%(name)s'] = _%(name)sAttr  # changedAttrs is a set
				# Tell ObjectStore it happened
				self._mk_store.objectChanged(self)
''' % {'name': name})

	def writePySetChecks(self, out):
		if self.isRequired():
			out.write('\t\tassert value is not None\n')


PyStubTemplate = """\
'''
%(basename)s
'''


from %(superclassModule)s import %(superclassName)s


class %(name)s(%(superclassName)s):

	def __init__(self):
		%(superclassName)s.__init__(self)
"""


class BoolAttr:

	def stringToValue(self, string):
		string = string.upper()
		if string=='TRUE' or string=='YES':
			value = 1
		elif string=='FALSE' or string=='NO':
			value = 0
		else:
			value = int(string)
		assert value==0 or value==1
		return value

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		out.write('''\
		if value is not None:
			if type(value) is not types.IntType:
				raise TypeError, 'expecting int for bool, but got value %r of type %r instead' % (value, type(value))
			if value not in (0, 1):
				raise ValueError, 'expecting 0 or 1 for bool, but got %s instead' % value
''')


class IntAttr:

	def stringToValue(self, string):
		return int(string)

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		out.write('''\
		if value is not None:
			if type(value) is types.LongType:
				value = int(value)
			elif type(value) is not types.IntType:
				raise TypeError, 'expecting int type, but got value %r of type %r instead' % (value, type(value))
''')


class LongAttr:

	def stringToValue(self, string):
		return long(string)

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		out.write('''\
		if value is not None:
			if type(value) is types.IntType:
				value = long(value)
			elif type(value) is not types.LongType:
				raise TypeError, 'expecting long type, but got value %r of type %r instead' % (value, type(value))
''')


class FloatAttr:

	def stringToValue(self, string):
		return float(string)

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		out.write('''\
		if value is not None:
			if type(value) in (types.IntType, types.LongType):
				value = float(value)
			elif type(value) is not types.FloatType:
				raise TypeError, 'expecting float type, but got value %r of type %r instead' % (value, type(value))
''')


class StringAttr:

	def stringToValue(self, string):
		return string

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		out.write('''\
		if value is not None:
			if type(value) is not types.StringType:
				raise TypeError, 'expecting string type, but got value %r of type %r instead' % (value, type(value))
''')


class EnumAttr:

	def stringToValue(self, string):
		return string

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		out.write('''\
		if value is not None:
			if type(value) is not types.StringType:
				raise TypeError, 'expecting string type for enum, but got value %%r of type %%r instead' %% (value, type(value))
			attr = self.klass().lookupAttr('%s')
			if not attr.hasEnum(value):
				raise ValueError, 'expecting one of %%r, but got %%r instead' %% (attr.enums(), value)
''' % self.name())
		# @@ 2001-07-11 ce: could optimize above code


class AnyDateTimeAttr:

	def mxDateTimeTypeName(self):
		raise AbstractError, self.__class__

	def writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		if DateTime:
			out.write('''\
		# have DateTime
		if value is not None:
			if type(value) is type(''):
				value = DateTime.DateTimeFrom(value)
			if type(value) is not DateTime.%s:
				raise TypeError, 'expecting %s type, but got value %%r of type %%r instead' %% (value, type(value))
''' % (self.mxDateTimeTypeName(), self['Type']))
		else:
			out.write('''\
		# no DateTime, use strings
		if value is not None:
			if type(value) is not types.StringType:
				raise TypeError, 'expecting string type, but got value %r of type %r instead' % (value, type(value))
''')


class DateAttr:

	def mxDateTimeTypeName(self):
		return 'DateTimeType'


class TimeAttr:

	def mxDateTimeTypeName(self):
		return 'DateTimeDeltaType'


class DateTimeAttr:

	def mxDateTimeTypeName(self):
		return 'DateTimeType'


class ObjRefAttr:

	def writePySet(self, out):
		name = self.name()
		pySetName = self.pySetName()
		targetClassName = self.className()
		package = self.setting('Package', '')
		if package:
			package += '.'
		if self.isRequired():
			reqAssert = 'assert value is not None'
		else:
			reqAssert = ''
		out.write('''
	def %(pySetName)s(self, value):
		%(reqAssert)s
		if value is not None and type(value) is not LongType:
			if not type(value) is InstanceType:
				raise TypeError, 'expecting InstanceType, but got value %%r of type %%r instead' %% (value, type(value))
			from %(package)s%(targetClassName)s import %(targetClassName)s
			if not isinstance(value, %(targetClassName)s):
				raise TypeError, 'expecting %(targetClassName)s, but got value %%r of type %%r instead' %% (value, type(value))
''' % locals())
		self.writePySetAssignment(out.write, name)


class ListAttr:

	def defaultValue(self):
		""" Returns the default value as a legal Pythonic value. """
		assert not self.get('Default', 0), 'Cannot have default values for lists.'
		return []

	def pyReadStoreDataStatement(self):
		# Set the lists to None on the very first read from the store
		# so the list get methods will fetch the lists from the store.
		return '\t\t\tself._%s = None\n' % self.name()

	def writePyAccessors(self, out):
		# Create various name values that are needed in code generation
		name = self.name()
		pyGetName = self.pyGetName()
		pySetName = self.pySetName()
		capName = name[0].upper() + name[1:]
		sourceClassName = self.klass().name()
		targetClassName = self.className()
		lowerSourceClassName = sourceClassName[0].lower() + sourceClassName[1:]
		package = self.setting('Package', '')
		if package:
			package += '.'
		names = locals()

		# Invoke various code gen methods with the names
		self.writePyGet(out, names)
		self.writePyAddTo(out, names)

	def writePyGet(self, out, names):
		""" Subclass responsibility. """
		raise SubclassResponsibility

	def writePySet(self, out, names=None):
		""" Raises an exception in order to ensure that our inherited "PySet" code generation is used. """
		raise AssertionError, 'Lists do not have a set method.'

	def writePyAddTo(self, out, names):
		out.write('''
	def addTo%(capName)s(self, value):
		assert value is not None
		from %(package)s%(targetClassName)s import %(targetClassName)s
		assert isinstance(value, %(targetClassName)s)
		assert value.%(lowerSourceClassName)s() is None
		self.%(pyGetName)s().append(value)
		value.set%(sourceClassName)s(self)
		store = self.store()
		if value.serialNum()==0 and self.isInStore():
			store.addObject(value)
''' % names)
