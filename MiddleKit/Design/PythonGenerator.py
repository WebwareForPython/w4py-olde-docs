from CodeGenerator import CodeGenerator
from time import asctime, localtime, time
import string
import os, sys
from types import *


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
		self._klasses.writePy(generator, dirname)


class ModelObject:

	def writePy(self, generator, out=sys.stdout):
		''' Writes the Python code to define a table for the class. The target can be a file or a filename. '''
		if type(out) is StringType:
			out = open(out, 'w')
			close = 1
		else:
			close = 0
		self.willWritePy(generator, out)
		self._writePy(generator, out)
		self.didWritePy(generator, out)
		if close:
			out.close()


	# @@ 2000-09-16 ce: Do we need the willWritePy() and didWritePy()?

	def willWritePy(self, generator, out):
		pass

	def didWritePy(self, generator, out):
		pass


class Klasses:

	def writePy(self, generator, outdir):
		self._pyOutDir = outdir
		self.willWritePy(generator, outdir)
		self._writePy(generator, outdir)
		self.didWritePy(generator, outdir)

	def _writePy(self, generator, outdir):
		for klass in self._klasses:
			filename = os.path.join(outdir, klass.name()+'.py')
			klass.writePyStubIfNeeded(generator, filename)

			filename = os.path.join(outdir, 'GeneratedPy', 'Gen'+klass.name()+'.py')
			klass.writePy(generator, filename)

		# Write GeneratedPy/__init__.py
		# @@ 2000-10-19 ce: break out into self.writeInitPy()
		filename = os.path.join(outdir, 'GeneratedPy', '__init__.py')
		open(filename, 'w').write('# Hi\n')


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

	def writePyImports(self):
		wr = self._pyOut.write
		supername = self.supername()
		if supername=='MiddleObject':
			wr('\n\nfrom MiddleKit.Run.MiddleObject import MiddleObject\n')
		else:
			pkg = self.setting('Package', '')
			if pkg:
				pkg += '.'
			backPath = '../' * (pkg.count('.')+1)
			wr('''\
import sys
sys.path.insert(0, %(backpath)s)
from %(pkg)s%(supername)s import %(supername)s
del sys.path[0]

''' % locals())

	def writePyClassDef(self):
		wr = self._pyOut.write
		wr('\n\nclass Gen%s(%s):\n' % (self.name(), self.supername()))
		self.writePyInit()
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

	def writePyAccessors(self):
		''' Write Python accessors for attributes simply by asking each one to do so. '''
		out = self._pyOut
		for attr in self.attrs():
			attr.writePyAccessors(out)


class Attr:

	def defaultValue(self):
		''' Returns the default value as a string of legal Python text. '''
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
		'''
		Returns a bona fide Python value given a string. Invokers should never pass None or blank strings.
		Used by at least defaultValue().
		Subclass responsibility.
		'''
		raise SubclassResponsibilityError

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
		if self.isRequired():
			assertions = 'assert value is not None'
		else:
			assertions = ''
		out.write('''
	def %(pySetName)s(self, value):
		%(assertions)s
		self._%(name)s = value
''' % locals())


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


class IntAttr:

	def stringToValue(self, string):
		return int(string)


class LongAttr:

	def stringToValue(self, string):
		return long(string)


class FloatAttr:

	def stringToValue(self, string):
		return float(string)


class StringAttr:

	def stringToValue(self, string):
		return string


class EnumAttr:

	def stringToValue(self, string):
		return repr(string)


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
			assert type(value) is InstanceType
			from %(package)s%(targetClassName)s import %(targetClassName)s
			assert isinstance(value, %(targetClassName)s)
		self._%(name)s = value
''' % locals())


class ListAttr:

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
		''' Subclass responsibility. '''
		raise SubclassResponsibility

	def writePySet(self, out, names=None):
		''' Raises an exception in order to ensure that our inherited "PySet" code generation is used. '''
		raise AssertionError, 'Lists do not have a set method.'

	def writePyAddTo(self, out, names):
		out.write('''
	def addTo%(capName)s(self, value):
		assert value is not None
		from %(package)s%(targetClassName)s import %(targetClassName)s
		assert isinstance(value, %(targetClassName)s)
		assert value.%(lowerSourceClassName)s()==None
		self.%(pyGetName)s().append(value)
		value.set%(sourceClassName)s(self)
		if value.serialNum()==0:
			self.store().addObject(value)
''' % names)
