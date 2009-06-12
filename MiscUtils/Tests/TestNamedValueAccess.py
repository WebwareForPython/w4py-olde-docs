import sys
import unittest
import types
from UserDict import UserDict

import FixPath
from MiscUtils.NamedValueAccess import (
    NamedValueAccessError, valueForKey, valueForName, NamedValueAccess)
from MiscUtils import AbstractError, NoDefault


class T(object):
    pass


class T1(T):

    def foo(self):
        return 1


class T2(T):

    def _foo(self):
        return 1


class T3(T):

    def foo(self):
        return 1

    def _foo(self):
        return 0


class T4(T):

    def foo(self):
        return 1

    def __init__(self):
        self._foo = 0


class T5(T):

    def __init__(self):
        self.foo = 0

    def _foo(self):
        return 1


class T6(T):

    def __init__(self):
        self.foo = 1
        self._foo = 0


class T7(T):

    def valueForKey(self, key, default):
        if key == 'foo':
            return 1
        elif key == 'nextObject':
            return getattr(self, 'nextObject')
        else:
            if default is NoDefault:
                raise NamedValueAccessError(key)
            else:
                return default


class T8(T):

    def valueForUnknownKey(self, key, default):
        if key == 'foo':
            return 1
        else:
            if default is NoDefault:
                raise NamedValueAccessError, key
            else:
                return default


# Make a list of all the 't' classes which are used in testing
tClasses = []
for name in dir():
    if len(name) == 2 and name[0] == 'T':
        tClasses.append(globals()[name])


class NamedValueAccessTest(unittest.TestCase):
    """Abstract root ancestor for all test case classes in this file."""


class LookupTest(NamedValueAccessTest):
    """Abstract super class for the test cases covering the functions.

    Subclasses must implement self.lookup() and can make use of
    self.classes and self.objs.

    """

    def setUp(self):
        self.setUpClasses()
        self.setUpObjects()

    def setUpClasses(self):
        self.classes = tClasses

    def setUpObjects(self):
        self.objs = map(lambda klass: klass(), self.classes)

    def lookup(self, obj, key, default=NoDefault):
        raise AbstractError, self.__class__

    def checkBasicAccess(self):
        """Check the basic access functionality.

        Invoke the look up function with key 'foo', expecting 1 in return.
        Invoke the look up with 'bar', expected an exception.
        Invoke the look up with 'bar' and default 2, expecting 2.
        """
        func = self.lookup
        for obj in self.objs:

            value = func(obj, 'foo')
            assert value == 1, 'value = %r, obj = %r' % (value, obj)

            self.assertRaises(NamedValueAccessError, func, obj, 'bar')

            value = func(obj, 'bar', 2)
            assert value == 2, 'value = %r, obj = %r' % (value, obj)

    def checkBasicAccessRepeated(self):
        """Just repeat checkBasicAccess multiple times to check stability."""
        for count in xrange(50):
            # Yes, it's safe to invoke this other particular test
            # multiple times without the usual setUp()/tearDown() cycle
            self.checkBasicAccess()


class ValueForKeyTest(LookupTest):

    def lookup(self, obj, key, default=NoDefault):
        return valueForKey(obj, key, default)


class ValueForNameTest(LookupTest):

    def lookup(self, obj, key, default=NoDefault):
        return valueForName(obj, key, default)

    def checkNamedValueAccess(self):
        objs = self.objs

        # link the objects
        for i in range(len(objs)-1):
            objs[i].nextObject = objs[i+1]

        # test the links
        for i in range(len(objs)):
            name = 'nextObject.' * i + 'foo'
            assert self.lookup(objs[0], name) == 1

    def checkDicts(self):
        # Basic dicts
        d = {'origin': {'x':1, 'y':2},  'size': {'width':3, 'height':4}}
        obj = self.objs[0]
        obj.rect = d
        self._checkDicts(d, obj)

        # User dicts
        d = UserDict(d)
        obj.rect = d
        self._checkDicts(d, obj)

    def _checkDicts(self, d, obj):
        """ Used exclusively by checkDicts(). """
        assert self.lookup(d, 'origin.x') == 1
        assert self.lookup(obj, 'rect.origin.x')

        self.assertRaises(NamedValueAccessError, self.lookup, d, 'bar')
        self.assertRaises(NamedValueAccessError, self.lookup, obj,  'bar')

        assert self.lookup(d, 'bar', 2) == 2
        assert self.lookup(obj, 'rect.bar', 2) == 2


