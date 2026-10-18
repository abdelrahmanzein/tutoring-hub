# Assessment feature: spec

Goal: run the whole quiz loop in Tutoring Hub.

> submission → AI first-pass marking → teacher moderation → annotated scripts + cover pages → boundaries and levels → class report → grade records → personalised next steps.

The behaviour is defined by the reference implementation in `assessment/reference/` and by the rules in `CLAUDE.md`. Both were validated on a real class (10 scripts, AA HL Functions Quiz, Oct 2026).

## 1. Assessment setup (teacher)
- Create an assessment with these fields:
  - title, course (AA/AI), level (SL/HL), paper type, time;
  - **available marks A** and **cap C**;
  - per-question max marks (`questions` map, e.g. `{"1":5,…}`);
  - question paper PDF, markscheme PDF;
  - the group it is assigned to.
- Data shape: see `assessment/fixtures/quiz.json`.

## 2. Submission (student)
- Students upload photos or PDFs, possibly several files per student. One reference student sent two PDFs covering different questions.
- Pages are normalised to images (one PNG per page), ordered, and stored privately (Drive or Worker storage, not GitHub).
- Missing pages and unattempted questions are fine. Don't block submission and don't nag.

## 3. AI first pass (server-side)
- The Cloudflare Worker calls the Claude API. The key is stored as a Worker secret.
- Inputs: page images, markscheme, quiz config, calibration rulings (`CLAUDE.md`).
- Output per student, matching `assessment/fixtures/students.json`:
  - `per_question` marks;
  - `pages[].items` annotations;
  - `notes`;
  - `feedback.went_well` (3), `feedback.to_fix` (all), `feedback.resolve` (list of incorrect questions);
  - `uncertain` flags (⚠️) with reasons.
- Annotation item types (coordinates are % of page width/height):
  - `["r", y, label, got, max]`: ringed part total near the right edge at height y;
  - `["s", x, y, text]`: stamp (M1, A0, "(M1) A1", AG…);
  - `["t", x, y]`: tick; `["x", x, y]`: cross;
  - `["u", x1, x2, y]`: wavy underline;
  - `["c", ax|null, y, text]`: comment with an arrow to (ax, y), or a general comment if ax is null.
- Mark each script in a separate call so one script never anchors another.

## 4. Moderation screen (teacher)
- Show each page with the proposed annotations overlaid and the ⚠️ items listed first.
- The teacher can:
  - change a mark;
  - edit or move a comment;
  - add a ruling ("condone typo in Q8a").
- Log every change as before → final + ruling. These feed the report's "Moderation decisions" table.
- Rulings the teacher marks as "general" get appended to the calibration list for future papers.

## 5. Boundaries and levels
- Use option C (see `assessment/reference/boundaries.py` and its test). It's generic for any A and C:
  - cap the marks at C, take μ and σ (population);
  - range from max(0, μ − 3σ) to C in 7 equal bands, lower bounds rounded up;
  - level 7 is open-ended.
- Recompute whenever a moderated mark changes.

## 6. Rendering
- **Cover page**, as specified in `CLAUDE.md` ("Marked-script output"): mark, %, level, boundary strip, question table, notes, went well / to fix / next step, and a key to the marking notation.
- **Annotated pages:**
  - handwriting-style red ink on the page;
  - free-space detection on the page image: ink mask from a median-filtered background, then an integral-image box search;
  - a hard no-overlap constraint (dilated used-mask), with stamps nudged into free spots;
  - comments wrapped to 26–58% of page width, with a white patch only if the spot has ink, and an arrow if far from the anchor;
  - a verification pass where the overlap count must be 0.
- Port options (decide with Zein):
  - **(a)** JS in the browser with `pdf-lib` + canvas for the ink mask. No server needed, and it fits the static app. This is the recommended option.
  - **(b)** keep the Python renderer as a small separate service (Cloud Run etc.).
- Handwriting font: the reference used Apple's Noteworthy, which can't be redistributed. For the app, pick an OFL handwriting font close to Zein's hand (e.g. Caveat, Kalam or Patrick Hand), or let him upload his own font file. Check that "M1" doesn't read as "MI".

## 7. Class report
- Contents:
  - lead paragraph;
  - levels and boundaries with rationale;
  - moderation decisions;
  - class marks table with per-question mean and mean %;
  - most common errors, re-teach list in priority order;
  - academic integrity signals;
  - teacher notes per student.
- Export as PDF. Every marking job delivers one folder (or zip) holding all marked PDFs plus the report.

## 8. Grade records
- Store per student and per assessment:
  - raw total, per-question marks, level, boundaries used, date, the "to fix" concepts.
- Show the history on the student's page in the app, with level trend and recurring weak concepts.

## 9. Personalised next steps (future: not in v1)
- Today, Next step = "re-solve every incorrect question by hand, check the markscheme after each".
- Later, generate notes and a practice set covering every "to fix" concept for that student, at IB level with a markscheme, and track completion.

## Suggested build order
1. Data model + assessment setup + boundaries (port `boundaries.py` to JS, port the test).
2. Submission upload and page normalisation.
3. Worker endpoint for the AI first pass (structured JSON output).
4. Moderation screen.
5. Renderer port + cover page.
6. Class report + folder/zip export.
7. Grade history.
8. (Later) notes and practice.
