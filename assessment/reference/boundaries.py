"""Option C level boundaries (Zein). Generic for any available total A and cap C."""
import statistics as st, math
def boundaries(marks, cap):
    """Option C: stats on marks capped at `cap`; range max(0, mean-3sd) .. cap split into 7 equal bands.
    Returns lower bounds for grades 2..7 (grade 7 has no upper limit)."""
    capped = [min(m, cap) for m in marks]
    mu, sd = st.mean(capped), st.pstdev(capped)
    lo, hi = max(0.0, mu - 3 * sd), float(cap)
    w = (hi - lo) / 7
    edges = [lo + k * w for k in range(1, 7)]
    return mu, sd, lo, w, edges, [math.ceil(e) for e in edges]
def grade(m, lows): return 1 + sum(m >= b for b in lows)
if __name__ == "__main__":
    # usage: python boundaries.py CAP mark1 mark2 ...
    import sys
    cap, marks = float(sys.argv[1]), [float(x) for x in sys.argv[2:]]
    mu, sd, lo, w, e, b = boundaries(marks, cap)
    print(f"mean {mu:.2f}  sd {sd:.2f}  floor {lo:.2f}  band {w:.2f}  lower bounds L2..L7 {b}")
