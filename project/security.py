from passlib.context import CryptContext

# Create a CryptContext object, which provides methods for hashing and verifying passwords.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    """
    Generate a hashed password from a plain-text password.
    
    This function uses bcrypt to securely hash the password, which is then returned for storage.
    
    Args:
        password (str): The plain-text password to hash.
    
    Returns:
        str: A hashed version of the password, suitable for secure storage in a database.
    """
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """
    Verify a plain-text password against the provided hashed password.
    
    Args:
        plain_password (str): The plain-text password to verify.
        hashed_password (str): The hashed password to verify against.
    
    Returns:
        bool: True if the verification succeeded, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
