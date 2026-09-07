from passlib.context import CryptContext
import bcrypt
# Initializing pass encryption object
pwd_context = CryptContext(schemes=['bcrypt'],deprecated='auto')

# Function that hashes password
def hash_password(password:str)->str:
    return pwd_context.hash(password)

# Function to verify password
def verify_password(plain:str,hashed:str)->str:
    return pwd_context.verify(plain,hashed)
