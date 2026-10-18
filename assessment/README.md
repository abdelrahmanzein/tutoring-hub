# assessment/

Reference implementation and fixtures for the quiz-marking feature. The spec is in `docs/assessment-feature.md`.

- `reference/boundaries.py`: option C level boundaries for any available-mark total A and cap C.
- `reference/annotate.py`: renders the cover page plus the on-page handwriting annotations, with no overlaps.
- `reference/test_boundaries.py`: regression test against the real class. Run it with `python3 assessment/reference/test_boundaries.py`.
- `fixtures/quiz.json`: config for the reference quiz (A = 61, C = 40).
- `fixtures/students.json`: 10 **anonymised** students (marks and feedback). Student J also has full page annotations; the scans themselves aren't included.

To render the scripts:

```bash
pip install reportlab pillow numpy scipy fonttools
HW_FONT_DIR=/path/to/handwriting-fonts \
python3 assessment/reference/annotate.py assessment/fixtures/quiz.json STUDENTS.json PAGE_DIR OUT_DIR
```

`HW_FONT_DIR` must contain `NoteworthyLight.ttf` and `NoteworthyBold.ttf`. On a Mac, extract them from `/System/Library/Fonts/Noteworthy.ttc`. Don't commit them. You can swap in another font by changing the two `registerFont` lines.

Keep real scans and outputs in `assessment/pages/` and `assessment/out/`. Both are git-ignored.
