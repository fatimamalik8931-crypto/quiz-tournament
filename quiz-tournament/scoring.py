"""Scoring: correctness + speed bonus, shared by practice and tournament modes."""


def compute_score(points, time_limit_seconds, time_ms, correct):
    """Award full points for a correct answer, plus up to +50% bonus for speed.

    A near-instant correct answer earns ~1.5x points; an answer that uses the
    full time limit earns exactly the base points. Wrong / unanswered = 0.
    """
    if not correct:
        return 0
    time_limit_ms = max(1, time_limit_seconds * 1000)
    time_taken = max(0, min(time_ms, time_limit_ms))
    speed_ratio = (time_limit_ms - time_taken) / time_limit_ms
    bonus = round(points * 0.5 * speed_ratio)
    return points + bonus
