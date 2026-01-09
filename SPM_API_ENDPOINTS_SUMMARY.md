# SPM API Endpoints - Quick Reference

## All Available Endpoints

### 1. Deposit Transaction
**POST** `/api/spm/deposit/`
```json
{
  "amount": 100.00,
  "country_code": "TM",
  "phone": "+99365123456",
  "remarks": "Optional"
}
```
**Response:** `{ "balance": 1000.00, "txn_id": "...", "message": "..." }`

---

### 2. Withdraw Transaction
**POST** `/api/spm/withdraw/`
```json
{
  "amount": 50.00,
  "country_code": "TM",
  "phone": "+99365123456",
  "remarks": "Optional"
}
```
**Response:** `{ "balance": 950.00, "txn_id": "...", "message": "..." }`

---

### 3. Get Deposit Status
**POST** `/api/spm/deposit/get-status/`
```json
{
  "txn_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
**Response:** `{ "balance": 1000.00, "txn_id": "..." }`

---

### 4. Get User by Phone
**POST** `/api/spm/get-by-phone/`
```json
{
  "country_code": "TM",
  "phone": "+99365123456"
}
```
**Response:** `{ "balance": 1000.00, "user_name": "John1234569", "is_active": true }`

---

### 5. Session Management
**POST** `/api/spm/session/`
```json
{
  "user_id": "user123",
  "action": "create"  // or "destroy"
}
```
**Response (create):** `{ "session": "session_token_here", "message": "..." }`
**Response (destroy):** `{ "session": null, "message": "..." }`

---

## Authentication

All endpoints require JWT authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Error Response Format

```json
{
  "error": {
    "message": "Error description",
    "errorCode": "ERROR_CODE"
  }
}
```

## Common Error Codes

- `DEPOSIT_ERROR` - Deposit failed
- `WITHDRAW_ERROR` - Withdrawal failed
- `STATUS_ERROR` - Status check failed
- `USER_LOOKUP_ERROR` - User lookup failed
- `SESSION_ERROR` - Session management failed
- `NETWORK_ERROR` - Network issue
- `INVALID_RESPONSE` - Invalid SPM response
- `HTTP_ERROR` - HTTP error
- `INTERNAL_ERROR` - Internal server error

---

See `SPM_API_INTEGRATION.md` for complete documentation with examples.
