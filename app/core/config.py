import os

JWT_SECRET = os.getenv("JWT_SECRET", "dev_only_change_me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
