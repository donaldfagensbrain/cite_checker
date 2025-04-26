import unittest
from typing import Any, Dict, Optional, Tuple

from newcitechecker import (
    CitationChecker,
    CitationValidationException,
    omit_words_in_case_name,
    validate_reporter_for_court
)
from citationfixer import auto_fix_citation, CitationFixError

class TestCitationCheckerCore(unittest.TestCase):
    def setUp(self):
        self.chk = CitationChecker()

    def test_valid_full_citation_wraps_case_name(self):
        comps, data, out = self.chk.validate_full_citation(
            "Brown v. Board, 347 U.S. 483 (U.S. 1954)"
        )
        # must wrap the exact case-name (no extra dots or commas)
        self.assertIn("<i>Brown v. Board</i>", out)

    def test_strip_trailing_comma_on_case_name(self):
        # even if user erroneously types a comma after the case-name
        bad = "Foo v. Bar,, 123 U.S. 456 (U.S. 2000)"
        comps, data, out = self.chk.validate_full_citation(bad)
        self.assertIn("<i>Foo v. Bar</i>", out)

    def test_missing_comma_and_parentheses(self):
        bad = "Foo v Bar 123 Xyz 456 WrongCourt 2025"
        with self.assertRaises(CitationValidationException) as cm:
            self.chk.validate_full_citation(bad)
        msg = str(cm.exception)
        self.assertIn("Missing parentheses", msg)
        self.assertIn("Missing comma", msg)

    def test_validate_dispatch_statute_and_fail(self):
        # assume PATTERNS includes statute under 'statute'
        good_statute = "12 C.S.C. § 3456"
        # should not raise
        self.assertTrue(self.chk.validate('statute', good_statute))
        with self.assertRaises(ValueError):
            self.chk.validate('statute', 'Not a statute')

    def test_omit_words_in_case_name_various(self):
        original = "The United States of America ex rel. John Doe, 10 U.S. 100 (U.S. 1800)"
        omitted = omit_words_in_case_name(original.split(',')[0])
        # "United States ex rel." (collapses, drops "John Doe")
        self.assertEqual(omitted, "United States ex rel.")

    def test_validate_reporter_for_court_rejects_bad(self):
        comps: Dict[str, Any] = {
            'court': 'Supreme Court',
            'reporter': 'F.2d'
        }
        # F.2d is not allowed for Supreme Court
        with self.assertRaises(ValueError):
            validate_reporter_for_court(comps)


class TestShortCitation(unittest.TestCase):
    def setUp(self):
        self.chk = CitationChecker()
        self.comps, _, _ = self.chk.validate_full_citation(
            "Alpha v. Beta, 10 U.S. 100 (U.S. 1800)"
        )

    def test_format_short_citation_explicit_then_id(self):
        short1 = self.chk.format_short_citation(self.comps, 'case')
        self.assertEqual(short1, "Alpha, 10 U.S. at 100.")
        # second time should yield Id. at pinpoint
        short2 = self.chk.format_short_citation(self.comps, 'case')
        self.assertEqual(short2, "Id. at 100.")

    def test_short_citation_reset_between_kinds(self):
        # a statute short
        comps_stat = {'code': '12 C.S.C.', 'section': '3456'}
        short_s = self.chk.format_short_citation(comps_stat, 'statute')
        self.assertEqual(short_s, "12 C.S.C. § 3456.")
        # next case again explicit, not Id.
        new_case_comps, _, _ = self.chk.validate_full_citation(
            "Gamma v. Delta, 11 U.S. 200 (U.S. 1801)"
        )
        short_new = self.chk.format_short_citation(new_case_comps, 'case')
        self.assertTrue(short_new.startswith("Gamma, 11 U.S. at 200"))


class TestFormatQuoteAndSignals(unittest.TestCase):
    def setUp(self):
        self.chk = CitationChecker()

    def test_inline_quote_less_than_50_words(self):
        q = "This is a short quote."
        formatted = self.chk.format_quote(q, "(U.S. 2000)")
        self.assertTrue(formatted.startswith('“This is a short quote.”'))
        self.assertTrue(formatted.endswith("(U.S. 2000)"))

    def test_block_quote_50_words_or_more(self):
        # build a 60‐word quote
        q = " ".join(f"word{i}" for i in range(60))
        formatted = self.chk.format_quote(q, "(U.S. 2000)")
        # should be indented (starts with 4 spaces)
        self.assertTrue(formatted.splitlines()[0].startswith("    word0"))

    def test_signal_formatting_italicizes_openers(self):
        text = "See Brown v. Board, 347 U.S. 483 (U.S. 1954)."
        out = self.chk._apply_signal_formatting(text)
        # "See " at the start should be italicized
        self.assertTrue(out.startswith("<i>See</i> "))
        # but signals in the middle should not
        mid = "as quoted in Brown"
        self.assertNotIn("<i>as quoted in</i>", self.chk._apply_signal_formatting(mid))


class TestCitationFixer(unittest.TestCase):
    def test_auto_fix_adds_comma_parentheses(self):
        bad = "Brown v. Board 347 U.S. 483 U.S. 1954"
        fixed = auto_fix_citation(bad)
        # after fix it must validate cleanly
        # and wrap case‐name correctly
        self.chk = CitationChecker()
        comps, data, out = self.chk.validate_full_citation(fixed)
        self.assertIn("<i>Brown v. Board</i>", out)

    def test_auto_fix_no_change_raises(self):
        # if fix_citation_format leaves it unchanged, it must bail
        with self.assertRaises(CitationFixError):
            auto_fix_citation("completely bogus text")

    def test_auto_fix_preserves_valid(self):
        good = "Brown v. Board, 347 U.S. 483 (U.S. 1954)"
        # should return the original unchanged
        self.assertEqual(auto_fix_citation(good), good)


if __name__ == "__main__":
    unittest.main()