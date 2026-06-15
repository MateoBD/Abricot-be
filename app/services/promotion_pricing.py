"""Pure promo-pricing math, shared by every menu read path.

Read paths (customer catalog + owner menu detail) batch-fetch the active promos
targeting each item, then call `best_promo` to pick the single promo that gives
the lowest effective price. No DB, no I/O here -- just the discount arithmetic so
it can be unit-tested in isolation and reused wherever an effective price is
needed (orders, future cart pricing, etc.).
"""

from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import DiscountType
from app.models.promotion import PromotionModel

_CENTS = Decimal("0.01")
_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def apply_promo(price: Decimal, promo: PromotionModel) -> Decimal:
    """Effective price after one promo. Never below 0, rounded to cents.

    PERCENTAGE: clamp value to [0, 100]. FIXED_AMOUNT: subtract, floor at 0.
    FREE_ITEM: price drops to 0.
    """
    if promo.discount_type == DiscountType.PERCENTAGE:
        pct = max(_ZERO, min(promo.discount_value, _HUNDRED))
        result = price * (_HUNDRED - pct) / _HUNDRED
    elif promo.discount_type == DiscountType.FIXED_AMOUNT:
        result = price - promo.discount_value
    elif promo.discount_type == DiscountType.FREE_ITEM:
        result = _ZERO
    else:  # defensive: unknown type leaves base price untouched
        result = price
    return _quantize(max(_ZERO, result))


def best_promo(
    price: Decimal, promos: list[PromotionModel]
) -> tuple[Decimal, PromotionModel] | None:
    """Pick the promo yielding the lowest effective price (best for customer).

    Returns (effective_price, promo) or None when `promos` is empty. Ties keep
    the first promo seen.
    """
    best: tuple[Decimal, PromotionModel] | None = None
    for promo in promos:
        effective = apply_promo(price, promo)
        if best is None or effective < best[0]:
            best = (effective, promo)
    return best
