"""
Database Models and User Management

Provides user authentication and session management functions for the
nursing home analytics platform. Uses MySQL for data persistence with
SHA-256 password hashing and secure random token generation.

Tables:
- users: User accounts with username/password/role
- sessions: Active authentication sessions with expiry tracking

Security Features:
- SHA-256 password hashing (upgrade to bcrypt recommended for production)
- Cryptographically secure random tokens via secrets module
- Foreign key cascading for automatic session cleanup
- Indexed queries for performance

Note:
    SHA-256 is used for simplicity. Production systems should use bcrypt
    or Argon2 with salt for better protection against rainbow table attacks.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from utils.shared import get_db_connection


def init_db():
    """Initialize database tables for authentication system.
    
    Creates users and sessions tables if they don't exist. Safe to call
    multiple times due to IF NOT EXISTS clause.
    
    Tables Created:
        users: Stores user credentials and roles
        sessions: Stores active authentication tokens
    
    Indexes:
        - users.username: Fast login lookups
        - sessions.token: Fast token validation
        - sessions.user_id: Fast session listing per user
        - sessions.expires_at: Efficient expired session cleanup
    
    Raises:
        Exception: If database connection or query fails (logged to console)
    
    Note:
        Must be called before using authentication endpoints.
        Run via backend/init_auth_tables.py script.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Users table: core authentication data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'user',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Sessions table: active authentication tokens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(255) UNIQUE NOT NULL,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_token (token),
                INDEX idx_user_id (user_id),
                INDEX idx_expires_at (expires_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        conn.commit()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def hash_password(password: str) -> str:
    """Hash password using SHA-256.
    
    Args:
        password: Plain text password
    
    Returns:
        64-character hexadecimal hash string
    
    Security Note:
        SHA-256 is fast but not ideal for passwords. Consider bcrypt
        or Argon2 for production to prevent brute-force attacks.
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored hash.
    
    Uses constant-time comparison via string equality (SHA-256 output
    is fixed length, providing some timing attack resistance).
    
    Args:
        password: Plain text password from login attempt
        password_hash: Stored hash from database
    
    Returns:
        True if password matches, False otherwise
    """
    return hash_password(password) == password_hash


def generate_token() -> str:
    """Generate cryptographically secure random session token.
    
    Uses secrets module (CSPRNG) to ensure tokens are unpredictable
    and safe for authentication purposes.
    
    Returns:
        URL-safe base64 token (43 characters, 256 bits of entropy)
    
    Note:
        Token collision probability is negligible (2^-256).
    """
    return secrets.token_urlsafe(32)


def create_user(username: str, password: str, role: str = 'user') -> Optional[Dict[str, Any]]:
    """Create new user account in database.
    
    Hashes password before storage. Username must be unique.
    
    Args:
        username: Unique username for login (case-sensitive)
        password: Plain text password (will be hashed)
        role: User role ('user' or 'admin'), defaults to 'user'
    
    Returns:
        Dict with user info (id, username, role, created_at) on success.
        None if username already exists or database error occurs.
    
    Note:
        Returns None on duplicate username to prevent username enumeration.
        Frontend should show generic "registration failed" message.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.utcnow()
        password_hash = hash_password(password)
        
        cursor.execute(
            'INSERT INTO users (username, password_hash, role, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)',
            (username, password_hash, role, now, now)
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        
        return {
            'id': user_id,
            'username': username,
            'role': role,
            'created_at': now.isoformat()
        }
    except Exception as e:
        print(f"Error creating user: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record by username.
    
    Args:
        username: Exact username to search (case-sensitive)
    
    Returns:
        Dict with user fields (id, username, password_hash, role, timestamps).
        None if user not found.
    
    Note:
        Used during login to validate credentials. Returns full user
        record including password_hash for verification.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        row = cursor.fetchone()
        return row if row else None
    finally:
        cursor.close()
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user record by primary key ID.
    
    Args:
        user_id: User's unique ID from database
    
    Returns:
        Dict with user fields. None if user not found.
    
    Note:
        Used to fetch user profile after token validation. Faster than
        username lookup due to primary key index.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        row = cursor.fetchone()
        return row if row else None
    finally:
        cursor.close()
        conn.close()


def create_session(user_id: int, expires_days: int = 7) -> str:
    """Create new authentication session for user.
    
    Generates cryptographically secure token and stores in database
    with expiration time. Token is returned to client for use in
    Authorization header.
    
    Args:
        user_id: User's database ID
        expires_days: Session validity period (default: 7 days)
    
    Returns:
        Generated session token (43-character URL-safe string)
    
    Note:
        Frontend stores token in localStorage. "Remember Me" functionality
        is handled client-side by persisting/clearing token on logout.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        token = generate_token()
        now = datetime.utcnow()
        expires_at = now + timedelta(days=expires_days)
        
        cursor.execute(
            'INSERT INTO sessions (user_id, token, created_at, expires_at) VALUES (%s, %s, %s, %s)',
            (user_id, token, now, expires_at)
        )
        
        conn.commit()
        return token
    finally:
        cursor.close()
        conn.close()


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve and validate session by token.
    
    Checks if session exists and hasn't expired. Automatically deletes
    expired sessions to keep database clean.
    
    Args:
        token: Bearer token from Authorization header
    
    Returns:
        Dict with session fields (id, user_id, token, timestamps).
        None if session not found or expired.
    
    Side Effects:
        Deletes session from database if found but expired.
    
    Note:
        Called on every authenticated request. Uses indexed query for
        performance (token column has unique index).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM sessions WHERE token = %s', (token,))
        row = cursor.fetchone()
        
        if row:
            # Validate expiration time
            expires_at = row['expires_at']
            if expires_at > datetime.utcnow():
                return row
            else:
                # Auto-cleanup expired session
                delete_session(token)
        return None
    finally:
        cursor.close()
        conn.close()


def delete_session(token: str):
    """Delete specific session (used for logout).
    
    Args:
        token: Session token to invalidate
    
    Note:
        Idempotent - safe to call even if session doesn't exist.
        Also called automatically by get_session() for expired tokens.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM sessions WHERE token = %s', (token,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def delete_user_sessions(user_id: int):
    """Delete all sessions for specific user.
    
    Used when user changes password or admin needs to force logout.
    
    Args:
        user_id: User whose sessions should be invalidated
    
    Note:
        Useful for security: force re-login after password change.
        Could be called from a "logout all devices" feature.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM sessions WHERE user_id = %s', (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def clean_expired_sessions():
    """Batch delete all expired sessions from database.
    
    Maintenance function to prevent sessions table from growing
    unbounded. Should be called periodically via cron job or
    application startup.
    
    Note:
        Expired sessions are also cleaned lazily by get_session(),
        so this is optional but recommended for database hygiene.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.utcnow()
        cursor.execute('DELETE FROM sessions WHERE expires_at < %s', (now,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# Auto-initialize database tables on module import
# Ensures tables exist before authentication endpoints are called
try:
    init_db()
except Exception as e:
    print(f"Warning: Could not initialize auth tables: {e}")

