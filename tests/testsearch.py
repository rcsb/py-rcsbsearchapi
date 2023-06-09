##
# File:    testsearch.py
# Author:  Spencer Bliven/Santiago Blaumann
# Date:    6/7/23
# Version: 0.001
#
# Update:
#
#
##
"""
Tests for all functions of the search file.
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
import requests

from rcsbsearchapi import Attr, Group, Session, Terminal, TextQuery, Value
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import PartialQuery
from itertools import islice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.__startTime = time.time()
        logger.info("Starting %s at %s", self.id(), time.strftime("%Y %m %d %H:%M:%S", time.localtime()))

    def tearDown(self):
        unitS = "MB" if platform.system() == "Darwin" else "GB"
        rusageMax = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        logger.info("Maximum resident memory size %.4f %s", rusageMax / 10 ** 6, unitS)
        endTime = time.time()
        logger.info("Completed %s at %s (%.4f seconds)", self.id(), time.strftime("%Y %m %d %H:%M:%S", time.localtime()), endTime - self.__startTime)

    def testBuildSearch(self):
        #Test construction
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
        q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "5T89"])

        both = q1 & q2
        ok = isinstance(both, Group)
        self.assertTrue(ok)
        ok = both.operator == "and"
        self.assertTrue(ok)
        ok = both.nodes[0] == q1
        self.assertTrue(ok)
        ok = both.nodes[1] == q2

        either = q1 | q2
        ok = isinstance(either, Group)
        self.assertTrue(ok)
        ok = either.operator == "or"
        self.assertTrue(ok)
        ok = either.nodes[0] == q1
        self.assertTrue(ok)
        ok = either.nodes[1] == q2
        self.assertTrue(ok)

        # test single_query
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
        session = Session(Group("and", [q1]))
        result = session._single_query()
        ok = result is not None
        self.assertTrue(ok)

        # test iquery
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
        session = Session(q1)
        result = session.iquery()
        ok = len(result) == 2
        self.assertTrue(ok)

        #test iterable
        ids = ["4HHB", "2GS2"]
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids)
        result = set(q1())
        ok = len(result) == 2
        ok2 = result == set(ids)
        self.assertTrue(ok)
        self.assertTrue(ok2)

        #test_inv
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "exact_match", "5T89")
        q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
        q = ~q1
        q22 = ~q2
        # Lots of results
        first = next(iter(q()))
        second = iter(q22())
        #print(first)
        ok = first is not None
        self.assertTrue(ok)
        ok = first != "5T89"
        self.assertTrue(ok)

        #test xor
        ids1 = ["5T89", "2GS2"]
        ids2 = ["4HHB", "2GS2"]
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids1)
        q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids2)
        q = q1 ^ q2
        result = set(q())
        ok = len(result) == 2
        self.assertTrue(ok)
        ok = result == {ids1[0], ids2[0]}
        self.assertTrue(ok)

        #test pagination
        ids = ["4HHB", "2GS2", "5T89", "1TIM"]
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids)

        # 2+2 results
        session = Session(q1, rows=2)
        result = set(session)
        ok = len(result) == 4
        self.assertTrue(ok)
        ok = result == set(ids)
        self.assertTrue(ok)

        # 3+1 results
        session = Session(q1, rows=3)
        result = set(session)
        ok = len(result) == 4
        self.assertTrue(ok)
        ok = result == set(ids)
        self.assertTrue(ok)

        # 1ABC will never be a valid ID
        q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["1ABC"])
        session = Session(q2)
        result = set(session)
        ok = len(result) == 0
        self.assertTrue(ok)

        # test errors

        # Malformed
        # I want to rewrite this 
        # q1 = Terminal("invalid_identifier", "exact_match", "ERROR")
        # session = Session(q1)
        # try:
        #     set(session)
        #     assert False, "Should raise error"
        # except requests.HTTPError:
        #     pass

        #example test
        """'Biological Assembly Search' from http://search.rcsb.org/#examples
        (Also used in the README)
        """
        # Create terminals for each query
        q1 = TextQuery('"heat-shock transcription factor"')
        q2 = attrs.rcsb_struct_symmetry.symbol == "C2"
        q3 = attrs.rcsb_struct_symmetry.kind == "Global Symmetry"
        q4 = attrs.rcsb_entry_info.polymer_entity_count_DNA >= 1

        # combined using bitwise operators (&, |, ~, etc)
        query = q1 & q2 & q3 & q4  # AND of all queries

        results = set(query("assembly"))
        ok = len(results) > 0  # 14 results 2020-06
        self.assertTrue(ok)
        ok = "1FYL-1" in results
        self.assertTrue(ok)

        # Fluent syntax
        query2 = (
            TextQuery('"heat-shock transcription factor"')
            .and_("rcsb_struct_symmetry.symbol")
            .exact_match("C2")
            .and_("rcsb_struct_symmetry.kind")
            .exact_match("Global Symmetry")
            .and_("rcsb_entry_info.polymer_entity_count_DNA")
            .greater_or_equal(1)
        )

        ok = query2 == query
        self.assertTrue(ok)

        results = set(query2.exec("assembly"))
        ok = len(results) > 0  # 14 results 2020-06
        self.assertTrue(ok)
        ok = "1FYL-1" in results
        self.assertTrue(ok)

        # example 2
        "'X-Ray Structures Search' from http://search.rcsb.org/#examples"
        q = (
            TextQuery('"thymidine kinase"')
            & Terminal(
                "rcsb_entity_source_organism.taxonomy_lineage.name",
                "exact_match",
                "Viruses",
            )
            & Terminal(
                "exptl.method",
                "exact_match",
                "X-RAY DIFFRACTION",
            )
            & Terminal(
                "rcsb_entry_info.resolution_combined",
                "less_or_equal",
                2.5,
            )
            & Terminal("rcsb_entry_info.nonpolymer_entity_count", "greater", 0)
        )

        results = set(q("entry"))
        ok = len(results) > 0  # 224 results 2020-06
        self.assertTrue(ok)
        ok = "1KI6" in results
        self.assertTrue(ok)

        #test attribute
        attr = Attr("attr")

        term = attr == "value"
        ok = isinstance(term, Terminal)
        self.assertTrue(ok)
        ok = term.operator == "exact_match"
        self.assertTrue(ok)

        term = "value" == attr
        ok = isinstance(term, Terminal)
        self.assertTrue(ok)
        ok = term.operator == "exact_match"
        self.assertTrue(ok)

        term = Value("value") == attr
        ok = isinstance(term, Terminal)
        self.assertTrue(ok)
        ok = term.operator == "exact_match"
        self.assertTrue(ok)

        #test freetext
        query = TextQuery("tubulin")
        results = set(query())
        ok = len(results) > 0
        self.assertTrue(ok)

        #test partial_query
        query = Attr("a").equals("aval").and_("b")

        ok = isinstance(query, PartialQuery)
        self.assertTrue(ok)

        query = query.exact_match("bval")

        ok = isinstance(query, Group)
        self.assertTrue(ok)
        ok = query.operator == "and"
        self.assertTrue(ok)
        ok = len(query.nodes) == 2
        self.assertTrue(ok)
        ok = query.nodes[0].attribute == "a"
        self.assertTrue(ok)
        ok = query.nodes[0].operator == "equals"
        self.assertTrue(ok)
        ok = query.nodes[0].value == "aval"
        self.assertTrue(ok)
        ok = query.nodes[1].attribute == "b"
        self.assertTrue(ok)
        ok = query.nodes[1].operator == "exact_match"
        self.assertTrue(ok)
        ok = query.nodes[1].value == "bval"

        query = query.and_(Attr("c") < 5)
        ok = len(query.nodes) == 3
        self.assertTrue(ok)
        ok = query.nodes[2].attribute == "c"
        self.assertTrue(ok)
        ok = query.nodes[2].operator == "less"
        self.assertTrue(ok)
        ok = query.nodes[2].value == 5
        self.assertTrue(ok)

        query = query.or_("d")

        ok = isinstance(query, PartialQuery)
        self.assertTrue(ok)
        ok = query.attr == Attr("d")
        self.assertTrue(ok)
        ok = query.operator == "or"
        self.assertTrue(ok)

        query = query == "dval"
        ok = isinstance(query, Group)
        self.assertTrue(ok)
        ok = query.operator == "or"
        self.assertTrue(ok)
        ok = len(query.nodes) == 2
        self.assertTrue(ok)

        ok = isinstance(query.nodes[0], Group)
        self.assertTrue(ok)
        ok = query.nodes[1].attribute == "d"
        self.assertTrue(ok)
        ok = query.nodes[1].operator == "exact_match"
        self.assertTrue(ok)
        ok = query.nodes[1].value == "dval"
        self.assertTrue(ok)

        #test operators
        q1 = attrs.rcsb_id.in_(["4HHB", "2GS2"])
        results = list(q1())
        ok = len(results) == 2
        self.assertTrue(ok)

        q1 = attrs.citation.rcsb_authors.contains_words("kisko bliven")
        results = list(q1())
        ok = results[0] == "5T89"  # first hit has both authors
        self.assertTrue(ok)
        ok = "3V6B" in results  # only a single author

        q1 = attrs.citation.rcsb_authors.contains_phrase("kisko bliven")
        results = list(q1())
        ok = len(results) == 0
        self.assertTrue(ok)

        q1 = attrs.struct.title.contains_phrase(
            "VEGF-A in complex with VEGFR-1 domains D1-6"
        )
        results = list(q1())
        ok = "5T89" in results
        self.assertTrue(ok)

        q1 = attrs.rcsb_struct_symmetry.type.exact_match("Asymmetric")
        results = list(islice(q1(), 5))
        ok = len(results) == 5
        self.assertTrue(ok)

        q1 = attrs.rcsb_struct_symmetry.type.exact_match("symmetric")
        results = list(islice(q1(), 5))
        ok = len(results) == 0
        self.assertTrue(ok)

    def testLargePagination(self):  # Give each test a unique name (and remember to add to suiteSelect at bottom of script)
        """Test server throttling (avoidance of 429s) - using generic text query with many results to paginate over"""
        # Add description in doc string (^) -- ends up showing up in Azure logs
        try:
            q1 = TextQuery("coli")
            resultL = list(q1())
            ok = len(resultL) > 100000  # Get OK value for success or failure, using rational conditions
            logger.info("Large search resultL length (%d) ok (%r)", len(resultL), ok)  # Logging added (obviously don't log all 100k results...)
        except requests.exceptions.HTTPError:
            ok = False
        self.assertTrue(ok)  # end each test with this


def buildSearch():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SearchTests("testBuildSearch"))
    suiteSelect.addTest(SearchTests("testLargePagination"))
    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSearch()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
