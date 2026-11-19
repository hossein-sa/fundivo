"""Pure integer-IRR allocation helper for future per-partner installment snapshots.

No database writes or money transfers occur here.
"""


def split_amount_irr(total_irr: int, units: list[int], *, rotation: int = 0) -> list[int]:
    """Split integer IRR by 12 units, distribute indivisible rials fairly.

    For equal remainders the extra rials rotate between partners across rounds.
    The caller must keep a stable participant order (e.g. membership UUID sort)
    and persist the per-round result when installment models exist.
    """
    if not isinstance(total_irr, int) or isinstance(total_irr, bool) or total_irr < 0:
        raise ValueError("total_irr must be a nonnegative integer")
    if not units or any(
        not isinstance(unit, int) or isinstance(unit, bool) or not 1 <= unit <= 12
        for unit in units
    ):
        raise ValueError("units must be positive integers in 1..12")
    if sum(units) != 12:
        raise ValueError("participation units must total exactly 12")
    if not isinstance(rotation, int) or isinstance(rotation, bool) or rotation < 0:
        raise ValueError("rotation must be a nonnegative integer")

    portions = [divmod(total_irr * unit, 12) for unit in units]
    result = [base for base, _ in portions]
    remaining = total_irr - sum(result)
    count = len(units)
    # Highest fractional remainders first; cyclic order breaks exact ties.
    priority = sorted(
        range(count),
        key=lambda i: (-portions[i][1], (i - rotation) % count),
    )
    for i in priority[:remaining]:
        result[i] += 1
    return result
