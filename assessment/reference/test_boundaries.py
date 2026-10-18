"""Run: python -m pytest assessment/reference  (or python assessment/reference/test_boundaries.py)"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from boundaries import boundaries, grade

FIX = os.path.join(HERE, "..", "fixtures")

def test_reference_quiz():
    quiz = json.load(open(os.path.join(FIX, "quiz.json")))
    studs = json.load(open(os.path.join(FIX, "students.json")))
    marks = [s["total"] for s in studs]
    mu, sd, lo, w, edges, lows = boundaries(marks, quiz["cap"])
    assert round(mu, 1) == 29.5 and round(sd, 2) == 9.15 and round(lo, 2) == 2.06
    assert lows == [8, 13, 19, 24, 30, 35]
    assert [grade(m, lows) for m in marks] == [7, 7, 7, 7, 6, 6, 4, 4, 3, 3]
    for s in studs:
        assert sum(s["per_question"].values()) == s["total"]

def test_level7_open_ended_and_floor():
    lows = boundaries([10, 20, 30, 40, 55], 40)[5]
    assert grade(55, lows) == 7 and grade(0, lows) == 1
    assert boundaries([0, 40], 40)[2] == 0.0          # floor clipped at 0

if __name__ == "__main__":
    test_reference_quiz(); test_level7_open_ended_and_floor(); print("ok")
