from jose import jwt,JWTError
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException, Depends,Request,status
from fastapi.security import OAuth2PasswordBearer

from passlib.context import CryptContext

import os 
from dotenv import load_dotenv
load_dotenv()

SECREAT_KEY = os.getenv("SECREAT_KEY")
ALGORITHM = os.getenv("ALGORITHM")
<<<<<<< HEAD
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
=======
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
>>>>>>> 611e85944e9256841998dcb1aa1f6ac0f9d15729



# Custom JWT token Checker
class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    
    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")
        if not token:
            return await super().__call__(request)
        return token
    
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/auth/login")

# Create Token
def create_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp":expire})

    return jwt.encode(to_encode,SECREAT_KEY,algorithm=ALGORITHM)


# Verify_token 
def verify_token(request:Request):
    try:
        token = request.cookies.get("access_token")
        if not token:
            return None

        
        payload = jwt.decode(token, SECREAT_KEY, algorithms=ALGORITHM)
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Token Access"
        )




# Bcrypt contxt set for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#get password to hash
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# verify password hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
