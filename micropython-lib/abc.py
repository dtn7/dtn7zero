"""
Dummy module for micropython. Not at all CPython compliant. Just suppresses import errors.

Useful if a class is marked abstract, but does not use any other abc functionality.

inspired by the pycopy project: https://github.com/pfalcon/pycopy-lib/blob/master/abc/abc.py
"""


class ABC:
    pass


def abstractmethod(f):
    return f
