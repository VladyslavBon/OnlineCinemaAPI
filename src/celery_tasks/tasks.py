import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from config.celery_config import celery_app
from database.models.accounts import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)
from database.session_postgresql import PostgresqlSessionLocal


logger = logging.getLogger(__name__)


@celery_app.task
def delete_expired_token():
    db: Session = PostgresqlSessionLocal()
    now = datetime.now(timezone.utc)

    try:
        db.execute(delete(ActivationTokenModel).where(ActivationTokenModel.expires_at < now))
        db.execute(delete(PasswordResetTokenModel).where(PasswordResetTokenModel.expires_at < now))
        db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.expires_at < now))

        db.commit()
    except Exception as error:
        db.rollback()

        raise RuntimeError(f"An error occurred while deleting tokens: {error}")
    finally:
        logger.warning("The process of deleting expired tokens has been completed.")
        db.close()
