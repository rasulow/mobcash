# SPM API Integration Documentation

## Overview

This integration allows interaction with SPM (Sports Manager) for deposit and withdrawal transactions. The API uses symmetric AES encryption for secure data transmission and public/secret key authentication.

## Configuration

### Environment Variables

Add the following to your `.env` file:

```env
SPM_API_BASE=https://ext.sportsmanager.app
SPM_PUBLIC_KEY=7440094f-9295-4508-9c6a-bb8ebdf5bbe3
SPM_SECRET_KEY=Oml77xzoMofOG0ch4gzdciCc81c7Pc
```

### Required Dependencies

Install the PyCryptodome library for AES encryption:

```bash
pip install pycryptodome
```

## API Endpoints

### Base URL
All SPM endpoints are available under `/api/spm/`

### Authentication
All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

---

## Deposit Transaction

**Endpoint:** `POST /api/spm/deposit/`

Initiates a deposit transaction for a user in the SPM system.

### Request Body

```json
{
  "amount": 100.00,
  "country_code": "TM",
  "phone": "+99365123456",
  "remarks": "Test Deposit"
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | Decimal | Yes | Amount to deposit (in SPM currency) |
| `country_code` | String | Yes | User's country code (e.g., 'TM', 'UZ') |
| `phone` | String | Yes | User's phone number |
| `remarks` | String | No | Optional transaction remarks |

### Success Response

**Status Code:** `200 OK`

```json
{
  "balance": 1000.00,
  "txn_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Deposit successful"
}
```

### Error Response

**Status Code:** `400 Bad Request` / `502 Bad Gateway` / `503 Service Unavailable`

```json
{
  "error": {
    "message": "Error description",
    "errorCode": "ERROR_CODE"
  }
}
```

### Example cURL Request

```bash
curl -X POST https://your-domain.com/api/spm/deposit/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "country_code": "TM",
    "phone": "+99365123456",
    "remarks": "Test Deposit"
  }'
```

---

## Withdraw Transaction

**Endpoint:** `POST /api/spm/withdraw/`

Initiates a withdrawal transaction for a user in the SPM system.

### Request Body

```json
{
  "amount": 50.00,
  "country_code": "TM",
  "phone": "+99365123456",
  "remarks": "Test Withdrawal"
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | Decimal | Yes | Amount to withdraw (in SPM currency) |
| `country_code` | String | Yes | User's country code (e.g., 'TM', 'UZ') |
| `phone` | String | Yes | User's phone number |
| `remarks` | String | No | Optional transaction remarks |

### Success Response

**Status Code:** `200 OK`

```json
{
  "balance": 950.00,
  "txn_id": "550e8400-e29b-41d4-a716-446655440001",
  "message": "Withdrawal successful"
}
```

### Error Response

**Status Code:** `400 Bad Request` / `502 Bad Gateway` / `503 Service Unavailable`

```json
{
  "error": {
    "message": "Error description",
    "errorCode": "ERROR_CODE"
  }
}
```

### Example cURL Request

```bash
curl -X POST https://your-domain.com/api/spm/withdraw/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50.00,
    "country_code": "TM",
    "phone": "+99365123456",
    "remarks": "Test Withdrawal"
  }'
```

---

## Important Notes

### Currency Handling

⚠️ **The SPM system only supports one currency per project.**

- The `amount` sent must be in the currency you selected in the SPM System
- If your platform uses multiple currencies, you must convert to the SPM currency before depositing
- After withdrawal, convert back to your platform's currency

### Transaction IDs

- Transaction IDs are automatically generated as UUIDs
- Each transaction has a unique ID to prevent duplicates
- Store the `txn_id` from the response for reconciliation

### Error Codes

Common error codes you may encounter:

| Error Code | Description |
|------------|-------------|
| `DEPOSIT_ERROR` | Deposit transaction failed |
| `WITHDRAW_ERROR` | Withdrawal transaction failed |
| `NETWORK_ERROR` | Network connectivity issue |
| `INVALID_RESPONSE` | Invalid response from SPM |
| `HTTP_ERROR` | HTTP error from SPM API |
| `INTERNAL_ERROR` | Internal server error |

---

## Implementation Details

### Encryption

The integration uses AES-256-CBC symmetric encryption to secure payload data:

1. Request payload is serialized to JSON
2. JSON is encrypted using the secret key
3. Encrypted payload is sent to SPM with the public key in headers

### Client Usage

You can use the SPM client directly in your code:

```python
from core.spm_api import get_spm_client, SPMApiError
from decimal import Decimal

try:
    client = get_spm_client()
    balance = client.deposit(
        amount=Decimal("100.00"),
        country_code="TM",
        phone="+99365123456",
        txn_id="unique-txn-id",
        remarks="Test deposit"
    )
    print(f"New balance: {balance}")
except SPMApiError as e:
    print(f"Error: {e} (Code: {e.error_code})")
```

### Files Modified/Created

1. **`core/spm_api.py`** - SPM API client with encryption utilities
2. **`core/api/serializers.py`** - Added SPM transaction serializers
3. **`core/api/views.py`** - Added SPM transaction viewset
4. **`core/api/urls.py`** - Registered SPM endpoints
5. **`config/settings.py`** - Added SPM configuration
6. **`env.example`** - Added SPM environment variables

---

## Testing

### Using Swagger UI

1. Navigate to `/swagger/` or `/redoc/` in your browser
2. Authenticate using your JWT token
3. Find the SPM endpoints under the "spm" section
4. Test deposit/withdraw operations

### Using Python Requests

```python
import requests

# Get JWT token first
login_response = requests.post(
    "http://localhost:8000/api/auth/login/",
    json={"username": "your_username", "password": "your_password"}
)
token = login_response.json()["access"]

# Make deposit
deposit_response = requests.post(
    "http://localhost:8000/api/spm/deposit/",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "amount": 100.00,
        "country_code": "TM",
        "phone": "+99365123456",
        "remarks": "Test deposit"
    }
)
print(deposit_response.json())
```

---

## Security Considerations

1. **Never commit** the actual SPM keys to version control
2. Use environment variables for all sensitive configuration
3. Ensure HTTPS is enabled in production
4. Validate all user inputs before sending to SPM
5. Log all transactions for audit purposes
6. Monitor for unusual transaction patterns

---

## Support

For issues with the SPM integration, check:

1. SPM API credentials are correct in `.env`
2. Network connectivity to `https://ext.sportsmanager.app`
3. Request payload matches the expected format
4. JWT authentication is working properly

For SPM-specific issues, contact the SPM support team.
