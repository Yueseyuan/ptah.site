import app.models
from app.database import engine, Base, SessionLocal
from app.models import User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()
existing = db.query(User).filter(User.email == "admin@cruelandassociates.site").first()
if existing:
    db.delete(existing)
    db.commit()

admin = User(
    email="admin@cruelandassociates.site",
    hashed_password=hash_password("CruelAdmin2024!"),
    full_name="System Admin",
    role="admin",
    is_active=True
)
db.add(admin)
db.commit()
db.close()
print("Admin user created successfully")
print("Email: admin@cruelandassociates.site")
print("Password: CruelAdmin2024!")
