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
import os
from itertools import islice
import requests
from rcsbsearchapi.const import CHEMICAL_ATTRIBUTE_SEARCH_SERVICE, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE, RETURN_UP_URL
from rcsbsearchapi import Attr, Group, TextQuery
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import PartialQuery, Terminal, AttributeQuery, SequenceQuery, SeqMotifQuery, StructSimilarityQuery, fileUpload, StructureMotifResidue, StructMotifQuery
from rcsbsearchapi.search import Session, Value
from rcsbsearchapi.search import ChemSimilarityQuery
from rcsbsearchapi.search import Facet, Range, TerminalFilter, GroupFilter, FilterFacet
from rcsbsearchapi.search import Sort
from rcsbsearchapi.search import GroupBy, RankingCriteriaType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]-%(module)s.%(funcName)s: %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.__startTime = time.time()
        logger.info("Starting %s at %s", self.id(), time.strftime("%Y %m %d %H:%M:%S", time.localtime()))
        HERE = os.path.abspath(os.path.dirname(__file__))
        self.__dirPath = os.path.join(HERE, "files")
        self.__4hhbBcif = os.path.join(self.__dirPath, "4hhb.bcif")
        self.__4hhbCif = os.path.join(self.__dirPath, "4hhb.cif")
        self.__4hhbPdb = os.path.join(self.__dirPath, "4hhb.pdb")
        self.__7n0rPdbGz = os.path.join(self.__dirPath, "7n0r.pdb.gz")
        self.__7n0rCifGz = os.path.join(self.__dirPath, "7n0r.cif.gz")
        self.__invalidTxt = os.path.join(self.__dirPath, "invalid.txt")
        self.__4hhbAssembly1 = os.path.join(self.__dirPath, "4hhb-assembly1.cif.gz")
        self.__4hhbpdb1 = os.path.join(self.__dirPath, "4hhb.pdb1")
        self.__4hhbpdb1Gz = os.path.join(self.__dirPath, "4hhb.pdb1.gz")
        self.__2mnr = os.path.join(self.__dirPath, "2mnr.cif")

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
        q1 = AttributeQuery("invalid_identifier", operator="exact_match", value="ERROR", service="text")
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
        query2 = TextQuery("heat-shock transcription factor").and_(AttributeQuery(attribute="rcsb_struct_symmetry.symbol", operator="exact_match", value="C2")
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
        attr = Attr(attribute="attr", type="type")

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
        query = Attr(attribute="a", type="text").equals("aval").and_("b")

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

        query = query.and_(Attr("c", "text") < 5)
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
        ok = query.attr == Attr("d", "text")
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
        q1 = attrs.rcsb_entry_container_identifiers.rcsb_id.in_(["4HHB", "2GS2"])  # test in
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
        ok2 = q4_length >= 800
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
        try:
            result = list(q2())
        except requests.exceptions.HTTPError as e:
            logger.error("HTTPError occurred: %s", e)
            result = []
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
        try:
            result = list(q5())
        except requests.exceptions.HTTPError as e:
            logger.error("HTTPError occurred: %s", e)
            result = []
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

    def testFileUpload(self):
        """Test uploading a file. Used for structure queries.
        As a unique URL is generated each time, the only common
        denominator is that the return URL contains the file
        name at the end of it, and that the first part of the
        URL is the same."""

        hemo = self.__4hhbCif
        x = fileUpload(hemo)
        ok = (x[x.rfind("/") + 1:]) == "4hhb.bcif"  # check that end of file name is 4hhb.cif
        self.assertTrue(ok)
        logger.info(".cif File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x  # check that beginning of URL is formed correctly. This is admittedly rather redundant.
        self.assertTrue(ok)
        logger.info(".cif File Upload check two: (%r)", ok)

        zipfile = self.__7n0rCifGz  # gz files should also work by default
        x = fileUpload(zipfile)
        ok = (x[x.rfind("/") + 1:]) == "7n0r.bcif"
        self.assertTrue(ok)
        logger.info(".cif.gz File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x
        self.assertTrue(ok)
        logger.info(".cif.gz File Upload check two: (%r)", ok)

        pdbfile = self.__4hhbPdb
        x = fileUpload(pdbfile, "pdb")  # for non-cif files provide file extension
        ok = (x[x.rfind("/") + 1:]) == "4hhb.bcif"  # check that end of file name is 4hhb.bcif
        self.assertTrue(ok)
        logger.info(".pdb File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x
        self.assertTrue(ok)
        logger.info(".pdb File Upload check two: (%r)", ok)

        zippdb = self.__7n0rPdbGz  # PDB Zip files should work as well.
        x = fileUpload(zippdb, "pdb")
        ok = (x[x.rfind("/") + 1:]) == "7n0r.bcif"
        self.assertTrue(ok)
        logger.info(".pdb.gz File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x
        self.assertTrue(ok)
        logger.info(".pdb.gz File Upload check two: (%r)", ok)

        hemobcif = self.__4hhbBcif
        x = fileUpload(hemobcif, "bcif")  # must specify that file you are providing is bcif
        ok = (x[x.rfind("/") + 1:]) == "4hhb.bcif"  # check that end of file name is 4hhb.bcif
        self.assertTrue(ok)
        logger.info(".bcif File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x  # check that beginning of URL is formed correctly.
        self.assertTrue(ok)
        logger.info(".bcif File Upload check two: (%r)", ok)

        hemoAssem = self.__4hhbAssembly1
        x = fileUpload(hemoAssem)
        ok = (x[x.rfind("/") + 1:]) == "4hhb-assembly1.bcif"
        self.assertTrue(ok)
        logger.info(".cif.gz Assembly File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x  # check that beginning of URL is formed correctly.
        self.assertTrue(ok)
        logger.info(".cif.gz Assembly File Upload check two: (%r)", ok)

        hemopdb1 = self.__4hhbpdb1
        x = fileUpload(hemopdb1, "pdb")
        ok = (x[x.rfind("/") + 1:]) == "4hhb.pdb1.bcif"
        self.assertTrue(ok)
        logger.info(".pdb1 File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x  # check that beginning of URL is formed correctly.
        self.assertTrue(ok)
        logger.info(".pdb1 File Upload check two: (%r)", ok)

        hemopdb1gz = self.__4hhbpdb1Gz
        x = fileUpload(hemopdb1gz, "pdb")
        ok = (x[x.rfind("/") + 1:]) == "4hhb.pdb1.bcif"
        self.assertTrue(ok)
        logger.info(".pdb1.gz File Upload check one: (%r)", ok)

        ok = RETURN_UP_URL in x  # check that beginning of URL is formed correctly.
        self.assertTrue(ok)
        logger.info(".pdb1.gz File Upload check two: (%r)", ok)

        # test error handling

        invalid = self.__invalidTxt
        ok = False
        try:
            _ = fileUpload(invalid, "bcif")
        except TypeError:
            ok = True
        self.assertTrue(ok)
        logger.info("invalid query failed successfully: (%r)", ok)

    def testStructSimQuery(self):
        """Test firing off a structure similarity query"""
        # Basic query - assembly ID
        q1 = StructSimilarityQuery(entry_id="4HHB")
        result = list(q1())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Basic Structure Similarity query results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with chain ID
        q2 = StructSimilarityQuery(structure_search_type="entry_id",
                                   entry_id="4HHB",
                                   structure_input_type="chain_id",
                                   chain_id="A",
                                   target_search_space="polymer_entity_instance")
        result = list(q2())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Query with chain ID results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with file url
        q3 = StructSimilarityQuery(structure_search_type="file_url",
                                   file_url="https://files.rcsb.org/view/4HHB.cif",
                                   file_format="cif")
        result = list(q3())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Query with file url results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with file upload
        q4 = StructSimilarityQuery(structure_search_type="file_upload",
                                   file_path=self.__4hhbCif,
                                   file_format="cif")
        result = list(q4())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Query with file upload results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with relaxed operator
        q5 = StructSimilarityQuery(structure_search_type="entry_id",
                                   entry_id="4HHB",
                                   operator="relaxed_shape_match")
        result = list(q5())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Query with relaxed operator results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with specifically polymer entity instance search space
        q6 = StructSimilarityQuery(structure_search_type="entry_id",
                                   entry_id="4HHB",
                                   structure_input_type="chain_id",
                                   chain_id="B",
                                   operator="relaxed_shape_match",
                                   target_search_space="polymer_entity_instance")
        result = list(q6())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Query with polymer entity instance results: result length : (%d), ok : (%r)", len(result), ok)

        # File upload query using 4HHB Assembly 1 - cif zip file
        q7 = StructSimilarityQuery(structure_search_type="file_upload",
                                   file_path=self.__4hhbAssembly1,
                                   file_format="cif")
        result = list(q7())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("File upload query using 4HHB Assembly 1 cif zip file results : (%d), ok : (%r)", len(result), ok)

        # File upload query using 4HHB PDB file
        q8 = StructSimilarityQuery(structure_search_type="file_upload",
                                   file_path=self.__4hhbPdb,
                                   file_format="pdb")
        result = list(q8())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("File upload query using 4HHB PDB file results: result length : (%d), ok : (%r)", len(result), ok)

        # File upload query using 4HHB bcif file
        q9 = StructSimilarityQuery(structure_search_type="file_upload",
                                   file_path=self.__4hhbBcif,
                                   file_format="bcif")
        result = list(q9())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("File upload query using 4HHB bcif file results: result length : (%d), ok : (%r)", len(result), ok)

        # File url query with mmcif file format, relaxed operator, and chains target search space
        q10 = StructSimilarityQuery(structure_search_type="file_url",
                                    file_url="https://files.rcsb.org/view/4HHB.cif",
                                    file_format="cif",
                                    operator="relaxed_shape_match",
                                    target_search_space="polymer_entity_instance")
        result = list(q10())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("File url query using mmcif file format, relaxed, and chains: result length : (%d), ok : (%r)", len(result), ok)

        # File url query with wrong combination of fire url and format (should fail)
        ok = False
        try:
            q11 = StructSimilarityQuery(structure_search_type="file_url",
                                        file_url="https://files.rcsb.org/view/4HHB.cif",
                                        file_format="pdb")
            result = list(q11())
        except requests.HTTPError:
            ok = True
        self.assertTrue(ok)
        logger.info("File url query with wrong file format failed successfully : (%r)", ok)

    def testStructMotifQuery(self):
        # base example, entry ID, residues
        Res1 = StructureMotifResidue("A", "1", 162, ["LYS", "HIS"])
        Res2 = StructureMotifResidue("A", "1", 193, ["ASP"])
        Res3 = StructureMotifResidue("A", "1", 192, ["LYS", "HIS", "ASP", "VAL"])
        Res4 = StructureMotifResidue("A", "1", 191, ["LYS", "HIS", "ASP", "VAL"])
        Res5 = StructureMotifResidue("A", "1", 190, ["LYS", "HIS", "ASP", "VAL"])
        Res6 = StructureMotifResidue("A", "1", 189, ["LYS", "HIS", "ASP", "VAL"])
        ResList = [Res1, Res2]

        q1 = StructMotifQuery(entry_id="2MNR", residue_ids=ResList)  # Avoid positionals for StructMotifQuery... way too many things are optional in these queries
        result = list(q1())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Basic StructMotifQuery completed successfully: (%r)", ok)

        # base example with file upload
        MNR = self.__2mnr
        q2 = StructMotifQuery(structure_search_type="file_upload", file_path=MNR, file_extension="cif", residue_ids=ResList)
        # You MUST specify structure_search_type for non entry_id queries.
        result = list(q2())
        ok = len(result) > 0  # Note that because of a bug where two queries don't return the same result, you can't compare results from this query and previous.
        self.assertTrue(ok)
        logger.info("File Upload StructMotifQuery completed successfully: (%r)", ok)

        # base example with file link
        link = "https://files.rcsb.org/view/2MNR.cif"
        q3 = StructMotifQuery(structure_search_type="file_url", url=link, file_extension="cif", residue_ids=ResList)
        result = list(q3())
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("File URL StructMotifQuery completed successfully: (%r)", ok)

        # invalid queries

        # no residues provided
        ok = False
        try:
            _ = StructMotifQuery(entry_id="2MNR")  # residue list missing
        except ValueError:
            ok = True
        self.assertTrue(ok)
        logger.info("No residues error caught correctly: (%r)", ok)

        # filepath missing for file upload
        ok = False
        try:
            _ = StructMotifQuery(structure_search_type="file_upload", file_extension="cif", residue_ids=ResList)
        except AssertionError:
            ok = True
        self.assertTrue(ok)
        logger.info("File Upload malformed query caught correctly: (%r)", ok)

        # file url missing for file upload
        ok = False
        try:
            _ = StructMotifQuery(structure_search_type="file_url", file_extension="cif", residue_ids=ResList)
        except AssertionError:
            ok = True
        self.assertTrue(ok)
        logger.info("File URL malformed query caught correctly: (%r)", ok)

        # make sure max exchanges per residue is 4
        ok = False
        try:
            _ = StructureMotifResidue("A", "1", 192, ["LYS", "HIS", "ASP", "VAL", "TYR"])  # not possible
        except AssertionError:
            ok = True
        self.assertTrue(ok)
        logger.info("Max exchanges per residue asserted correctly: (%r)", ok)

        # make sure no more than 16 max exchanges total per query
        ok = False
        _ = StructMotifQuery(entry_id="2MNR", residue_ids=[Res3, Res4, Res5, Res6])  # this should cause no issues, 16
        try:
            _ = StructMotifQuery(entry_id="2MNR", residue_ids=[Res2, Res3, Res4, Res5, Res6])  # this should crash
        except AssertionError:
            ok = True
        self.assertTrue(ok)
        logger.info("Max exchanges per query asserted correctly: (%r)", ok)

        # catch invalid query_id
        ok = False
        try:
            _ = StructMotifQuery(structure_search_type="invalid structure_search_type goes here", residue_ids=ResList)
        except ValueError:
            ok = True
        self.assertTrue(ok)
        logger.info("Invalid structure_search_type caught correctly: (%r)", ok)

    def testChemSimilarityQuery(self):
        """Test firing off chemical similarity queries"""
        # Basic query with default values: query type = formula and match subset = False
        q1 = ChemSimilarityQuery(value="C12 H17 N4 O S")
        result = list(q1())
        ok = len(result) > 0
        logger.info("Basic query with default values results: result length : (%d), ok : (%r)", len(result), ok)

        # query with type = formula and match subset = True
        q2 = ChemSimilarityQuery(value="C12 H28 O4",
                                 query_type="formula",
                                 match_subset=True)
        result = list(q2())
        ok = len(result) > 0
        logger.info("Query with type = formula and match subset = True results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with type = descriptor, descriptor type = SMILES, match type = similar ligands (sterospecific) or graph-relaxed-stereo
        q3 = ChemSimilarityQuery(value="Cc1c(sc[n+]1Cc2cnc(nc2N)C)CCO",
                                 query_type="descriptor",
                                 descriptor_type="SMILES",
                                 match_type="graph-relaxed-stereo")
        result = list(q3())
        ok = len(result) > 0
        logger.info("Query with using type - descriptor, SMILES, and graph-relaxed-stereo results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with type = descriptor, descriptor type = SMILES, match type = similar ligands (including stereoisomers) or graph-relaxed
        q4 = ChemSimilarityQuery(value="Cc1c(sc[n+]1Cc2cnc(nc2N)C)CCO",
                                 query_type="descriptor",
                                 descriptor_type="SMILES",
                                 match_type="graph-relaxed")
        result = list(q4())
        ok = len(result) > 0
        logger.info("Query with using type - descriptor, SMILES, and graph-relaxed results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with type = descriptor, descriptor type = SMILES, match type = similar ligands (quick screen) or fingerprint-similarity
        q5 = ChemSimilarityQuery(value="Cc1c(sc[n+]1Cc2cnc(nc2N)C)CCO",
                                 query_type="descriptor",
                                 descriptor_type="SMILES",
                                 match_type="fingerprint-similarity")
        result = list(q5())
        ok = len(result) > 0
        logger.info("Query with using type - descriptor, SMILES, and fingerprint-similarity results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with type = descriptor, descriptor type = InChI, match type = substructure (sterospecific) or sub-struct-graph-relaxed-stereo
        q6 = ChemSimilarityQuery(value="InChI=1S/C13H10N2O4/c16-10-6-5-9(11(17)14-10)15-12(18)7-3-1-2-4-8(7)13(15)19/h1-4,9H,5-6H2,(H,14,16,17)/t9-/m0/s1",
                                 query_type="descriptor",
                                 descriptor_type="InChI",
                                 match_type="sub-struct-graph-relaxed-stereo")
        result = list(q6())
        ok = len(result) > 0
        logger.info("Query with using type - descriptor, InChI, and sub-struct-graph-relaxed-stereo results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with type = descriptor, descriptor type = InChI, match type = substructure (including stereoisomers) or sub-struct-graph-relaxed
        q7 = ChemSimilarityQuery(value="InChI=1S/C13H10N2O4/c16-10-6-5-9(11(17)14-10)15-12(18)7-3-1-2-4-8(7)13(15)19/h1-4,9H,5-6H2,(H,14,16,17)/t9-/m0/s1",
                                 query_type="descriptor",
                                 descriptor_type="InChI",
                                 match_type="sub-struct-graph-relaxed")
        result = list(q7())
        ok = len(result) > 0
        logger.info("Query with using type - descriptor, InChI, and sub-struct-graph-relaxed results: result length : (%d), ok : (%r)", len(result), ok)

        # Query with type = descriptor, descriptor type = InChI, match type = exact match or graph-exact
        q8 = ChemSimilarityQuery(value="InChI=1S/C13H10N2O4/c16-10-6-5-9(11(17)14-10)15-12(18)7-3-1-2-4-8(7)13(15)19/h1-4,9H,5-6H2,(H,14,16,17)/t9-/m0/s1",
                                 query_type="descriptor",
                                 descriptor_type="InChI",
                                 match_type="graph-exact")
        result = list(q8())
        ok = len(result) > 0
        logger.info("Query with using type - descriptor, InChI, and graph-exact results: result length : (%d), ok : (%r)", len(result), ok)

        # Invalid query with invalid parameters
        ok = False
        try:
            q9 = ChemSimilarityQuery(value="InChI=1S/C13H10N2O4/c16-10-6-5-9(11(17)14-10)15-12(18)7-3-1-2-4-8(7)13(15)19/h1-4,9H,5-6H2,(H,14,16,17)/t9-/m0/s1",
                                     query_type="descriptor",
                                     descriptor_type="something",  # unsupported parameter
                                     match_type="something")  # unsupported parameter
            result = list(q9())
        except requests.HTTPError:
            ok = True
        self.assertTrue(ok)
        logger.info("Descriptor query type with invalid parameters failed successfully : (%r)", ok)

    def testReturnCounts(self):
        """Test firing off results count requests"""
        # Attribute query test
        q1 = AttributeQuery("exptl.method", "exact_match", "FLUORESCENCE TRANSFER")
        result = q1(return_type="assembly", return_counts=True)
        ok = result == len(list(q1("assembly")))
        self.assertTrue(ok)
        logger.info("Counting results of structural Attribute query: (%d), ok : (%r)", result, ok)

        q2 = TextQuery("hemoglobin")
        result = q2(return_counts=True)
        ok = result == len(list(q2()))
        self.assertTrue(ok)
        logger.info("Counting results of Text query: (%d), ok : (%r)", result, ok)

        q3 = AttributeQuery(
            "drugbank_info.brand_names",
            "contains_phrase",
            "tylenol",
            CHEMICAL_ATTRIBUTE_SEARCH_SERVICE,  # this constant specifies "text_chem" service
        )
        result = q3(return_counts=True)
        ok = result == len(list(q3()))
        self.assertTrue(ok)
        logger.info("Counting results of chemical Attribute query: (%d), ok : (%r)", result, ok)

        q4 = SequenceQuery(
            "MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGET"
            + "CLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQI"
            + "KRVKDSDDVPMVLVGNKCDLPARTVETRQAQDLARSYGIPYIETSAKTRQ"
            + "GVEDAFYTLVREIRQHKLRKLNPPDESGPGCMNCKCVIS",
            1,
            0.9,
        )
        result = q4(return_counts=True)
        ok = result == len(list(q4()))
        self.assertTrue(ok)
        logger.info("Counting results of Sequence query: (%d), ok : (%r)", result, ok)

        q5 = SeqMotifQuery(
            "C-x(2,4)-C-x(3)-[LIVMFYWC]-x(8)-H-x(3,5)-H.",
            pattern_type="prosite",
            sequence_type="protein",
        )
        result = q5(return_counts=True)
        ok = result == len(list(q5()))
        self.assertTrue(ok)
        logger.info("Counting results of Sequence motif query: (%d), ok : (%r)", result, ok)

        q6 = StructSimilarityQuery(
            structure_search_type="entry_id",
            entry_id="4HHB",  # Structure Similarity Query
            structure_input_type="assembly_id",
            assembly_id="1",
            operator="strict_shape_match",
            target_search_space="assembly",
        )
        result = q6(return_counts=True)
        ok = result == len(list(q6()))
        self.assertTrue(ok)
        logger.info("Counting results of Structure similarity query: (%d), ok : (%r)", result, ok)

        Res1 = StructureMotifResidue("A", "1", 162, ["LYS", "HIS"])
        Res2 = StructureMotifResidue("A", "1", 193)
        Res3 = StructureMotifResidue("A", "1", 219)
        Res4 = StructureMotifResidue("A", "1", 245, ["GLU", "ASP", "ASN"])
        Res5 = StructureMotifResidue("A", "1", 295, ["HIS", "LYS"])
        ResList = [Res1, Res2, Res3, Res4, Res5]
        q7 = StructMotifQuery(entry_id="2MNR", residue_ids=ResList)
        result = q7(return_counts=True)
        ok = result == len(list(q7()))
        self.assertTrue(ok)
        logger.info("Counting results of Structure motif query: (%d), ok : (%r)", result, ok)

        q8 = ChemSimilarityQuery(value="C12 H17 N4 O S")
        result = q8(return_counts=True)
        ok = result == len(list(q8()))
        self.assertTrue(ok)
        logger.info("Counting results of Chemical similarity query: (%d), ok : (%r)", result, ok)

        ok = False
        q9 = AttributeQuery("invalid_identifier", operator="exact_match", value="ERROR", service="textx")
        try:
            _ = q9()
        except requests.HTTPError:
            ok = True
        self.assertTrue(ok)
        logger.info("Counting results of Attribute query type with invalid parameters failed successfully : (%r)", ok)

        q10 = TextQuery(" ")
        result = q10(return_counts=True)
        ok = result == 0
        self.assertTrue(ok)
        logger.info("Counting results of empty Text query failed successfully : (%r)", ok)

        q11 = TextQuery("heat-shock transcription factor")
        q12 = AttributeQuery(attribute="rcsb_struct_symmetry.symbol", operator="exact_match", value="C2")
        q13 = q11 & q12
        result = q13(return_counts=True)
        ok = result == len(list(q13()))
        self.assertTrue(ok)
        logger.info("Counting results queries combined with &: (%d), ok : (%r)", result, ok)

        q14 = q11 | q12
        result = q14(return_counts=True)
        ok = result == len(list(q11())) + len(list(q12())) - len(list(q13()))
        self.assertTrue(ok)
        logger.info("Counting results of queries combined with &: (%d), ok : (%r)", result, ok)

    def testResultsVerbosity(self):
        """Test firing off queries with result verbosity set"""
        q1 = AttributeQuery("rcsb_entry_info.polymer_entity_count_RNA", operator="equals", value=4)
        result = list(q1(results_verbosity="compact"))
        ok = len(result) == len(list(q1()))
        self.assertTrue(ok)
        logger.info("Query with compact results: (%d), ok : (%r)", len(result), ok)

        result = list(q1(results_verbosity="minimal"))
        ok = len(result) == len(list(q1()))
        self.assertTrue(ok)
        logger.info("Query with minimal results: (%d), ok : (%r)", len(result), ok)

        result = list(q1(results_verbosity="verbose"))
        ok = len(result) == len(list(q1()))
        self.assertTrue(ok)
        logger.info("Query with verbose results: (%d), ok : (%r)", len(result), ok)

    def testFacetQuery(self):
        """Test firing off Facets queries and Filter Facet queries"""

        q1 = AttributeQuery(
            attribute="rcsb_accession_info.initial_release_date",
            operator="greater",
            value="2019-08-20",
        )
        result = q1(facets=[Facet("Methods", "terms", "exptl.method")]).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Basic Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(facets=Facet("Journals", "terms", "rcsb_primary_citation.rcsb_journal_abbrev", min_interval_population=1000)).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Terms Facet query on Empty query results: result length : (%d), ok : (%r)", len(result), ok)

        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(
            return_type="polymer_entity",
            facets=Facet("Formula Weight", "histogram", "rcsb_polymer_entity.formula_weight", interval=50, min_interval_population=1)
        ).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Histogram Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(
            return_type="polymer_entity",
            facets=Facet("Release Date", "date_histogram", "rcsb_accession_info.initial_release_date", interval="year", min_interval_population=1)
        ).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Date Histogram Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(
            facets=Facet(
                "Resolution Combined",
                "range",
                "rcsb_entry_info.resolution_combined",
                ranges=[Range(None, 2), Range(2, 2.2), Range(2.2, 2.4), Range(4.6, None)]
            )
        ).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Range Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental"
        )
        result = q1(
            facets=Facet(
                "Release Date",
                "date_range",
                "rcsb_accession_info.initial_release_date",
                ranges=[Range(None, "2020-06-01||-12M"), Range("2020-06-01", "2020-06-01||+12M"), Range("2020-06-01||+12M", None)]
            )
        ).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Date Range Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(
            facets=Facet("Organism Names Count", "cardinality", "rcsb_entity_source_organism.ncbi_scientific_name")
        ).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Cardinality Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        f1 = Facet("Polymer Entity Types", "terms", "rcsb_entry_info.selected_polymer_entity_types")
        f2 = Facet("Release Date", "date_histogram", "rcsb_accession_info.initial_release_date", interval="year")
        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(facets=Facet("Experimental Method", "terms", "rcsb_entry_info.experimental_method", nested_facets=[f1, f2])).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Multi-dimensional Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        tf1 = TerminalFilter("rcsb_polymer_instance_annotation.type", "exact_match", value="CATH")
        tf2 = TerminalFilter("rcsb_polymer_instance_annotation.annotation_lineage.id", "in", ["2.140.10.30", "2.120.10.80"])
        ff1 = FilterFacet(tf2, Facet("CATH Domains", "terms", "rcsb_polymer_instance_annotation.annotation_lineage.id", min_interval_population=1))
        ff2 = FilterFacet(tf1, ff1)
        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(return_type="polymer_instance", facets=[ff2]).facets
        print(f"filterfacet:\n {result}")
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Filter Facet query results: result length : (%d), ok : (%r)", len(result), ok)

        tf3 = TerminalFilter("rcsb_struct_symmetry.kind", "exact_match", value="Global Symmetry", negation=False)
        f3 = Facet("ec_terms", "terms", "rcsb_polymer_entity.rcsb_ec_lineage.id")
        f4 = Facet("sym_symbol_terms", "terms", "rcsb_struct_symmetry.symbol", nested_facets=f3)
        ff3 = FilterFacet(tf3, f4)
        q2 = AttributeQuery("rcsb_assembly_info.polymer_entity_count", operator="equals", value=1)
        q3 = AttributeQuery("rcsb_assembly_info.polymer_entity_instance_count", operator="greater", value=1)
        q4 = q2 & q3
        result = q4(return_type="assembly", facets=ff3).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Filter Facet query with Multi-dimensional facets results: result length : (%d), ok : (%r)", len(result), ok)

        tf4 = TerminalFilter("rcsb_polymer_entity_group_membership.aggregation_method", "exact_match", value="sequence_identity")
        tf5 = TerminalFilter("rcsb_polymer_entity_group_membership.similarity_cutoff", "equals", value=100)
        gf1 = GroupFilter("and", [tf4, tf5])
        ff4 = FilterFacet(gf1, Facet("Distinct Protein Sequence Count", "cardinality", "rcsb_polymer_entity_group_membership.group_id"))
        q1 = AttributeQuery(
            attribute="rcsb_entry_info.structure_determination_methodology",
            operator="exact_match",
            value="experimental",
        )
        result = q1(return_type="polymer_entity", facets=ff4).facets
        ok = len(result) > 0
        self.assertTrue(ok)
        logger.info("Group Filter Facet query results: result length : (%d), ok : (%r)", len(result), ok)

    def testGroupBy(self):
        with self.subTest("1. Group by deposit ID + ranking_criteria_type"):
            # TerminalFilter
            try:
                tf = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.aggregation_method", operator="exact_match", value="sequence_identity")
                query = AttributeQuery(
                    attribute="rcsb_entity_source_organism.scientific_name",
                    operator="exact_match",
                    value="gallus gallus",
                )
                list(query(
                    group_by=GroupBy(
                        aggregation_method="matching_deposit_group_id",
                        ranking_criteria_type=RankingCriteriaType(sort_by="score", filter=tf, direction="asc"),
                    )))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # GroupFilter
            try:
                tf1 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.aggregation_method", operator="exact_match", value="electron microscopy")
                tf2 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.similarity_cutoff", operator="equals", value=100)
                gf = GroupFilter(logical_operator="and", nodes=[tf1, tf2])
                query = AttributeQuery(
                    attribute="rcsb_entity_source_organism.scientific_name",
                    operator="exact_match",
                    value="gallus gallus",
                )
                list(query(
                    group_by=GroupBy(
                        aggregation_method="matching_deposit_group_id",
                        ranking_criteria_type=RankingCriteriaType(sort_by="score", filter=gf, direction="asc"),
                    )
                ))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # Wrong return_type
            query = AttributeQuery(
                attribute="rcsb_entity_source_organism.scientific_name",
                operator="exact_match",
                value="gallus gallus",
            )
            query_dict = (query(
                return_type="polymer_entity",
                group_by=GroupBy(
                    aggregation_method="matching_deposit_group_id",
                )
            ))._make_params()
            self.assertEqual(query_dict["return_type"], "entry")

        with self.subTest("2. Group by sequence identity"):
            try:
                tf1 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.aggregation_method", operator="exact_match", value="electron microscopy")
                tf2 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.similarity_cutoff", operator="equals", value=100)
                gf = GroupFilter(logical_operator="and", nodes=[tf1, tf2])
                query = AttributeQuery(
                    attribute="rcsb_assembly_info.polymer_entity_count",
                    operator="equals",
                    value=1,
                )
                list(query(
                    return_type="polymer_entity",
                    group_by=GroupBy(
                        aggregation_method="sequence_identity",
                        similarity_cutoff=95,
                        ranking_criteria_type=RankingCriteriaType(sort_by="score", filter=gf, direction="asc")
                    )
                ))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # Wrong return_type
            query = AttributeQuery(
                attribute="rcsb_assembly_info.polymer_entity_count",
                operator="equals",
                value=1,
            )
            query_dict = (query(
                return_type="entry",
                group_by=GroupBy(
                    aggregation_method="sequence_identity",
                    similarity_cutoff=95,
                )
            ))._make_params()
            self.assertEqual(query_dict["return_type"], "polymer_entity")

        with self.subTest("3. Group by UniProt Accession"):
            # using standard sort options
            try:
                tf1 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.aggregation_method", operator="exact_match", value="electron microscopy")
                tf2 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.similarity_cutoff", operator="equals", value=100)
                gf = GroupFilter(logical_operator="and", nodes=[tf1, tf2])
                query = AttributeQuery(
                    attribute="entity_poly.rcsb_mutation_count",
                    operator="equals",
                    value=10,
                )
                list(query(
                    return_type="polymer_entity",
                    group_by=GroupBy(
                        aggregation_method="matching_uniprot_accession",
                        ranking_criteria_type=RankingCriteriaType(sort_by="score", filter=gf, direction="asc")
                    )
                ))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # using uniprot specific ranking_criteria_type
            try:
                query = AttributeQuery(
                    attribute="entity_poly.rcsb_mutation_count",
                    operator="equals",
                    value=10,
                )
                list(query(
                    return_type="polymer_entity",
                    group_by=GroupBy(
                        aggregation_method="matching_uniprot_accession",
                        ranking_criteria_type=RankingCriteriaType(sort_by="coverage")
                    )
                ))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # Wrong return_type
            query = AttributeQuery(
                attribute="entity_poly.rcsb_mutation_count",
                operator="equals",
                value=10,
            )
            query_dict = (query(
                return_type="entry",
                group_by=GroupBy(
                    aggregation_method="matching_uniprot_accession",
                )
            ))._make_params()
            self.assertEqual(query_dict["return_type"], "polymer_entity")

    def testGroupByReturnType(self):
        query = AttributeQuery(
            attribute="rcsb_entity_source_organism.scientific_name",
            operator="exact_match",
            value="gallus gallus",
        )
        with self.subTest('1. Return type "representatives"'):
            # try running the query
            try:
                list(query(
                    return_type="polymer_entity",
                    group_by=GroupBy(
                        aggregation_method="sequence_identity",
                        similarity_cutoff=95,
                    ),
                    group_by_return_type="representatives"
                ))

            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # check parameters
            query_dict = (query(
                return_type="polymer_entity",
                group_by=GroupBy(
                    aggregation_method="sequence_identity",
                    similarity_cutoff=95,
                ),
                group_by_return_type="representatives"
            ))._make_params()
            self.assertEqual(query_dict["request_options"]["group_by_return_type"], "representatives")

        with self.subTest('2. Return type "groups"'):
            # try running the query
            try:
                list(query(
                    return_type="polymer_entity",
                    group_by=GroupBy(
                        aggregation_method="sequence_identity",
                        similarity_cutoff=95,
                    ),
                    group_by_return_type="groups"
                ))

            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # check parameters
            query_dict = (query(
                return_type="polymer_entity",
                group_by=GroupBy(
                    aggregation_method="sequence_identity",
                    similarity_cutoff=95,
                ),
                group_by_return_type="groups"
            ))._make_params()
            self.assertEqual(query_dict["request_options"]["group_by_return_type"], "groups")

        with self.subTest('3. Try "group_by_return_type" without "group_by"'):
            with self.assertRaises(ValueError):
                query(return_type="polymer_entity", group_by_return_type="groups")

    def testSort(self):
        with self.subTest("1. Sorting without filter"):
            try:
                query = AttributeQuery(
                    "rcsb_entity_source_organism.ncbi_scientific_name",
                    operator="exact_match",
                    value="Homo sapiens",
                )
                list(query(sort=Sort(sort_by="rcsb_assembly_info.polymer_entity_count", direction="asc")))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

        with self.subTest("1. Sorting with filter"):
            # Terminal Filter
            try:
                tf = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.aggregation_method", operator="exact_match", value="electron microscopy")
                query = AttributeQuery(
                    "rcsb_entity_source_organism.ncbi_scientific_name",
                    operator="exact_match",
                    value="Homo sapiens",
                )
                list(query(sort=Sort(sort_by="rcsb_assembly_info.polymer_entity_count", direction="asc", filter=tf)))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

            # Group Filter
            try:
                tf1 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.aggregation_method", operator="exact_match", value="electron microscopy")
                tf2 = TerminalFilter(attribute="rcsb_polymer_entity_group_membership.similarity_cutoff", operator="equals", value=100)
                gf = GroupFilter(logical_operator="and", nodes=[tf1, tf2])
                query = AttributeQuery(
                    "rcsb_entity_source_organism.ncbi_scientific_name",
                    operator="exact_match",
                    value="Homo sapiens",
                )
                list(query(sort=Sort(sort_by="rcsb_assembly_info.polymer_entity_count", direction="asc", filter=gf)))
            except Exception as error:
                self.fail(f"Failed unexpectedly: {error}")

    def testReturnExplainMetadata(self):
        query = AttributeQuery("rcsb_entity_source_organism.ncbi_scientific_name", operator="exact_match", value="Homo sapiens")
        self.assertIsNotNone(query(return_explain_metadata=True).explain_metadata)

    def testScoringStrategy(self):
        try:
            query = AttributeQuery("rcsb_entity_source_organism.ncbi_scientific_name", operator="exact_match", value="Homo sapiens")
            query(scoring_strategy="text")
        except Exception as error:
            self.fail(f"Failed unexpectedly: {error}")


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
    suiteSelect.addTest(SearchTests("testFileUpload"))
    suiteSelect.addTest(SearchTests("testStructSimQuery"))
    suiteSelect.addTest(SearchTests("testStructMotifQuery"))
    suiteSelect.addTest(SearchTests("testChemSimilarityQuery"))
    suiteSelect.addTest(SearchTests("testReturnCounts"))
    suiteSelect.addTest(SearchTests("testResultsVerbosity"))
    suiteSelect.addTest(SearchTests("testFacetQuery"))
    suiteSelect.addTest(SearchTests("testGroupBy"))
    suiteSelect.addTest(SearchTests("testGroupByReturnType"))
    suiteSelect.addTest(SearchTests("testSort"))
    suiteSelect.addTest(SearchTests("testReturnExplainMetadata"))
    suiteSelect.addTest(SearchTests("testScoringStrategy"))
    return suiteSelect


if __name__ == "__main__":
    mySuite = buildSearch()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
