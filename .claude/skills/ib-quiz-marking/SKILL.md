---
name: ib-quiz-marking
description: Mark an IBDP Maths quiz or test for a class against a markscheme: IB annotations, calibration rulings, option C level boundaries, annotated scripts with cover pages, a class report, and one output folder.
---

# IB quiz marking (Zein's standard)

Read `CLAUDE.md` first. It holds the marking standard, the calibration rulings, the grading model and the output rules. This skill is the procedure.

## Inputs
- Question paper and markscheme. If there is no markscheme, write one in IB format and wait for approval, unless told "mark directly".
- Available marks A, cap C, time allowed. Ask if not given.
- Student scripts (PDFs or photos; one student may send several files). Missing pages or questions are expected. Don't ask for them.

## Procedure
1. **Set up the quiz.** Write the quiz config in the shape of `assessment/fixtures/quiz.json`: questions map, A, C, title.
2. **Prepare the pages.** Convert every script to page PNGs (`pdftoppm -r 100`). Check the per-student page order.
3. **Mark each script independently**, applying the calibration rulings:
   - record per-part marks with the M/A/R/AG trail and implied (bracketed) marks;
   - ⚠️ every uncertain mark with a reason;
   - name any unreadable line rather than guessing.
4. **Annotate.** Write annotation items per page (`r`, `s`, `t`, `x`, `u`, `c`; coordinates in % of the page). Comments are short and student-facing, and say what the right idea is.
5. **Write the feedback:**
   - `went_well`: exactly 3 concepts with clear evidence of understanding;
   - `to_fix`: every concept with partial or no understanding;
   - `resolve`: every incorrect question/part.
   - Write neutral notes for unattempted questions.
6. **Moderate.** Present a table of ⚠️ marks to the teacher, apply the rulings, and log before → final + ruling. Add any new general ruling to `CLAUDE.md`.
7. **Set boundaries** with `assessment/reference/boundaries.py` (option C) on the final totals.
8. **Render** each student: `assessment/reference/annotate.py` (cover + on-page handwriting). Confirm `overlaps: 0`.
9. **Write the class report**:
   - lead, levels and boundaries with rationale, moderation decisions;
   - class summary with per-question mean and mean %;
   - most common errors, re-teach list in priority order;
   - integrity signals (no accusations);
   - teacher notes per student.
   - Export it to PDF.
10. **Deliver one folder**, `<Group> - <Quiz> - Marked (final)/`, holding `<Name> - <Quiz> - Marked.pdf` for each student plus the report PDF.
11. **Check:**
    - totals equal the sum of the parts;
    - levels match the boundaries;
    - spot-check rendered pages visually;
    - no student data is committed to git (the repo is public).
