# Tutoring Hub — guide for Claude

Owner: Abdelrahman Zein. He's an IBDP Mathematics teacher and tutor (AA and AI, SL and HL) and an experienced IB Group 5 examiner. Work at that level: assume he knows the syllabus and the IB marking conventions.

## The app today
- Static site on GitHub Pages: `index.html` (main app, ~3k lines), `tutor.html`, `s.html`, `join.html`, `sw.js`, `manifest.webmanifest`, icons, `.nojekyll`. There's no build step.
- Backend:
  - Google Apps Script web app (`script.google.com/macros/s/...`) backed by Google Sheets.
  - Cloudflare Worker at `tutoring-hub.abdelrahmanzein.workers.dev`.
  - **Neither backend's source is in this repo.** Ask before assuming its API.
- Client state: `fetch` and `localStorage`.

## ⚠️ This repo is PUBLIC
- Never commit student names, scans, marks or emails. Never commit fonts we don't hold a licence to redistribute (e.g. Apple's Noteworthy). Never commit API keys.
- Test data goes in `assessment/fixtures/` and stays anonymised ("Student A…J").
- Real student data lives in Sheets/Drive or the Worker's storage, never in git. `.gitignore` covers the usual private folders.
- Any Claude API key lives as a Worker secret. The browser never sees it.

## Assessment feature (in progress)
- Spec: `docs/assessment-feature.md`. Decisions and rejected options: `docs/assessment-decisions.md`.
- Reference implementation (Python): `assessment/reference/`. It produced the real marked scripts for an AA HL Functions Quiz (Oct 2026).
  - `boundaries.py` computes level boundaries.
  - `annotate.py` renders the on-page handwriting annotations and the cover page.
  - `test_boundaries.py` is the regression test.
- The marking skill is in `.claude/skills/ib-quiz-marking/SKILL.md`.

## Marking standard (follow strictly)
- Mark against the markscheme. If none is supplied, write one in IB format and get approval before marking (unless told "mark directly").
- Use IB notation:
  - M = method; A = accuracy, dependent on the preceding M; R = reasoning; AG = answer given; N = no working.
  - Marks in brackets, e.g. (M1), are implied by a correct answer.
  - Apply follow-through (FT). Credit correct alternative methods. Apply the 3 s.f. rule.
- Mark each script independently.
- Flag uncertain marks with ⚠️ for the teacher. Never guess at unreadable handwriting; say which line couldn't be read.

### Calibration rulings (from Zein's moderation, apply to every paper, any course or level)
1. "Show that" where the given answer isn't reached: method mark only (M1 A0).
2. Graph sketches need key features clearly shown: turning points are clear, and tails approach the asymptote. A wrong asymptote loses its mark.
3. A sketch inconsistent with the student's own working earns 0.
4. Transformations described as operations ("multiply by 2", "subtract 1") are not condoned. They must be named: reflect, translate, stretch, with factor/vector.
5. Condone errors caused by typos in the question paper.
6. Award M1 for a genuine attempt with the right structural feature (e.g. a symmetric shape for f(|x|)).
7. Parabola sketch M1 requires a symmetric shape. An intercept written on the axis scale counts as labelled.
8. Wrong or missing intercept labels lose the corresponding A1.
9. A correct final answer earns the implied bracketed marks.
10. Strict calls he upheld:
    - an open bracket where the endpoint is included → A0;
    - an axis of symmetry given as a number rather than "x = …" → A0;
    - an equation where an inequality was required gets only the (A1) for critical values.

## Grading model
- A quiz has **A available marks** but is **graded out of a cap C**, with A > C (reference quiz: 61 available, C = 40, 60 minutes). Why:
  1. Students choose questions and compensate for weaker topics.
  2. The teacher can include any suitable question.
  3. Most important, pacing. AA HL externals are 110 marks in 120 minutes; the DP1 target is 40 marks in 60 minutes. Strong students attempt the extras to practise exam pace.
- **Unattempted or missing questions are normal.** Never penalise them in tone, and never ask students for missing pages.
- **Boundaries (option C):**
  1. Cap every mark at C.
  2. Compute the mean μ and population SD σ of the capped marks.
  3. Split the range from max(0, μ − 3σ) to C into 7 equal bands.
  4. Round each lower bound up.
  5. Level 7 has no upper limit. Report the raw mark as is, e.g. 51/40 = 127.5%.
- Caveat: a weak class can end up with no 6s or 7s, because the top of the scale is fixed at C.

## Marked-script output (per student)
- **Cover page:**
  - raw mark "X / C", % of C, level, and "Raw mark X of A available · graded out of C";
  - a 7-box boundary strip with the student's level highlighted;
  - a per-question marks table, plus neutral notes (e.g. "Q3 not attempted. That's fine: aim for C marks, then attempt more as your pace builds.");
  - **What went well:** exactly 3 concepts with clear evidence of understanding;
  - **What to fix:** every concept with clear evidence of partial or no understanding;
  - **Next step:** re-solve every incorrect question by hand (any resource, but the student works every step and understands it), checking the markscheme after each question. Personalised notes and practice is future work; don't include it yet.
- **Pages:** examiner-style marks in red, handwriting font, written ON the page (never in a side margin).
  - Marks: M1/A1/A0/R0/AG stamps, ticks, crosses, wavy underlines, ringed part totals.
  - Short comments sit in free space, with an arrow to the error.
  - **No annotation may overlap another** (enforced and verified; the overlap count must be 0).
- If a script is disorganised (parts scattered), add one general comment on the cover.

## Every marking job also produces
- A **class report**:
  - lead summary, levels and boundaries (with rationale), moderation decisions table;
  - class summary with per-question means, most common errors, re-teach list in priority order;
  - academic-integrity signals (state the signals; never accuse);
  - teacher notes per student.
- **One folder** holding all marked PDFs plus the report PDF.

## Style
- Student-facing text: clear, supportive, direct English for 16–18-year-olds, often EAL learners.
- Teacher-facing text: blunt.
- No preamble. LaTeX for maths in documents.
