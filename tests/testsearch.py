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
from rcsbsearchapi.const import CHEMICAL_ATTRIBUTE_SEARCH_SERVICE, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE
from rcsbsearchapi import Attr, Group, Session, TextQuery, Value
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import PartialQuery, Terminal, AttributeQuery, SequenceQuery, SeqMotifQuery


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
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["4HHB", "2GS2"])
        q2 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["4HHB", "5T89"])

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
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["4HHB", "2GS2"])
        session = Session(Group("and", [q1]))
        result = session._single_query()  # pylint takes issue with this as this is a protected method
        print(result)
        ok = result is not None
        self.assertTrue(ok)
        logger.info("Single query test results: ok : (%r)", ok)

    def testIquery(self):
        """Tests the iquery function, which evaluates a query with a progress bar.
        The progress bar requires tqdm to run. """
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["4HHB", "2GS2"])
        session = Session(q1)
        result = session.iquery()
        ok = len(result) == 2
        self.assertTrue(ok)
        logger.info("Iquery test results: ok : (%r)", ok)

    def testIterable(self):
        """Take a query, make it iterable and then test that its attributes remain unchanged as a result. """
        ids = ["4HHB", "2GS2"]
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=ids)
        result = set(q1())
        ok = len(result) == 2
        ok2 = result == set(ids)
        self.assertTrue(ok)
        self.assertTrue(ok2)
        logger.info("Iterable test results: ok : (%r), ok2 = (%r)", ok, ok2)

    def testInversion(self):
        """Test the overloaded inversion operator in a query. """
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="exact_match", value="5T89")
        q3 = ~q1
        # Lots of results
        first = next(iter(q3()))
        # print(first)
        ok = first is not None
        self.assertTrue(ok)
        ok = first != "5T89"
        self.assertTrue(ok)
        logger.info("Inversion test results: ok : (%r)", ok)
        # Test that seqqueries fail as intended:
        q4 = SequenceQuery("VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR")
        ok = False
        try:
            _ = ~q4
        except TypeError:
            ok = True
        self.assertTrue(ok)
        logger.info("Inversion failed on SequenceQuery: ok : (%r)", ok)

    def testXor(self):
        """Test the overloaded XOR operator in a query. """
        ids1 = ["5T89", "2GS2"]
        ids2 = ["4HHB", "2GS2"]
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=ids1)
        q2 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=ids2)
        q3 = q1 ^ q2  # overloaded xor operator used on results
        result = set(q3())
        ok = len(result) == 2
        self.assertTrue(ok)
        ok = result == {ids1[0], ids2[0]}
        self.assertTrue(ok)
        logger.info("Xor test results: ok : (%r)", ok)
        # Test that xor fails when used for seqqueries
        q4 = SequenceQuery("VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR")
        q5 = SequenceQuery("VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR")
        ok = False
        try:
            _ = q4 ^ q5  # this should fail as xor is not supported behavior for seq queries
        except TypeError:
            ok = True
        self.assertTrue(ok)
        logger.info("xor failed for seq queries: ok : (%r)", ok)

    def testPagination(self):
        """Test the pagination of the query. Note that this test differs from
        the large pagination tests below, which test avoiding a 429 error,
        while this exists to make sure the feature behaves as intended. """
        ids = ["4HHB", "2GS2", "5T89", "1TIM"]
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=ids)

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
        q2 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["1ABC"])
        session = Session(q2)
        result = set(session)
        ok = len(result) == 0
        self.assertTrue(ok)
        logger.info("Pagination test results: ok : (%r)", ok)

    def testMalformedQuery(self):
        """Attempt to make an invalid, malformed query. Upon finding an error,
        catch the error and pass, continuing tests. An exception is only thrown
        if the query somehow completes successfully. """
        q1 = AttributeQuery("invalid_identifier", operator="exact_match", value="ERROR")
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
        q1 = TextQuery("heat-shock transcription factor")
        q2 = attrs.rcsb_struct_symmetry.symbol == "C2"
        q3 = attrs.rcsb_struct_symmetry.kind == "Global Symmetry"
        q4 = attrs.rcsb_entry_info.polymer_entity_count_DNA >= 1

        # combined using bitwise operators (&, |, ~, etc)
        query = q1 & (q2 & q3 & q4)  # AND of all queries

        results = set(query("assembly"))
        ok = len(results) > 0  # 1657 results 2023-06
        self.assertTrue(ok)
        ok = "1FYL-1" in results
        self.assertTrue(ok)

        # Fluent syntax
        query2 = TextQuery("heat-shock transcription factor").and_(AttributeQuery("rcsb_struct_symmetry.symbol", "exact_match", "C2")
                                                                   .and_("rcsb_struct_symmetry.kind", STRUCTURE_ATTRIBUTE_SEARCH_SERVICE)
                                                                   .exact_match("Global Symmetry")
                                                                   .and_("rcsb_entry_info.polymer_entity_count_DNA", STRUCTURE_ATTRIBUTE_SEARCH_SERVICE)
                                                                   .greater_or_equal(1))
        ok = query2 == query
        self.assertTrue(ok)

        results = set(query2.exec("assembly"))
        ok = len(results) > 0  # 1657 results 2023-06
        self.assertTrue(ok)
        ok = "1FYL-1" in results
        self.assertTrue(ok)
        logger.info("Example1 Test Results: length: (%d) ok: (%r)", len(results), ok)

    def exampleQuery2(self):
        """Make another example query, and make sure that it performs successfully. """
        q1 = (
            TextQuery("thymidine kinase")
            & AttributeQuery(
                "rcsb_entity_source_organism.taxonomy_lineage.name",
                operator="exact_match",
                value="Viruses",
            )
            & AttributeQuery(
                "exptl.method",
                operator="exact_match",
                value="X-RAY DIFFRACTION",
            )
            & AttributeQuery(
                "rcsb_entry_info.resolution_combined",
                operator="less_or_equal",
                value=2.5,
            )
            & AttributeQuery("rcsb_entry_info.nonpolymer_entity_count", operator="greater", value=0)
        )
        results = set(q1("entry"))
        ok = len(results) > 0  # 1484 results 2023-06
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
        ok = term.params.get("operator") == "exact_match"
        self.assertTrue(ok)

        term = "value" == attr
        ok = isinstance(term, Terminal)
        self.assertTrue(ok)
        ok = term.params.get("operator") == "exact_match"
        self.assertTrue(ok)

        term = Value("value") == attr
        ok = isinstance(term, Terminal)
        self.assertTrue(ok)
        ok = term.params.get("operator") == "exact_match"
        self.assertTrue(ok)
        logger.info("Attribute tests results: ok: (%d)", ok)

    def testFreeText(self):
        """Test the free text search function"""
        query = TextQuery("tubulin")  # make a TextQuery
        results = list(query())  # make it an iterable set
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
        ok = query.nodes[0].params.get("attribute") == "a"
        self.assertTrue(ok)
        ok = query.nodes[0].params.get("operator") == "equals"
        self.assertTrue(ok)
        ok = query.nodes[0].params.get("value") == "aval"
        self.assertTrue(ok)
        ok = query.nodes[1].params.get("attribute") == "b"
        self.assertTrue(ok)
        ok = query.nodes[1].params.get("operator") == "exact_match"
        self.assertTrue(ok)
        ok = query.nodes[1].params.get("value") == "bval"

        query = query.and_(Attr("c") < 5)
        ok = len(query.nodes) == 3
        self.assertTrue(ok)
        ok = query.nodes[2].params.get("attribute") == "c"
        self.assertTrue(ok)
        ok = query.nodes[2].params.get("operator") == "less"
        self.assertTrue(ok)
        ok = query.nodes[2].params.get("value") == 5
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
        ok = query.nodes[1].params.get("attribute") == "d"
        self.assertTrue(ok)
        ok = query.nodes[1].params.get("operator") == "exact_match"
        self.assertTrue(ok)
        ok = query.nodes[1].params.get("value") == "dval"
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
        logger.info("Author contains words search results: (%s) ok: (%r)", "3V6B", ok)

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
        logger.info("Structure title contains phrase: (%s), (%s) in results, ok: (%r)", "VEGF-A in complex with VEGFR-1 domains D1-6", "5T89", ok)

        q1 = attrs.rcsb_struct_symmetry.type.exact_match("Asymmetric")
        results = list(islice(q1(), 5))
        ok = len(results) == 5
        self.assertTrue(ok)
        logger.info("Structure type exact match: symmetry type: (%s), length: (%d), ok: (%r)", "Asymmetric", len(results), ok)

        q1 = attrs.rcsb_struct_symmetry.type.exact_match("symmetric")
        results = list(islice(q1(), 5))
        ok = len(results) == 0
        self.assertTrue(ok)
        logger.info("Structure type exact match: symmetry type: (%s), length: (%d), ok: (%r)", "symmetric", len(results), ok)

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

    def testChemSearch(self):
        """Test the chemical attribute search using both the operator and
        fluent syntaxes. """
        q1 = attrs.drugbank_info.brand_names.contains_phrase("Tylenol")  # 111 results 19/06/23
        result = list(q1())
        ok = len(result) > 0
        self.assertTrue(ok)
        ok2 = "1TYL" in result
        logger.info("Chemical Search Operator Syntax: result length: (%d), ok: (%r), ok2: (%r)", len(result), ok, ok2)

        result = TextQuery("Hemoglobin")\
            .and_("chem_comp.name", CHEMICAL_ATTRIBUTE_SEARCH_SERVICE).contains_phrase("adenine")
        # result = set(result("assembly"))
        q1 = TextQuery("Hemoglobin")
        q2 = attrs.chem_comp.name.contains_phrase("adenine")
        result2 = q1 & q2
        # result2 = set(result2("assembly"))
        ok = result == result2  # check why this doesn't work tomorrow
        logger.info("result of first query:")
        logger.info(result)
        logger.info("result of second query:")
        logger.info(result2)
        self.assertTrue(ok)
        resultL = list(result2())
        ok2 = "6FJH" in resultL
        self.assertTrue(ok2)
        logger.info("Chemical Search Fluent Syntax: result length: (%d), ok: (%r), ok2: (%r)", len(resultL), ok, ok2)

    def testMismatch(self):
        """Negative test - test running a chemical attribute query but with structure attribute service type.
        Expected failure."""
        try:
            query = TextQuery('"hemoglobin"')\
                .and_("rcsb_chem_comp.name", STRUCTURE_ATTRIBUTE_SEARCH_SERVICE).contains_phrase("adenine")\
                .exec("assembly")
            resultL = list(query)
            ok = len(resultL) < 0  # set this to false as it should fail
        except requests.exceptions.HTTPError:
            ok = True
        self.assertTrue(ok)
        logger.info("Mismatch test: ok: (%r)", ok)

    def testCSMquery(self):
        """Test firing off a single query that includes Computed Structure Models. Making sure the result is not None"""
        q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["AF_AFO87296F1"])  # entry ID for specific computed structure model of hemoglobin
        session = Session(q1, return_content_type=["computational", "experimental"])
        result = session._single_query()
        ok = result is not None
        self.assertTrue(ok)
        logger.info("Single query test results with Computed Structure Models: ok : (%r)", ok)

        # Checks to see if result count changes when computed structure models included or not and if result count is expected
        q2 = AttributeQuery("rcsb_entity_source_organism.taxonomy_lineage.name", operator="contains_phrase", value="Arabidopsis thaliana")
        q2_length = len(list(q2(return_content_type=["experimental"])))
        q2_computational_length = len(list(q2(return_content_type=["computational", "experimental"])))
        ok = q2_length > 1900
        self.assertTrue(ok)
        logger.info("Single query test results for Arabidopsis thaliana without Computed Structure Models has count greater than 1900: ok : (%s)", ok)
        ok = q2_computational_length > 27000
        self.assertTrue(ok)
        logger.info("Single query test results for Arabidopsis thaliana with Computed Structure Models has count greater than 27000: ok : (%s)", ok)

        # full text search test with computed models
        q3 = TextQuery("hemoglobin")
        session = Session(q3, return_content_type=["computational", "experimental"])
        result = session._single_query()
        ok = result is not None
        self.assertTrue(ok)
        logger.info("Text Query results with Computed Structure Models: ok : (%r)", ok)

        # Query with only computed models
        q4 = AttributeQuery("rcsb_uniprot_protein.name.value", operator="contains_phrase", value="Hemoglobin")
        session = Session(q4, return_content_type=["computational"])
        result = session._single_query()
        ok = result is not None
        self.assertTrue(ok)
        q4_length = len(list(q4(return_content_type=["computational"])))
        ok2 = q4_length == 885
        self.assertTrue(ok2)
        logger.info("Query results with only computed models: ok : (%r) : ok2 : (%s)", ok, ok2)

    def testSequenceQuery(self):
        """Test firing off a Sequence query"""
        # Sequence query with hemoglobin protein sequence (id: 4HHB). Default parameters
        q1 = SequenceQuery("VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR")
        result = list(q1())
        result_len = len(result)
        ok = result_len > 0  # this query displays 706 ids in pdb website search function
        logger.info("Sequence query results correctly displays ids: (%r)", ok)

        # Sequence query (id: 4HHB) with custom parameters
        q1 = SequenceQuery("VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR",
                           evalue_cutoff=0.01, identity_cutoff=0.9)
        result = list(q1())
        result_len = len(result)
        ok = result_len > 0  # this query displays 313 ids in pdb website search function
        logger.info("Sequence query results correctly displays ids with custom parameters: (%r)", ok)

    def testSeqMotifQuery(self):
        """Test firing off a SeqMotif query"""
        q1 = SeqMotifQuery("RK")  # basic test, make sure standard query is instantiated properly
        result = list(q1())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Basic SeqMotif query results: result_length : (%d), ok : (%r)", len(result), ok)

        q2 = SeqMotifQuery("FFFFF", sequence_type="dna")  # test a DNA query, this should yield no results
        result = list(q2())
        ok = len(result) == 0
        self.assertTrue(ok)
        logger.info("Basic DNA SeqMotif query results: result_length : (%d) (this should be 0), ok : (%r)", len(result), ok)

        q3 = SeqMotifQuery("CCGGCG", sequence_type="dna")
        result = list(q3())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Basic Functional DNA query results: result_length : (%d), ok : (%r)", len(result), ok)

        # rna query
        q4 = SeqMotifQuery("AUXAU", sequence_type="rna")  # X is a variable for any amino acid in that position
        result = list(q4())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Basic Functional RNA query results: result_length : (%d), ok : (%r)", len(result), ok)

        q5 = SeqMotifQuery("ATUAC")  # An rna query with T should yield no results
        result = list(q5())
        ok = len(result) == 0
        self.assertTrue(ok)
        logger.info("Basic Non-functional DNA query results: result_length : (%d), ok : (%r)", len(result), ok)

        ok = False
        try:
            _ = SeqMotifQuery("A")  # test an invalid query. This will fail.
        except ValueError:
            ok = True
        self.assertTrue(ok)
        logger.info("Short SeqMotif query failed successfully: (%r)", ok)

        ok = False
        try:
            q1 = SeqMotifQuery("AAAA", "nothing", "nothing")  # this should fail
            _ = list(q1())
        except requests.exceptions.HTTPError:
            ok = True
        self.assertTrue(ok)
        logger.info("SeqMotif Query with invalid parameters failed successfully: (%r)", ok)


