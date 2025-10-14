import jwt
import requests
from typing import Dict, Optional
from fastapi import HTTPException
from config.settings import settings
import time
from functools import lru_cache

class Auth0Manager:
    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.audience = settings.AUTH0_AUDIENCE
        self.client_id = settings.AUTH0_CLIENT_ID
        self.client_secret = settings.AUTH0_CLIENT_SECRET
        self.algorithms = ["RS256"]
        self._jwks_cache = None
        self._jwks_cache_time = 0
        self._cache_duration = 3600  # 1 hour

    @lru_cache(maxsize=1)
    def get_jwks(self) -> Dict:
        """Get JSON Web Key Set from Auth0"""
        current_time = time.time()
        
        # Check if cache is still valid
        if (self._jwks_cache and 
            current_time - self._jwks_cache_time < self._cache_duration):
            return self._jwks_cache
        
        try:
            jwks_url = f"https://{self.domain}/.well-known/jwks.json"
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            self._jwks_cache = response.json()
            self._jwks_cache_time = current_time
            return self._jwks_cache
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch JWKS: {str(e)}"
            )

    def get_rsa_key(self, token: str) -> Optional[Dict]:
        """Extract RSA key from token header"""
        try:
            # Decode token header without verification
            unverified_header = jwt.get_unverified_header(token)
            
            # Get JWKS
            jwks = self.get_jwks()
            
            # Find matching key
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    return {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
            
            return None
            
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token header: {str(e)}"
            )

    async def validate_token(self, token: str) -> Dict:
        """Validate Auth0 JWT token and return user info"""
        try:
            # Get RSA key
            rsa_key = self.get_rsa_key(token)
            if not rsa_key:
                raise HTTPException(
                    status_code=401,
                    detail="Unable to find appropriate key"
                )

            # Construct the key for verification
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

            # Decode and verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )

            # Extract user information
            user_info = {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "email_verified": payload.get("email_verified", False),
                "name": payload.get("name"),
                "given_name": payload.get("given_name"),
                "family_name": payload.get("family_name"),
                "picture": payload.get("picture"),
                "nickname": payload.get("nickname"),
                "updated_at": payload.get("updated_at"),
                "aud": payload.get("aud"),
                "iss": payload.get("iss"),
                "iat": payload.get("iat"),
                "exp": payload.get("exp")
            }

            return user_info

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Token validation failed: {str(e)}"
            )

    async def get_user_info(self, token: str) -> Dict:
        """Get detailed user info from Auth0 userinfo endpoint"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"https://{self.domain}/userinfo",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch user info: {str(e)}"
            )

    def extract_user_id(self, user_info: Dict) -> str:
        """Extract clean user ID from Auth0 sub field"""
        sub = user_info.get("sub", "")
        # Remove auth0| prefix if present
        if sub.startswith("auth0|"):
            return sub[6:]
        return sub

# Create global instance
auth0_manager = Auth0Manager()
