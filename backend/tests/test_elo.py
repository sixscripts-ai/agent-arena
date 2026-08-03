import pytest

from agent_arena.elo import INITIAL_RATING, K_FACTOR, expected_score, update_ratings


def test_constants():
    assert INITIAL_RATING == 1200.0
    assert K_FACTOR == 32.0


def test_expected_rating_is_symmetric_and_half():
    assert expected_score(1200, 1200) == pytest.approx(0.5)
    assert expected_score(1200, 1400) + expected_score(1400, 1200) == pytest.approx(1.0)


def test_win_raises_winner_rating():
    new_a, new_b = update_ratings(1200.0, 1200.0, 1.0)
    assert new_a > 1200.0
    assert new_b < 1200.0
    assert new_a + new_b == pytest.approx(2400.0, abs=0.1)


def test_draw_moves_toward_expected():
    new_a, new_b = update_ratings(1400.0, 1200.0, 0.5)
    assert new_a < 1400.0
    assert new_b > 1200.0


def test_loss_lowers_rating():
    new_a, _ = update_ratings(1200.0, 1200.0, 0.0)
    assert new_a < 1200.0
