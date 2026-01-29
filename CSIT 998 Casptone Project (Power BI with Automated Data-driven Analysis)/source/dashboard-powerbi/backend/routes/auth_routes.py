"""
Auth routes.

- Register, login, logout, session validation
- Bearer token sessions, dependency-based protection
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Annotated
from models import auth_models as models

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """Summary: Registration payload.
    Fields: username, password, role('user'|'admin', default 'user')"""
    username: str
    password: str
    role: Optional[str] = 'user'


class LoginRequest(BaseModel):
    """Summary: Login payload.
    Fields: username, password"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Summary: Login result.
    Returns: {ok, token, user{id, username, role, created_at}}"""
    ok: bool
    token: str
    user: dict


class UserResponse(BaseModel):
    """Summary: User info wrapper.
    Returns: {ok, user}"""
    ok: bool
    user: dict


class MessageResponse(BaseModel):
    """Summary: Generic message wrapper.
    Returns: {ok, message}"""
    ok: bool
    message: str


def get_current_user(authorization: Annotated[str | None, Header()] = None):
    """Summary: Extract and validate current user from Bearer token.
    Args: Authorization: "Bearer <token>"
    Returns: {id, username, role, created_at}
    Raises: 401 on missing/malformed/invalid/expired token or missing user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing authentication token")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid authentication format")
    
    token = authorization[7:]
    
    session = models.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Unauthorized: Token invalid or expired")
    
    user = models.get_user_by_id(session['user_id'])
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: User does not exist")
    
    user_data = {
        'id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'created_at': user['created_at']
    }
    
    return user_data


@router.post("/register", response_model=MessageResponse)
async def register(req: RegisterRequest):
    """Summary: Register user with role validation.
    Validates username/password/role; hashes password; creates user.
    Raises: 400 on invalid input or duplicate username
    Returns: {ok, message}"""
    if not req.username or not req.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    if len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if req.role not in ['user', 'admin']:
        raise HTTPException(status_code=400, detail="Invalid role type")
    
    user = models.create_user(req.username.strip(), req.password, req.role)
    
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    return MessageResponse(ok=True, message="Registration successful")


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Summary: Login and issue bearer token.
    Validates credentials; returns {ok, token, user}. Raises: 400/401"""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password cannot be empty")
    
    user = models.get_user_by_username(req.username.strip())
    
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if not models.verify_password(req.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    token = models.create_session(user['id'])
    
    user_data = {
        'id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'created_at': user['created_at']
    }
    
    return LoginResponse(ok=True, token=token, user=user_data)


@router.post("/logout", response_model=MessageResponse)
async def logout(authorization: Annotated[str | None, Header()] = None):
    """Summary: Logout and invalidate session token.
    Safe if header missing. Returns: {ok, message}"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        models.delete_session(token)
    
    return MessageResponse(ok=True, message="Logout successful")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Summary: Get current user profile.
    Returns: {ok, user}. Raises: 401 (via dependency)"""
    return UserResponse(ok=True, user=current_user)


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Summary: Verify token validity.
    Returns: {ok, valid, user}. Raises: 401 (via dependency)"""
    return {"ok": True, "valid": True, "user": current_user}

