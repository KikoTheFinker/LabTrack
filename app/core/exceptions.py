from fastapi import HTTPException, status


def raise_user_not_found():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


def raise_jwt_invalid_or_expired():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Please log in"
    )


def raise_invalid_credentials():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )