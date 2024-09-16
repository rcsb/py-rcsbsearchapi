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
from rcsbsearchapi import SCHEMA
from rcsbsearchapi.const import STRUCTURE_ATTRIBUTE_SCHEMA_URL, CHEMICAL_ATTRIBUTE_SCHEMA_URL, STRUCTURE_ATTRIBUTE_SCHEMA_FILE, CHEMICAL_ATTRIBUTE_SCHEMA_FILE


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
        # Check structure attribute schema version
        webSchema = SCHEMA._fetch_schema(STRUCTURE_ATTRIBUTE_SCHEMA_URL)
        localSchema = SCHEMA._load_json_schema(STRUCTURE_ATTRIBUTE_SCHEMA_FILE)
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
        webSchema = SCHEMA._fetch_schema(CHEMICAL_ATTRIBUTE_SCHEMA_URL)
        localSchema = SCHEMA._load_json_schema(CHEMICAL_ATTRIBUTE_SCHEMA_FILE)
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
        # check fetching of structure attribute schema
        fetchSchema = SCHEMA._fetch_schema(STRUCTURE_ATTRIBUTE_SCHEMA_URL)
        ok = fetchSchema is not None
        logger.info("ok is %r", ok)
        self.assertTrue(ok)
        fetchSchema = SCHEMA._fetch_schema(CHEMICAL_ATTRIBUTE_SCHEMA_URL)
        ok = fetchSchema is not None
        logger.info("ok is %r", ok)
        self.assertTrue(ok)
        errorURL = "https://httpbin.org/status/404"
        fetchSchema = SCHEMA._fetch_schema(errorURL)
        ok = fetchSchema is None
        logger.info("ok is %r", ok)
        self.assertTrue(ok)

    def testRcsbAttrs(self):
        with self.subTest(msg="1. Check type and descriptions exist for attributes"):
            for attr in attrs:
                attr_dict = vars(attr)
                desc = attr_dict["description"]
                self.assertIsNotNone(desc)

        with self.subTest(msg="2. Check searching for attribute details"):
            attr_details = attrs.get_attribute_details("drugbank_info.drug_groups")
            for obj_attr in ["attribute", "type", "description"]:
                self.assertIn(obj_attr, vars(attr_details).keys())

            # special case because rcsb_id is in both structure and chemical attributes
            attr_dict = vars(attrs.get_attribute_details("rcsb_id"))
            self.assertIsInstance(attr_dict["type"], list)
            self.assertIsInstance(attr_dict["description"], list)

            attr_details = attrs.get_attribute_details("foo")
            self.assertIsNone(attr_details)


def buildSchema():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SchemaTests("testSchema"))
    suiteSelect.addTest(SchemaTests("testSchemaVersion"))
    suiteSelect.addTest(SchemaTests("testFetchSchema"))
    suiteSelect.addTest(SchemaTests("testRcsbAttrs"))

    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSchema()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
