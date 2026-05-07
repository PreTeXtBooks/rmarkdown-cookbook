import tempfile
import unittest
from pathlib import Path

import check_ptx_consistency


class SplitRmdTests(unittest.TestCase):
    def test_split_rmd_ignores_headings_inside_fenced_blocks(self):
        prose, code_blocks = check_ptx_consistency.split_rmd(
            """---
title: Example
---

# Visible Heading

````md
## Hidden Heading
```{r}
1 + 1
```
````
"""
        )

        headings = check_ptx_consistency.extract_rmd_headings(prose)

        self.assertEqual(headings, ["visible heading"])
        self.assertEqual(len(code_blocks), 1)
        self.assertIn("## Hidden Heading", code_blocks[0])

    def test_split_rmd_ignores_headings_inside_standard_fences(self):
        prose, code_blocks = check_ptx_consistency.split_rmd(
            """# Visible Heading

```python
## Hidden Heading
print("hello")
```
"""
        )

        headings = check_ptx_consistency.extract_rmd_headings(prose)

        self.assertEqual(headings, ["visible heading"])
        self.assertEqual(len(code_blocks), 1)
        self.assertIn("## Hidden Heading", code_blocks[0])


class ChapterCheckTests(unittest.TestCase):
    def test_check_chapter_accepts_matching_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapter.Rmd").write_text(
                "# Sample Chapter\n\nThis prose matches the PTX version very closely.\n",
                encoding="utf-8",
            )
            (root / "chapter.ptx").write_text(
                "<chapter><title>Sample Chapter</title><p>This prose matches the PTX version very closely.</p></chapter>",
                encoding="utf-8",
            )

            errors = check_ptx_consistency.check_chapter(root, "chapter.Rmd", "chapter.ptx")

            self.assertEqual(errors, [])

    def test_check_chapter_reports_heading_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapter.Rmd").write_text(
                "# Sample Chapter\n\n## Important Section\n\nThis prose matches the PTX version very closely.\n",
                encoding="utf-8",
            )
            (root / "chapter.ptx").write_text(
                "<chapter><title>Sample Chapter</title><p>This prose matches the PTX version very closely.</p></chapter>",
                encoding="utf-8",
            )

            errors = check_ptx_consistency.check_chapter(root, "chapter.Rmd", "chapter.ptx")

            self.assertTrue(
                any("heading recall" in error for error in errors),
                "Expected a heading recall error but none was found",
            )


class BackmatterAndMainTests(unittest.TestCase):
    def test_check_backmatter_reports_missing_references_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "18-references.Rmd").write_text("# References\n", encoding="utf-8")
            (root / "pretext/source").mkdir(parents=True)
            (root / "pretext/source/meta_backmatter.ptx").write_text(
                "<backmatter><references><title>Bibliography</title></references></backmatter>",
                encoding="utf-8",
            )

            errors = check_ptx_consistency.check_backmatter(root)

            self.assertTrue(any("missing References title" in error for error in errors))
            self.assertTrue(any("expected at least" in error for error in errors))

    def test_main_returns_success_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapter.Rmd").write_text("# Sample Chapter\n\nMatching prose.\n", encoding="utf-8")
            (root / "chapter.ptx").write_text(
                "<chapter><title>Sample Chapter</title><p>Matching prose.</p></chapter>",
                encoding="utf-8",
            )
            (root / "18-references.Rmd").write_text("# References\n", encoding="utf-8")
            (root / "pretext/source").mkdir(parents=True)
            (root / "pretext/source/meta_backmatter.ptx").write_text(
                """<backmatter>
                <references>
                  <title>References</title>
                  <biblio xml:id="a"/>
                  <biblio xml:id="b"/>
                  <biblio xml:id="c"/>
                  <biblio xml:id="d"/>
                  <biblio xml:id="e"/>
                </references>
                </backmatter>""",
                encoding="utf-8",
            )

            original_root = check_ptx_consistency.REPO_ROOT
            original_pairs = check_ptx_consistency.CHAPTER_PAIRS
            try:
                check_ptx_consistency.REPO_ROOT = root
                check_ptx_consistency.CHAPTER_PAIRS = [("chapter.Rmd", "chapter.ptx")]
                self.assertEqual(check_ptx_consistency.main(), 0)

                (root / "chapter.ptx").write_text(
                    "<chapter><title>Different</title><p>Different prose.</p></chapter>",
                    encoding="utf-8",
                )
                self.assertEqual(check_ptx_consistency.main(), 1)
            finally:
                check_ptx_consistency.REPO_ROOT = original_root
                check_ptx_consistency.CHAPTER_PAIRS = original_pairs


if __name__ == "__main__":
    unittest.main()
