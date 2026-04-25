import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_review_repository import RestaurantReviewRepository

logger = logging.getLogger(__name__)

_MIN = 1
_MAX = 5


class RestaurantReviewService:
    @staticmethod
    def set_my_review(
        user_id: UUID,
        restaurant_id: UUID,
        score: object,
    ) -> dict:
        if score is None or score is True or score is False:
            raise ValidationError(
                f"Score must be an integer between {_MIN} and {_MAX}.",
                {"score": f"Expected integer from {_MIN} to {_MAX}"},
            )
        if isinstance(score, float) and score.is_integer():
            score = int(score)
        if not isinstance(score, int) or score < _MIN or score > _MAX:
            raise ValidationError(
                f"Score must be an integer between {_MIN} and {_MAX}.",
                {"score": f"Expected integer from {_MIN} to {_MAX}"},
            )
        r = RestaurantRepository.get_by_id(restaurant_id)
        if not r:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        row = RestaurantReviewRepository.upsert(
            user_id=user_id, restaurant_id=restaurant_id, score=score
        )
        logger.info(
            "Review upsert: user_id=%s restaurant_id=%s score=%s",
            user_id,
            restaurant_id,
            score,
        )
        return {
            "restaurantId": str(restaurant_id),
            "userId": str(user_id),
            "score": row.score,
            "createdAt": row.created_at.isoformat(),
            "updatedAt": row.updated_at.isoformat(),
        }
