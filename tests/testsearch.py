##
# File:    testsearch.py
# Author:  Santiago Blaumann
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
__author__ = "Santiago Blaumann"
__email__ = "santiago.blaumann@rcsb.org"
__license__ = "BSD 3-Clause"

import logging
import platform
import resource
import time
import unittest
from itertools import islice
import requests

from rcsbsearchapi import Attr, Group, Session, Terminal, TextQuery, Value
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import PartialQuery


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]-%(module)s.%(funcName)s: %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

    def testConstruction(self):
        """Test the construction of queries, and check that the query is what
        you'd expect. """
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
        logger.info("Construction test results: ok : (%r)", ok)

    def testSingleQuery(self):
        """Test firing off a single query, making sure the result is not None."""
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
        session = Session(Group("and", [q1]))
        result = session._single_query()  # pylint takes issue with this as this is a protected method
        ok = result is not None
        self.assertTrue(ok)
        logger.info("Single query test results: ok : (%r)", ok)

    def testIquery(self):
        """Tests the iquery function, which evaluates a query with a progress bar.
        The progress bar requires tqdm to run. """
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
        session = Session(q1)
        result = session.iquery()
        ok = len(result) == 2
        self.assertTrue(ok)
        logger.info("Iquery test results: ok : (%r)", ok)

    def testIterable(self):
        """Take a query, make it iterable and then test that its attributes remain unchanged as a result. """
        ids = ["4HHB", "2GS2"]
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids)
        result = set(q1())
        ok = len(result) == 2
        ok2 = result == set(ids)
        self.assertTrue(ok)
        self.assertTrue(ok2)
        logger.info("Iterable test results: ok : (%r), ok2 = (%r)", ok, ok2)

    def testInversion(self):
        """Test the overloaded inversion operator in a query. """
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "exact_match", "5T89")
        q3 = ~q1
        # Lots of results
        first = next(iter(q3()))
        # print(first)
        ok = first is not None
        self.assertTrue(ok)
        ok = first != "5T89"
        self.assertTrue(ok)
        logger.info("Inversion test results: ok : (%r)", ok)

    def testXor(self):
        """Test the overloaded XOR operator in a query. """
        ids1 = ["5T89", "2GS2"]
        ids2 = ["4HHB", "2GS2"]
        q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids1)
        q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids2)
        q3 = q1 ^ q2  # overloaded xor operator used on results.
        result = set(q3())
        ok = len(result) == 2
        self.assertTrue(ok)
        ok = result == {ids1[0], ids2[0]}
        self.assertTrue(ok)
        logger.info("Xor test results: ok : (%r)", ok)

    def testPagination(self):
        """Test the pagination of the query. Note that this test differs from
        the large pagination tests below, which test avoiding a 429 error,
        while this exists to make sure the feature behaves as intended. """
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
        logger.info("Pagination test results: ok : (%r)", ok)

    def testMalformedQuery(self):
        """Attempt to make an invalid, malformed query. Upon finding an error,
        catch the error and pass, continuing tests. An exception is only thrown
        if the query somehow completes successfully. """
        q1 = Terminal("invalid_identifier", "exact_match", "ERROR")
        session = Session(q1)
        try:
            set(session)
            ok = False
        except requests.HTTPError:
            ok = True
        self.assertTrue(ok)
        logger.info("Malformed query test results: ok : (%r)", ok)

    def exampleQuery1(self):
        """Make an example query, and make sure it performs correctly.
        This example is pulled directly from the 'Biological Assembly Search'
        example found at http://search.rcsb.org/#examples"""
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
        logger.info("Example1 Test Results: length: (%d) ok: (%r)", len(results), ok)

    def exampleQuery2(self):
        """Make another example query, and make sure that it performs successfully. """
        q1 = (
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

        results = set(q1("entry"))
        ok = len(results) > 0  # 224 results 2020-06
        self.assertTrue(ok)
        ok = "1KI6" in results  # make sure that the right information is pulled
        self.assertTrue(ok)
        logger.info("Example2 Test Results: length: (%d) ok: (%r)", len(results), ok)

    def testAttribute(self):
        """Test the attributes - make sure that they are assigned correctly, etc. """
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
        logger.info("Attribute tests results: ok: (%d)", ok)

    def testFreeText(self):
        """Test the free text search function"""
        query = TextQuery("tubulin")  # make a TextQuery
        results = set(query())  # make it an iterable set
        ok = len(results) > 0  # assert the result isn't blank
        self.assertTrue(ok)
        logger.info("FreeText test results: length (%d) ok (%r)", len(results), ok)

    def testPartialQuery(self):
        """Test the ability to perform partial queries. """
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
        logger.info("Partial Query results: ok: (%r)", ok)

    def testOperators(self):
        """Test operators such as contain and in. """
        q1 = attrs.rcsb_id.in_(["4HHB", "2GS2"])  # test in
        results = list(q1())
        ok = len(results) == 2
        logger.info("In search results length: (%d) ok: (%r)", len(results), ok)
        self.assertTrue(ok)

        q1 = attrs.citation.rcsb_authors.contains_words("kisko bliven")  # test contains_Words
        results = list(q1())
        ok = results[0] == "5T89"  # first hit has both authors
        self.assertTrue(ok)
        ok = "3V6B" in results  # only a single author
        logger.info("Aurhor contains words search results: (%s) ok: (%r)", "3V6B", ok)

        q1 = attrs.citation.rcsb_authors.contains_phrase("kisko bliven")  # test contains_phrase
        results = list(q1())
        ok = len(results) == 0
        self.assertTrue(ok)
        logger.info("Author contains phrase results: phrase: (%s) length: (%d) ok: (%r)", "kikso bliven", len(results), ok)

        q1 = attrs.struct.title.contains_phrase(
            "VEGF-A in complex with VEGFR-1 domains D1-6"
        )
        results = list(q1())
        ok = "5T89" in results
        self.assertTrue(ok)
        logger.info("Sctructure title contains phrase: (%s), (%s) in results, ok: (%r)", "VEGF-A in complex with VEGFR-1 domains D1-6", "5T89", ok)

        q1 = attrs.rcsb_struct_symmetry.type.exact_match("Asymmetric")
        results = list(islice(q1(), 5))
        ok = len(results) == 5
        self.assertTrue(ok)
        logger.info("Sctructure type exact match: symmetry type: (%s), length: (%d), ok: (%r)", "Asymmetric", len(results), ok)

        q1 = attrs.rcsb_struct_symmetry.type.exact_match("symmetric")
        results = list(islice(q1(), 5))
        ok = len(results) == 0
        self.assertTrue(ok)
        logger.info("Sctructure type exact match: symmetry type: (%s), length: (%d), ok: (%r)", "symmetric", len(results), ok)

    def testLargePagination(self):
        """Test server throttling (avoidance of 429s) - using generic text query with many results to paginate over"""
        try:
            q1 = TextQuery("coli")
            resultL = list(q1())
            ok = len(resultL) > 100000
            logger.info("Large search resultL length: (%d) ok: (%r)", len(resultL), ok)
        except requests.exceptions.HTTPError:
            ok = False
        self.assertTrue(ok)


def buildSearch():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SearchTests("testConstruction"))
    suiteSelect.addTest(SearchTests("testLargePagination"))
    suiteSelect.addTest(SearchTests("testOperators"))
    suiteSelect.addTest(SearchTests("testPartialQuery"))
    suiteSelect.addTest(SearchTests("testFreeText"))
    suiteSelect.addTest(SearchTests("testAttribute"))
    suiteSelect.addTest(SearchTests("exampleQuery2"))
    suiteSelect.addTest(SearchTests("exampleQuery1"))
    suiteSelect.addTest(SearchTests("testMalformedQuery"))
    suiteSelect.addTest(SearchTests("testPagination"))
    suiteSelect.addTest(SearchTests("testXor"))
    suiteSelect.addTest(SearchTests("testInversion"))
    suiteSelect.addTest(SearchTests("testIterable"))
    suiteSelect.addTest(SearchTests("testIquery"))
    suiteSelect.addTest(SearchTests("testSingleQuery"))
    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSearch()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
