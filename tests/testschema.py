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
__author__ = "Santiago Blaumann"
__email__ = "santiago.blaumann@rcsb.org"
__license__ = "BSD 3-Clause"

import logging
import platform
import resource
import time
import unittest

from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.schema import _load_json_schema, _load_chem_schema, _fetch_schema
from rcsbsearchapi.const import STRUCTURE_ATTRIBUTE_SCHEMA_URL, CHEMICAL_ATTRIBUTE_SCHEMA_URL


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s]-%(module)s.%(funcName)s: %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


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

    def testSchema(self):
        ok = attrs.rcsb_id.attribute == "rcsb_id"
        self.assertTrue(ok)
        ok2 = attrs.rcsb_struct_symmetry.symbol.attribute == "rcsb_struct_symmetry.symbol"
        self.assertTrue(ok2)
        logger.info("Schema test results: ok : (%r), ok2: (%r)", ok, ok2)

    def testSchemaVersion(self):
        # Check structure attribute schema version
        webSchema = _fetch_schema(STRUCTURE_ATTRIBUTE_SCHEMA_URL)
        localSchema = _load_json_schema()
        webVer = webSchema.get("$comment").split()[-1]
        localVer = localSchema.get("$comment").split()[-1]  
        ok = len(localVer.split(".")) == 3 and len(webVer.split(".")) == 3
        self.assertTrue(ok)
        logger.info("ok is %r", ok)
        webVerMajorMinor = float(".".join(webVer.split(".")[0:2]))
        localVerMajorMinor = float(".".join(localVer.split(".")[0:2]))
        ok = localVerMajorMinor <= webVerMajorMinor and localVerMajorMinor >= webVerMajorMinor - 0.10
        logger.info("ok is %r", ok)
        self.assertTrue(ok)
        logger.info("Metadata schema tests results: local version (%r) and web version (%s)", localVer, webVer)
        # Check chemical attribute schema version
        webSchema = _fetch_schema(CHEMICAL_ATTRIBUTE_SCHEMA_URL)
        localSchema = _load_chem_schema()
        webVer = webSchema.get("$comment").split()[-1]
        localVer = localSchema.get("$comment").split()[-1]
        ok = len(localVer.split(".")) == 3 and len(webVer.split(".")) == 3
        self.assertTrue(ok)
        logger.info("ok is %r", ok)
        webVerMajorMinor = float(".".join(webVer.split(".")[0:2]))
        localVerMajorMinor = float(".".join(localVer.split(".")[0:2]))
        ok = localVerMajorMinor <= webVerMajorMinor and localVerMajorMinor >= webVerMajorMinor - 0.10
        logger.info("ok is %r", ok)
        self.assertTrue(ok)
        logger.info("Chemical schema tests results: local version (%r) and web version (%s)", localVer, webVer)

    def testFetchSchema(self):
        #check fetching of structure attribute schema
        fetchSchema = _fetch_schema(STRUCTURE_ATTRIBUTE_SCHEMA_URL)
        ok = fetchSchema != None
        logger.info("ok is %r", ok)
        self.assertTrue(ok)        
        fetchSchema = _fetch_schema(CHEMICAL_ATTRIBUTE_SCHEMA_URL)
        ok = fetchSchema != None
        logger.info("ok is %r", ok)
        self.assertTrue(ok)
        errorURL = "https://httpbin.org/status/404"
        fetchSchema = _fetch_schema(errorURL)
        ok = fetchSchema == None
        logger.info("ok is %r", ok)
        self.assertTrue(ok)

def buildSchema():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SchemaTests("testSchema"))
    suiteSelect.addTest(SchemaTests("testSchemaVersion"))
    suiteSelect.addTest(SchemaTests("testFetchSchema"))

    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSchema()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
