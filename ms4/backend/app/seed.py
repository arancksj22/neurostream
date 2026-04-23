from sqlalchemy import select

from .database import SessionLocal, Base, engine
from .models import User, Video, WorkflowStatusLog, CallbackEvent, DeletedVideoCleanupLog
from .security import hash_password


def main() -> None:
    # Ensure all models are known to SQLAlchemy
    _ = (User, Video, WorkflowStatusLog, CallbackEvent, DeletedVideoCleanupLog)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        email = "demo@neurostream.ai"
        existing = db.scalar(select(User).where(User.email == email))

        if existing:
            print("Demo user already exists.")
            return

        user = User(
            email=email,
            name="Demo User",
            password_hash=hash_password("DemoPassword123!"),
            role="USER",
        )
        db.add(user)
        db.flush()

        db.commit()
        print("Seeded demo user demo@neurostream.ai / DemoPassword123!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
