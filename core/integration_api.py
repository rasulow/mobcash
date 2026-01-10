"""
Data Integration API Client
Handles requests to external data integration service with HMAC SHA256 authentication.
"""
import json
import logging
import hmac
import hashlib
import base64
from typing import TypeVar, Generic
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class IntegrationApiError(RuntimeError):
    """Raised when Integration API calls fail"""
    def __init__(self, message: str, error_code: str = "INTERNAL", status_code: int = 500):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


def generate_signature_from_string(data: str, private_key: str) -> str:
    final_data = data.replace(" ", "")
    signature_bytes = hmac.new(
        private_key.encode("utf-8"),
        final_data.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature_bytes).decode("utf-8")


def generate_signature(payload: dict, private_key: str) -> str:
    """
    Generate HMAC SHA256 signature for the request payload.
    
    Args:
        payload: Request payload dictionary
        private_key: Private key for signing
        
    Returns:
        Base64 encoded signature
    """
    # 1. Stringify the payload
    data = json.dumps(payload, separators=(',', ':'))
    return generate_signature_from_string(data, private_key)


class IntegrationClient:
    """Client for interacting with Data Integration API"""
    
    def __init__(
        self,
        base_url: str | None = None,
        public_key: str | None = None,
        private_key: str | None = None,
        timeout_s: int = 30
    ):
        self.base_url = (base_url or getattr(settings, "INTEGRATION_API_BASE", "")).rstrip("/")
        self.public_key = public_key or getattr(settings, "INTEGRATION_PUBLIC_KEY", "")
        self.private_key = private_key or getattr(settings, "INTEGRATION_PRIVATE_KEY", "")
        self.timeout_s = timeout_s
        
        if not self.base_url:
            raise ValueError("INTEGRATION_API_BASE must be configured in settings")
        if not self.public_key:
            raise ValueError("INTEGRATION_PUBLIC_KEY must be configured in settings")
        if not self.private_key:
            raise ValueError("INTEGRATION_PRIVATE_KEY must be configured in settings")
    
    def _make_request(self, endpoint: str, payload: dict) -> dict:
        """
        Make authenticated POST request to Integration API.
        
        Args:
            endpoint: API endpoint path (e.g., '/users', '/txns')
            payload: Request payload dictionary
            
        Returns:
            Response data dictionary
            
        Raises:
            IntegrationApiError: If request fails
        """
        endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        full_url = f"{self.base_url}{endpoint_path}"

        data = json.dumps(payload, separators=(",", ":"))
        signature = generate_signature_from_string(data, self.private_key)
        body = data.encode("utf-8")
        
        # Create request
        req = Request(
            full_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-key": self.public_key,
                "x-signature": signature,
                "User-Agent": "mobcash/1.0",
            },
        )
        
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Integration API call to {endpoint} succeeded: {response_data.get('statusCode')}")
                return response_data
                
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("error", {}).get("message", "Unknown error") if isinstance(error_data.get("error"), dict) else str(error_data.get("error", "Unknown error"))
                error_code = error_data.get("error", {}).get("errorCode", "HTTP_ERROR") if isinstance(error_data.get("error"), dict) else "HTTP_ERROR"
                status_code = error_data.get("statusCode", e.code)
            except (json.JSONDecodeError, AttributeError):
                error_msg = f"HTTP {e.code}: {error_body or e.reason}"
                error_code = "HTTP_ERROR"
                status_code = e.code
            
            logger.error(f"Integration API HTTP error for {endpoint}: {error_msg}")
            raise IntegrationApiError(error_msg, error_code, status_code) from e
            
        except (URLError, TimeoutError) as e:
            logger.error(f"Integration API network error for {endpoint}: {e}")
            raise IntegrationApiError(f"Network error: {e}", "NETWORK_ERROR", 503) from e
            
        except json.JSONDecodeError as e:
            logger.error(f"Integration API invalid JSON response for {endpoint}: {e}")
            raise IntegrationApiError("Invalid JSON response from Integration API", "INVALID_RESPONSE", 502) from e
    
    def get_users(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        last_updated: str | None = None,
        page_size: int = 100,
        skip: int = 0
    ) -> dict:
        """
        Retrieve users from Integration API.
        
        Args:
            start_date: Start date in ISO format (Option A)
            end_date: End date in ISO format (Option A)
            last_updated: Last updated timestamp in ISO format (Option B)
            page_size: Number of records per page (default 100)
            skip: Number of records to skip (default 0)
            
        Returns:
            Dictionary with count, pagesize, and result array
            
        Raises:
            IntegrationApiError: If request fails
        """
        payload = {
            "pagesize": page_size,
            "skip": skip,
        }
        
        if last_updated:
            payload["lastupdated"] = last_updated
        elif start_date and end_date:
            payload["startdate"] = start_date
            payload["enddate"] = end_date
        else:
            raise ValueError("Either (start_date and end_date) or last_updated must be provided")
        
        response = self._make_request("/users", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            if isinstance(error, dict):
                raise IntegrationApiError(
                    error.get("message", "Users request failed"),
                    error.get("errorCode", "USERS_ERROR"),
                    response.get("statusCode", 400)
                )
            else:
                raise IntegrationApiError(
                    str(error),
                    "USERS_ERROR",
                    response.get("statusCode", 400)
                )
        
        return response.get("data", {})
    
    def get_transactions(
        self,
        txn_type: str,
        start_date: str | None = None,
        end_date: str | None = None,
        last_updated: str | None = None,
        page_size: int = 100,
        skip: int = 0
    ) -> dict:
        """
        Retrieve transactions from Integration API.
        
        Args:
            txn_type: Transaction type ('casino', 'sports', 'deposit', 'withdraw')
            start_date: Start date in ISO format (Option A)
            end_date: End date in ISO format (Option A)
            last_updated: Last updated timestamp in ISO format (Option B)
            page_size: Number of records per page (default 100)
            skip: Number of records to skip (default 0)
            
        Returns:
            Dictionary with count, pagesize, and result array
            
        Raises:
            IntegrationApiError: If request fails
        """
        if txn_type not in ["casino", "sports", "deposit", "withdraw"]:
            raise ValueError("txn_type must be one of: casino, sports, deposit, withdraw")
        
        payload = {
            "type": txn_type,
            "pagesize": page_size,
            "skip": skip,
        }
        
        if last_updated:
            payload["lastupdated"] = last_updated
        elif start_date and end_date:
            payload["startdate"] = start_date
            payload["enddate"] = end_date
        else:
            raise ValueError("Either (start_date and end_date) or last_updated must be provided")
        
        response = self._make_request("/txns", payload)
        
        # Check for errors
        if response.get("error"):
            error = response["error"]
            if isinstance(error, dict):
                raise IntegrationApiError(
                    error.get("message", "Transactions request failed"),
                    error.get("errorCode", "TRANSACTIONS_ERROR"),
                    response.get("statusCode", 400)
                )
            else:
                raise IntegrationApiError(
                    str(error),
                    "TRANSACTIONS_ERROR",
                    response.get("statusCode", 400)
                )
        
        return response.get("data", {})


def get_integration_client() -> IntegrationClient:
    """Get a configured Integration API client instance"""
    return IntegrationClient()
