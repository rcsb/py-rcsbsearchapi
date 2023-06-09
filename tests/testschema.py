##
# File:    testschema.py
# Author:  Spencer Bliven/Santiago Blaumann
# Date:    6/7/23
# Version: 1.0
#
# Update:
#
#
##
"""
Tests for all functions of the schema file.
"""

__docformat__ = "google en"
__author__ = "Spencer Bliven/Santiago Blaumann"
__email__ = "santiago.blaumann@rcsb.org"
__license__ = "BSD 3-Clause"

import logging
import platform
import resource
import time
import unittest

from rcsbsearchapi import rcsb_attributes as attrs


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.__startTime = time.time()
        logger.info("Starting %s at %s", self.id(), time.strftime("%Y %m %d %H:%M:%S", time.localtime()))

    def tearDown(self):
        unitS = "MB" if platform.system() == "Darwin" else "GB"
        rusageMax = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        logger.info("Maximum resident memory size %.4f %s", rusageMax / 10 ** 6, unitS)
        endTime = time.time()
        logger.info("Completed %s at %s (%.4f seconds)", self.id(), time.strftime("%Y %m %d %H:%M:%S", time.localtime()), endTime - self.__startTime)

    def testBuildSchema(self):
        ok = attrs.rcsb_id.attribute == "rcsb_id"
        self.assertTrue(ok)

        ok = attrs.rcsb_struct_symmetry.symbol.attribute == "rcsb_struct_symmetry.symbol"
        self.assertTrue(ok)


def buildSchema():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SchemaTests("testBuildSchema"))
    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSchema()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
