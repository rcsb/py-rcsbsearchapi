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
from rcsbsearchapi.schema import _load_json_schema, _load_chem_schema, _download_schema
from rcsbsearchapi.const import METADATA_SCHEMA_URL, CHEMICAL_SCHEMA_URL


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]-%(module)s.%(funcName)s: %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        webSchema = _download_schema(METADATA_SCHEMA_URL)
        localSchema = _load_json_schema()
        ok = webSchema == localSchema
        self.assertTrue(ok)
        logger.info("Metadata schema tests results: local version (%r) and web version (%s)", localSchema.get("$comment"), webSchema.get("$comment"))

        webSchema = _download_schema(CHEMICAL_SCHEMA_URL)
        localSchema = _load_chem_schema()
        ok = webSchema == localSchema
        self.assertTrue(ok)
        logger.info("Chemical schema tests results: local version (%r) and web version (%s)", localSchema.get("$comment"), webSchema.get("$comment"))


def buildSchema():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SchemaTests("testSchema"))
    suiteSelect.addTest(SchemaTests("testSchemaVersion"))
    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSchema()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