class MixInTest(NamedValueAccessTest):
    """
    This test case is really just a utility to mix-in the
    NamedValueAccess so that the test classes (T1, T2, ...) inherit it.
    Run this test suite after the basic tests, but before the
    NamedValueAccess mix-in tests.
    """

    def setUp(self):
        if NamedValueAccess not in T.__bases__:
            T.__bases__ += (NamedValueAccess,)

    def checkNothing(self):
        pass


class MixInKeyTest(ValueForKeyTest):

    def lookup(self, obj, key, default=NoDefault):
        if type(obj) is not types.InstanceType:
            # just so non-obj cases pass
            return valueForKey(obj, key, default)
        else:
            # What we're really testing, the mix-in method:
            return obj.valueForKey(key, default)


class MixInNameTest(ValueForNameTest):

    def lookup(self, obj, key, default=NoDefault):
        if type(obj) is not types.InstanceType:
            # just so non-obj cases pass
            return valueForName(obj, key, default)
        else:
            # What we're really testing, the mix-in method:
            return obj.valueForName(key, default)


class MixInExtrasTest(MixInTest, NamedValueAccessTest):

    def checkValuesForNames(self):
        # def valuesForNames(self, keys, default=None, defaults=None, forgive=0)

        # set up structure: rect(attrs(origin(x, y), size(width, height)))
        rect = T1()
        origin = T1()
        origin.x = 5
        origin.y = 6
        size = T1()
        size.width = 43
        size.height = 87
        attrs = {'origin': origin, 'size': size}
        rect.attrs = attrs

        # test integrity of structure and validity of valueForName()
        assert rect.valueForName('attrs') is attrs
        assert rect.valueForName('attrs.origin') is origin
        assert rect.valueForName('attrs.size') is size

        # test valuesForNames()
        notFound = 'notFound'
        assert rect.valuesForNames(['attrs', 'attrs.origin',
            'attrs.size']) == [attrs, origin, size]
        assert rect.valuesForNames(['attrs.dontFind', 'attrs',
            'attrs.origin.dontFind'],
            default=notFound) == [notFound, attrs, notFound]
        assert rect.valuesForNames(['attrs.dontFind', 'attrs',
            'attrs.origin.dontFind'], defaults=[1, 2, 3]) == [1, attrs, 3]
        assert rect.valuesForNames(['attrs.dontFind', 'attrs',
            'attrs.origin.dontFind'], forgive=1) == [attrs]


class WrapperTest(NamedValueAccessTest):
    """
    This is a utility class that modifies LookupTest. After running this,
    run all the LookupTests (e.g., all subclasses) as usual in order to
    test wrappers.
    """

    def setUp(self):
        def setUpObjects(self):
            wrapper = NamedValueAccessWrapper
            self.objs = map(lambda klass, wrapper=wrapper: wrapper(klass()), self.classes)
        LookupTest.setUpObjects = setUpObjects


def makeTestSuite():
    testClasses = [
        ValueForKeyTest,
        ValueForNameTest,
        MixInTest, # utility
            MixInKeyTest,
            MixInNameTest,
            MixInExtrasTest,
        WrapperTest, # utility
            MixInKeyTest,
            MixInNameTest,
            MixInExtrasTest,
    ]
    make = unittest.makeSuite
    suites = [make(klass, 'check') for klass in testClasses]
    return unittest.TestSuite(suites)


def testUse():
    runner = unittest.TextTestRunner(stream=sys.stdout)
    unittest.main(defaultTest='makeTestSuite', testRunner=runner)


def usage():
    sys.stdout = sys.stderr
    print 'usage:'
    print '  TestNamedValueAccess.py use'
    print '  TestNamedValueAccess.py leaks <iterations>'
    print
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        testUse()
    elif sys.argv[1] in ('-h', '--help', 'help'):
        usage()
    elif sys.argv[1] == 'use':
        testUse()
    elif sys.argv[1] == 'leaks':
        testLeaks()
    else:
        usage()
