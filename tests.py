import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import unittest

from newcitechecker import CitationChecker, CitationValidationException
from citationfixer import auto_fix_citation, CitationFixError

class TestCitationChecker(unittest.TestCase):
    def setUp(self):
        self.chk = CitationChecker()

    def test_valid_full_citation(self):
        comps, data, out = self.chk.validate_full_citation(
            "Brown v. Board, 347 U.S. 483 (U.S. 1954)"
        )
        # formatted out should wrap the case‐name in <i>…</i>
        self.assertIn("<i>Brown v. Board</i>", out)

    def test_invalid_full_citation_reports_multiple_errors(self):
        bad = "Foo v Bar 123 Xyz 456 WrongCourt 2025"
        with self.assertRaises(CitationValidationException) as cm:
            self.chk.validate_full_citation(bad)
        msg = str(cm.exception)
        # Should mention both missing comma *and* missing parentheses
        self.assertIn("Missing parentheses", msg)
        self.assertIn("Missing comma", msg)


class TestCitationFixer(unittest.TestCase):
    def test_auto_fix_adds_parentheses_and_comma(self):
        bad = "Brown v. Board 347 U.S. 483 U.S. 1954"
        fixed = auto_fix_citation(bad)
        # Now it should re‐validate cleanly
        self.chk = CitationChecker()
        # This should *not* raise
        self.chk.validate_full_citation(fixed)

    def test_auto_fix_unfixable_raises(self):
        with self.assertRaises(CitationFixError):
            auto_fix_citation("completely bogus text")

if __name__ == "__main__":
    unittest.main()