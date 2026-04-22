def list_envelope(rows: list[dict], page: int = 1) -> dict:
    total = len(rows)
    return {
        "data": rows,
        "total": total,
        "page": page,
        "perPage": total if total > 0 else 1,
    }


def paginated_list_envelope(
    rows: list[dict], *, total: int, page: int, per_page: int
) -> dict:
    return {
        "data": rows,
        "total": total,
        "page": page,
        "perPage": per_page,
    }
