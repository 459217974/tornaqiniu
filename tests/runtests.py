#-*- coding:utf -*-

import unittest
import tornado.testing
TEST_MODULES=[
	'tornaqiniu.tests.test_resource_load'
]

def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)

if __name__ == '__main__':
     tornado.testing.main()
