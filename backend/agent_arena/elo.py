INITIAL_RATING = 1200.0
K_FACTOR = 32.0


def expected_score(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def update_ratings(ra: float, rb: float, score_a: float) -> tuple[float, float]:
    ea = expected_score(ra, rb)
    new_a = ra + K_FACTOR * (score_a - ea)
    new_b = rb + K_FACTOR * ((1.0 - score_a) - (1.0 - ea))
    return round(new_a, 2), round(new_b, 2)