def buildSearch():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SearchTests("testConstruction"))
    suiteSelect.addTest(SearchTests("testLargePagination"))
    suiteSelect.addTest(SearchTests("testOperators"))
    suiteSelect.addTest(SearchTests("testPartialQuery"))
    suiteSelect.addTest(SearchTests("testFreeText"))
    suiteSelect.addTest(SearchTests("testAttribute"))
    suiteSelect.addTest(SearchTests("exampleQuery1"))
    suiteSelect.addTest(SearchTests("exampleQuery2"))
    suiteSelect.addTest(SearchTests("testMalformedQuery"))
    suiteSelect.addTest(SearchTests("testPagination"))
    suiteSelect.addTest(SearchTests("testXor"))
    suiteSelect.addTest(SearchTests("testInversion"))
    suiteSelect.addTest(SearchTests("testIterable"))
    suiteSelect.addTest(SearchTests("testIquery"))
    suiteSelect.addTest(SearchTests("testSingleQuery"))
    suiteSelect.addTest(SearchTests("testChemSearch"))
    suiteSelect.addTest(SearchTests("testMismatch"))
    suiteSelect.addTest(SearchTests("testCSMquery"))
    suiteSelect.addTest(SearchTests("testSequenceQuery"))
    suiteSelect.addTest(SearchTests("testSeqMotifQuery"))
    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSearch()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
