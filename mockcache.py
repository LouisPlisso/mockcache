#!/usr/bin/env python
# -*- coding: ascii -*-

# Copyright (c) 2016 Hong Minhee <http://hongminhee.org/>
# Copyright (c) 2010 Lunant <http://lunant.net/>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
"""The Python dictionary-based mock memcached client library. It does not
connect to any memcached server, but keeps a dictionary and stores every cache
into there internally. It is a just emulated API of memcached client only for
tests. It implements expiration also. NOT THREAD-SAFE.  ::

    try:
        import memcache
    except ImportError:
        import warnings
        import mockcache as memcache
        warnings.warn("imported mockcache instead of memcache; cannot find "
                      "memcache module")

    mc = memcache.Client(["127.0.0.1:11211"])

This module and other memcached client libraries have the same behavior.

>>> from mockcache import Client
>>> mc = Client()
>>> mc
<mockcache.Client {}>
>>> mc.get("a")
>>> mc.get("a") is None
True
>>> mc.set("a", "1234")
1
>>> mc.get("a")
'1234'
>>> mc.dictionary[b'a']
('1234', None)
>>> mc.add("a", "1111")
0
>>> mc.get("a")
'1234'
>>> mc.dictionary[b'a']
('1234', None)
>>> mc.replace("a", "2222")
1
>>> mc.get("a")
'2222'
>>> mc.dictionary[b'a']
('2222', None)
>>> mc.append("a", "3")
1
>>> mc.get("a")
'22223'
>>> mc.dictionary[b'a']
('22223', None)
>>> mc.prepend("a", "1")
1
>>> mc.get("a")
'122223'
>>> mc.dictionary[b'a']
('122223', None)
>>> mc.incr("a")
122224
>>> mc.get("a")
122224
>>> mc.dictionary[b'a']
(122224, None)
>>> mc.incr("a", 10)
122234
>>> mc.get("a")
122234
>>> mc.dictionary[b'a']
(122234, None)
>>> mc.decr("a")
122233
>>> mc.get("a")
122233
>>> mc.dictionary[b'a']
(122233, None)
>>> mc.decr("a", 5)
122228
>>> mc.get("a")
122228
>>> mc.dictionary[b'a']
(122228, None)
>>> len(mc.dictionary)
1
>>> mc.replace("b", "value")
0
>>> mc.get("b")
>>> mc.get("b") is None
True
>>> mc.dictionary[b'a']
(122228, None)
>>> len(mc.dictionary)
1
>>> mc.add("b", "value", 5)
1
>>> mc.get("b")
'value'
>>> len(mc.dictionary)
2
>>> mc.dictionary[b'a']
(122228, None)
>>> mc.dictionary[b'b'] # doctest: +ELLIPSIS
('value', ...)
>>> import time
>>> time.sleep(6)
>>> mc.get("b")
>>> mc.get("b") is None
True
>>> len(mc.dictionary)
1
>>> mc.dictionary[b'a']
(122228, None)
>>> mc.set("c", "value")
1
>>> multi_result = mc.get_multi(["a", "b", "c"])
>>> len(multi_result)
2
>>> multi_result[b'a']
122228
>>> multi_result[b'c']
'value'
>>> mc.set_multi({"a": 999, "b": 998, "c": 997}, key_prefix="pf_")
[]
>>> mc.get("pf_a")
999
>>> multi_result = mc.get_multi(["b", "c"], key_prefix="pf_")
>>> len(multi_result)
2
>>> multi_result[b"b"]
998
>>> multi_result[b"c"]
997
>>> mc.delete("a")
1
>>> mc.get("a") is None
True
>>> mc.set("a b c", 123) #doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
MockcachedKeyCharacterError: Control characters not allowed
>>> mc.set(None, 123) #doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
MockcachedKeyNoneError: Key is None
>>> mc.set(123, 123) #doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
MockcachedKeyTypeError: Key must be bytes()'s
>>> mc.set("a" * 251, 123) #doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
MockcachedKeyLengthError: Key length is > ...

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
# breaks python 2 tests
# from __future__ import unicode_literals

import datetime
import copy

try:
    unicode
except NameError:
    unicode = None.__class__

__author__ = "Hong Minhee <http://hongminhee.org/>"
__maintainer__ = __author__
__email__ = "dahlia@lunant.com"
__copyright__ = "Copyright (c) 2010-2016 Lunant <http://lunant.com/>"
__license__ = "MIT License"
__version__ = "1.1.0"


SERVER_MAX_KEY_LENGTH = 250
SERVER_MAX_VALUE_LENGTH = 1024*1024


class Client(object):
    """Dictionary-based mock memcached client. Almost like other Python
    memcached client libraries' interface.

    """

    __slots__ = ("dictionary", "__dict__")

    # exceptions for Client
    class MockcachedKeyError(Exception):
        pass
    class MockcachedKeyLengthError(MockcachedKeyError):
        pass
    class MockcachedKeyCharacterError(MockcachedKeyError):
        pass
    class MockcachedKeyNoneError(MockcachedKeyError):
        pass
    class MockcachedKeyTypeError(MockcachedKeyError):
        pass
    class MockcachedStringEncodingError(Exception):
        pass

    def __init__(self, *args, **kwargs):
        """Does nothing. It takes no or any arguments, but they are just for
        compatibility so ignored.

        """
        self.dictionary = {}

    def set_servers(self, servers):
        """Does nothing, like `__init__`. Just for compatibility."""
        pass

    def disconnect_all(self):
        """Does nothing, like `__init__`. Just for compatibility."""
        pass

    def delete(self, key, time=0):
        """Deletes the `key` from the dictionary."""
        key = check_key(key)
        if key in self.dictionary:
            if int(time) < 1:
                del self.dictionary[key]
                return 1
            self.set(key, self.dictionary[key], time)
        return 0

    def incr(self, key, delta=1):
        """Increments an integer by the `key`."""
        key = check_key(key)
        try:
            value, exp = self.dictionary[key]
        except KeyError:
            return
        else:
            value = int(value) + delta
            self.dictionary[key] = value, exp
            return value

    def decr(self, key, delta=1):
        """Decrements an integer by the `key`."""
        key = check_key(key)
        return self.incr(key, -delta)

    def append(self, key, val):
        """Append the `val` to the end of the existing `key`'s value.
        It works only when there is the key already.

        """
        key = check_key(key)
        try:
            self.dictionary[key] = str(self.dictionary[key][0]) + val, \
                                   self.dictionary[key][1]
        except KeyError:
            return 0
        else:
            return 1

    def prepend(self, key, val):
        """Prepends the `val` to the beginning of the existing `key`'s value.
        It works only when there is the key already.

        """
        key = check_key(key)
        try:
            self.dictionary[key] = val + str(self.dictionary[key][0]), \
                                   self.dictionary[key][1]
        except KeyError:
            return 0
        else:
            return 1

    def add(self, key, val, time=0):
        """Adds a new `key` with the `val`. Almost like `set` method,
        but it stores the value only when the `key` doesn't exist already.

        """
        key = check_key(key)
        if key in self.dictionary:
            return 0
        return self.set(key, val, time)

    def replace(self, key, val, time=0):
        """Replaces the existing `key` with `val`. Almost like `set` method,
        but it store the value only when the `key` already exists.

        """
        key = check_key(key)
        if key not in self.dictionary:
            return 0
        return self.set(key, val, time)

    def set(self, key, val, time=0):
        """Sets the `key` with `val`."""
        key = check_key(key)
        if not time:
            time = None
        elif time < 60 * 60 * 24 * 30:
            time = datetime.datetime.now() + datetime.timedelta(0, time)
        else:
            time = datetime.datetime.fromtimestamp(time)
        self.dictionary[key] = val, time
        return 1

    def set_multi(self, mapping, time=0, key_prefix=b''):
        """Sets all the key-value pairs in `mapping`. If `key_prefix` is
        given, it is prepended to all keys in `mapping`."""
        if not isinstance(key_prefix, bytes):
            try:
                key_prefix = key_prefix.encode('ascii')
            except Exception:
                key_prefix = b''
        for key, value in mapping.items():
            key = check_key(key)
            self.set(b''.join((key_prefix, key)), value, time)
        return []

    def get(self, key):
        """Retrieves a value of the `key` from the internal dictionary."""
        key = check_key(key)
        try:
            val, exptime = self.dictionary[key]
        except KeyError:
            return
        else:
            if exptime and exptime < datetime.datetime.now():
                del self.dictionary[key]
                return
            return copy.deepcopy(val)

    def get_multi(self, keys, key_prefix=b''):
        """Retrieves values of the `keys` at once from the internal
        dictionary. If `key_prefix` is given, it is prepended to all
        keys before retrieving them.
        """
        if not isinstance(key_prefix, bytes):
            try:
                key_prefix = key_prefix.encode('ascii')
            except Exception:
                key_prefix = b''
        dictionary = self.dictionary

        pairs = []
        for key in keys:
            key = check_key(key)
            prefixed_key = b''.join((key_prefix, key))
            if prefixed_key in dictionary:
                pairs.append((key, self.dictionary[prefixed_key]))
        now = datetime.datetime.now
        return dict((key, copy.deepcopy(value)) for key, (value, exp) in pairs
                                                if not exp or exp > now())

    def delete_multi(self, keys):
        """Deletes the `keys` from the dictionary

        """
        result = True
        for key in keys:
            key = check_key(key)
            result = result and self.delete(key)
        return result

    def flush_all(self):
        """Clear the internal dictionary"""
        self.dictionary.clear()

    def __repr__(self):
        modname = "" if __name__ == "__main__" else __name__ + "."
        return "<%sClient %r>" % (modname, self.dictionary)

    def __len__(self):
        return len(self.dictionary)

    def __contains__(self, key):
        try:
            key = check_key(key)
        except MockcachedKeyError:
            pass
        return key in self.dictionary


def check_key(key, key_extra_len=0):
    """Checks sanity of key. Fails if:
        Key length is > SERVER_MAX_KEY_LENGTH (Raises MockcachedKeyLengthError).
        Contains control characters  (Raises MockcachedKeyCharacterError).
        Is not a string (Raises MockcachedKeyTypeError)
        Is None (Raises MockcachedKeyNoneError)
    """
    if type(key) == tuple:
        key = key[1]
    if not key:
        raise Client.MockcachedKeyNoneError('Key is None')

    if isinstance(key, unicode):
        raise Client.MockcachedKeyTypeError(
            "Key must be bytes()'s, not unicode")
    if not isinstance(key, bytes):
        try:
            key = key.encode('ascii')
        except Exception:
            raise Client.MockcachedKeyTypeError(
                'Key must be encodable to ascii')

    if len(key) + key_extra_len > SERVER_MAX_KEY_LENGTH:
        raise Client.MockcachedKeyLengthError("Key length is > %s" % \
                                                 SERVER_MAX_KEY_LENGTH)
    for char in key:
        if isinstance(char, str):
            char = ord(char)
        if char < 33 or char == 127:
            raise Client.MockcachedKeyCharacterError("Control characters not "
                                                     "allowed")
    return key
