import logging
import sys

from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies.db import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def seed_data(db: Session) -> None:

    # Using SQLAlchemy ORM Model
    # stmt = pg_insert(Advisor).values(SEED_ADVISORS).on_conflict_do_nothing(index_elements=["id"])
    # db.execute(stmt)

    db.commit()


def main() -> None:
    if settings.ENVIRONMENT == "production":
        logger.warning("Skipping seed_db: refusing to seed in production environment.")
        sys.exit(0)

    logger.info("Seeding database for environment '%s'...", settings.ENVIRONMENT)

    with SessionLocal() as db:
        seed_data(db)
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    main()
