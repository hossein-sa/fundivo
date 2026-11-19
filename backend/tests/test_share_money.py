"""Pure proportional financial calculation: exact integer amounts, no floats."""

import pytest
from apps.shares.money import split_amount_irr


def test_halves_are_exact():
    assert split_amount_irr(900_000, [6, 6]) == [450_000, 450_000]


def test_thirds_sum_to_original_even_with_remainder():
    assert split_amount_irr(1_000_000, [4, 4, 4]) == [333_334, 333_333, 333_333]


def test_remnant_rotates_for_equal_partners():
    assert split_amount_irr(1_000_000, [4, 4, 4], rotation=1) == [333_333, 333_334, 333_333]
    assert split_amount_irr(1_000_000, [4, 4, 4], rotation=2) == [333_333, 333_333, 333_334]


def test_uneven_share_fractions():
    result = split_amount_irr(999_999, [6, 3, 3])
    assert sum(result) == 999_999
    assert max(result) - min(result) > 0


@pytest.mark.parametrize("total,units", [(1, [4, 4]), (-1, [6, 6]), (1.5, [6, 6]), (12, [0, 12]), (12, [])])
def test_invalid_amounts_or_units(total, units):
    with pytest.raises(ValueError):
        split_amount_irr(total, units)
