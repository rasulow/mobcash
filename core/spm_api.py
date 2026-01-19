"""
SPM (Sports Manager) API Client
Handles deposit/withdraw transactions with symmetric encryption.
"""
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar, Generic
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import base64
import os

from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto.Util.Padding import pad, unpad

from django.conf import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class SPMResponse(Generic[T]):
    """Generic SPM API response wrapper"""
    error: dict | None
    data: T | None
    statusCode: int


class SPMApiError(RuntimeError):
    """Raised when SPM API calls fail"""
    def __init__(self, message: str, error_code: str = "INTERNAL", status_code: int = 500):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


def symmetric_encrypt(data: str, key: str) -> str:
    """
    Encrypt data using AES symmetric encryption (AES-256-CBC).
    Compatible with CryptoJS.AES.encrypt format.
    
    Args:
        data: String data to encrypt
        key: Secret key for encryption
        
    Returns:
        Base64 encoded encrypted string
    """
    passphrase = key.encode("utf-8")

    # OpenSSL-compatible format used by CryptoJS.AES.encrypt(passphrase)
    # base64( b"Salted__" + salt(8) + ciphertext )
    salt = os.urandom(8)

    d = b""
    last = b""
    while len(d) < 48:  # 32 bytes key + 16 bytes iv
        last = MD5.new(last + passphrase + salt).digest()
        d += last
    key_bytes = d[:32]
    iv = d[32:48]

    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))

    openssl_blob = b"Salted__" + salt + ct
    return base64.b64encode(openssl_blob).decode("utf-8")


def symmetric_decrypt(encrypted_data: str, key: str) -> str:
    """
    Decrypt AES encrypted data.
    
    Args:
        encrypted_data: Base64 encoded encrypted string
        key: Secret key for decryption
        
    Returns:
        Decrypted string
    """
    passphrase = key.encode("utf-8")

    combined = base64.b64decode(encrypted_data)
    if len(combined) < 16 or combined[:8] != b"Salted__":
        raise ValueError("Invalid encrypted data format")

    salt = combined[8:16]
    ciphertext = combined[16:]

    d = b""
    last = b""
    while len(d) < 48:
        last = MD5.new(last + passphrase + salt).digest()
        d += last
    key_bytes = d[:32]
    iv = d[32:48]

    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    decrypted_padded = cipher.decrypt(ciphertext)
    return unpad(decrypted_padded, AES.block_size).decode("utf-8")


