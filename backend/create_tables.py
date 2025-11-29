from app.database import Base, engine
from app.models import *

print("\n=== Creating PostgreSQL Tables ===\n")
Base.metadata.create_all(bind=engine)
print("\n=== Done! Tables successfully created ===\n")

