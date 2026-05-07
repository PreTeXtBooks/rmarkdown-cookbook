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

            self.assertTrue(any("heading recall" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