class SPMClient:
    """Client for interacting with SPM API"""
    
    def __init__(
        self,
        base_url: str | None = None,
        public_key: str | None = None,
        secret_key: str | None = None,
        timeout_s: int = 10
    ):
        self.base_url = (base_url or getattr(settings, "SPM_API_BASE", "")).rstrip("/")
        self.public_key = public_key or getattr(settings, "SPM_PUBLIC_KEY", "")
        self.secret_key = secret_key or getattr(settings, "SPM_SECRET_KEY", "")
        self.timeout_s = timeout_s
        
        if not self.base_url:
            raise ValueError("SPM_API_BASE must be configured in settings")
        if not self.public_key:
            raise ValueError("SPM_PUBLIC_KEY must be configured in settings")
        if not self.secret_key:
            raise ValueError("SPM_SECRET_KEY must be configured in settings")
    
    def _make_request(self, url: str, payload: dict) -> dict:
        """
        Make encrypted POST request to SPM API.
        
        Args:
            url: API endpoint path (e.g., '/txn/user/deposit')
            payload: Request payload dictionary
            
        Returns:
            Response data dictionary
            
        Raises:
            SPMApiError: If request fails
        """
        full_url = f"{self.base_url}{url}"
        
        # Encrypt payload
        encrypted_payload = symmetric_encrypt(
            json.dumps(payload, separators=(",", ":")),
            self.secret_key
        )
        
        # Prepare request body
        body = json.dumps({"payload": encrypted_payload}).encode("utf-8")
        
        # Create request
        req = Request(
            full_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "ext-auth-pub": self.public_key,
                "User-Agent": "mobcash/1.0",
            },
        )
        
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"SPM API call to {url} succeeded: {response_data.get('statusCode')}")
                return response_data
                
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                error_code = error_data.get("error", {}).get("errorCode", "HTTP_ERROR")
                status_code = error_data.get("statusCode", e.code)
            except (json.JSONDecodeError, AttributeError):
                error_msg = f"HTTP {e.code}: {error_body or e.reason}"
                error_code = "HTTP_ERROR"
                status_code = e.code
            
            logger.error(f"SPM API HTTP error for {url}: {error_msg}")
            raise SPMApiError(error_msg, error_code, status_code) from e
            
        except (URLError, TimeoutError) as e:
            logger.error(f"SPM API network error for {url}: {e}")
            raise SPMApiError(f"Network error: {e}", "NETWORK_ERROR", 503) from e
            
        except json.JSONDecodeError as e:
            logger.error(f"SPM API invalid JSON response for {url}: {e}")
            raise SPMApiError("Invalid JSON response from SPM", "INVALID_RESPONSE", 502) from e
    
    def deposit(
        self,
        amount: Decimal,
        user_name: str,
        txn_id: str,
        remarks: str = ""
    ) -> Decimal:
        """
        Initiate a deposit transaction.
        
        Args:
            amount: Amount to deposit (in SPM currency)
            country_code: User's country code (e.g., 'TM', 'UZ')
            phone: User's phone number
            txn_id: Unique transaction ID
            remarks: Optional transaction remarks
            
        Returns:
            Updated balance after deposit
            
        Raises:
            SPMApiError: If deposit fails
        """
        payload = {
            "amount": float(amount),
            "userName": user_name,
            "txnId": txn_id,
            "remarks": remarks or f"Deposit {txn_id}",
        }
        
        response = self._make_request("/txn/user/deposit", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "Deposit failed"),
                error.get("errorCode", "DEPOSIT_ERROR"),
                response.get("statusCode", 400)
            )
        
        # Extract balance
        data = response.get("data", {})
        balance = data.get("balance")
        
        if balance is None:
            raise SPMApiError("No balance returned from deposit", "INVALID_RESPONSE", 502)
        
        return Decimal(str(balance))
    
    def withdraw(
        self,
        amount: Decimal,
        user_name: str,
        txn_id: str,
        remarks: str = ""
    ) -> Decimal:
        """
        Initiate a withdrawal transaction.
        
        Args:
            amount: Amount to withdraw (in SPM currency)
            country_code: User's country code (e.g., 'TM', 'UZ')
            phone: User's phone number
            txn_id: Unique transaction ID
            remarks: Optional transaction remarks
            
        Returns:
            Updated balance after withdrawal
            
        Raises:
            SPMApiError: If withdrawal fails
        """
        payload = {
            "amount": float(amount),
            "userName": user_name,
            "txnId": txn_id,
            "remarks": remarks or f"Withdraw {txn_id}",
        }
        
        response = self._make_request("/txn/user/withdraw", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "Withdrawal failed"),
                error.get("errorCode", "WITHDRAW_ERROR"),
                response.get("statusCode", 400)
            )
        
        # Extract balance
        data = response.get("data", {})
        balance = data.get("balance")
        
        if balance is None:
            raise SPMApiError("No balance returned from withdrawal", "INVALID_RESPONSE", 502)
        
        return Decimal(str(balance))
    
    def get_deposit_status(self, txn_id: str) -> Decimal:
        """
        Get the status of a deposit transaction.
        
        Args:
            txn_id: Transaction ID to check
            
        Returns:
            Current balance
            
        Raises:
            SPMApiError: If status check fails
        """
        payload = {
            "txnId": txn_id,
        }
        
        response = self._make_request("/txn/user/deposit/get-status", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "Status check failed"),
                error.get("errorCode", "STATUS_ERROR"),
                response.get("statusCode", 400)
            )
        
        # Extract balance
        data = response.get("data", {})
        balance = data.get("balance")
        
        if balance is None:
            raise SPMApiError("No balance returned from status check", "INVALID_RESPONSE", 502)
        
        return Decimal(str(balance))
    
    def get_user_by_phone(self, country_code: str, phone: str) -> dict:
        """
        Get user details by phone number.
        
        Args:
            country_code: User's country code (e.g., 'TM', 'UZ')
            phone: User's phone number
            
        Returns:
            Dictionary with user details: {balance, userName, isActive}
            
        Raises:
            SPMApiError: If user lookup fails
        """
        payload = {
            "countryCode": country_code,
            "phone": phone,
        }
        
        response = self._make_request("/txn/user/get-by-phone", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "User lookup failed"),
                error.get("errorCode", "USER_LOOKUP_ERROR"),
                response.get("statusCode", 400)
            )
        
        # Extract user data
        data = response.get("data", {})
        
        return {
            "balance": Decimal(str(data.get("balance", 0))),
            "userName": data.get("userName", ""),
            "isActive": data.get("isActive", False),
        }

    def get_user_by_userid(self, user_id: int) -> dict:
        """
        Get user details by userId.

        Args:
            user_id: User ID in SPM system

        Returns:
            Dictionary with user details: {balance, userName, isActive}

        Raises:
            SPMApiError: If user lookup fails
        """
        payload = {
            "userId": user_id,
        }

        response = self._make_request("/user/get-by-userid", payload)

        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "User lookup failed"),
                error.get("errorCode", "USER_LOOKUP_ERROR"),
                response.get("statusCode", 400)
            )

        # Extract user data
        data = response.get("data", {})

        return data

    def get_user_by_username(self, user_name: str) -> dict:
        """Get user details by userName."""
        payload = {
            "userName": user_name,
        }

        response = self._make_request("/user/get-by-username", payload)

        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "User lookup failed"),
                error.get("errorCode", "USER_LOOKUP_ERROR"),
                response.get("statusCode", 400),
            )

        return response.get("data", {})
    
    def register_user(
        self,
        names: str,
        user_name: str,
        email: str,
        country_code: str,
        phone: int,
        password: str
    ) -> dict:
        """
        Register a new user in SPM system.
        
        Args:
            names: User's full name
            user_name: Unique username
            email: User's email address
            country_code: Country code (e.g., '91', 'TM')
            phone: Phone number as integer
            password: User password (min 8 chars, must have capital & small letter, number, symbol)
            
        Returns:
            Dictionary with user details: {userId, userName, name}
            
        Raises:
            SPMApiError: If registration fails
        """
        payload = {
            "names": names,
            "userName": user_name,
            "email": email,
            "countryCode": country_code,
            "phone": phone,
            "password": password,
        }
        
        response = self._make_request("/user/register", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "User registration failed"),
                error.get("errorCode", "REGISTRATION_ERROR"),
                response.get("statusCode", 400)
            )
        
        # Extract user data
        data = response.get("data", {})
        
        return {
            "userId": data.get("userId"),
            "userName": data.get("userName"),
            "name": data.get("name"),
        }
    
    def manage_session(self, user_id: str, action: str) -> str | None:
        """
        Create or destroy a user session.
        
        Args:
            user_id: User ID in SPM system
            action: Either 'create' or 'destroy'
            
        Returns:
            Session token if action is 'create', None if action is 'destroy'
            
        Raises:
            SPMApiError: If session management fails
        """
        if action not in ["create", "destroy"]:
            raise ValueError("action must be 'create' or 'destroy'")
        
        payload = {
            "userId": user_id,
            "action": action,
        }
        
        response = self._make_request("/user/session", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            raise SPMApiError(
                error.get("message", "Session management failed"),
                error.get("errorCode", "SESSION_ERROR"),
                response.get("statusCode", 400)
            )
        
        # Extract session token
        data = response.get("data", {})
        session = data.get("session")
        
        return session


# Singleton instance
_spm_client: SPMClient | None = None


def get_spm_client() -> SPMClient:
    """Get or create singleton SPM client instance"""
    global _spm_client
    if _spm_client is None:
        _spm_client = SPMClient()
    return _spm_client
