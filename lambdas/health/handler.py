import json


def _response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(payload),
    }


def handler(event, context):
    return _response(
        200,
        {
            "status": "ok",
            "service": "health",
        },
    )
