# External API Specification (to be implemented by another team)

This document describes the **external service API** that the MobCash Django app integrates with.

MobCash assumes the external service exposes a REST API at:

- `BASE_URL = https://yildiztop.com/api` (configurable via `YILDIZTOP_API_BASE`)

All requests/responses use **JSON**.

---

## 1) List users

### Endpoint

`GET /users`

### Query params

- `page` (optional, integer, default: `1`)
- `referral_token` (optional, string) — if present, server should filter users by this token.

### Response (success)

MobCash expects a Laravel-style pagination envelope (minimum required fields shown):

```json
{
  "success": true,
  "message": "Users retrieved successfully",
  "data": {
    "current_page": 1,
    "data": [
      {
        "id": 15,
        "name": "John Doe",
        "email": "john@example.com",
        "balance": "500.5",
        "referral_token": "694ae52f76f1c",
        "status": "1",
        "created_at": "2025-12-23T18:53:35.000000Z",
        "updated_at": "2025-12-23T20:53:45.000000Z",
        "image_url": "https://example.com/public/images/user-default.jpg"
      }
    ]
  }
}
```

### Notes / requirements

- `data.data` must be an array of users.
- `balance` may be a string or number, but should be parseable as decimal.
- `referral_token` must be present for each user (string).
- When `referral_token` query param is provided, it is acceptable to return either:
  - a single matching user in `data.data`, or
  - multiple matches (if tokens are not unique).

---

## 2) Update balance (delta-based)

### Endpoint

`POST /users/update-balance`

### Headers

- `Content-Type: application/json`
- `Accept: application/json`

### Request body

MobCash sends **a delta** in the `balance` field (signed number):

- **Deposit**: positive delta (e.g. `+100.00`)
- **Withdraw**: negative delta (e.g. `-100.00`)

Example deposit:

```json
{
  "referral_token": "694ae52f76f1c",
  "balance": 500.5
}
```

Example withdraw:

```json
{
  "referral_token": "694ae52f76f1c",
  "balance": -500.5
}
```

### Semantics

Server must:

1. Find the user by `referral_token`
2. Apply the delta:
   - `new_balance = old_balance + balance_delta`
3. Persist the new balance

### Validation rules

- `referral_token` is required and must map to an existing user
- `balance` is required and must be numeric (decimal)
- It is **recommended** to reject updates that would make balance negative:
  - if `old_balance + delta < 0`, return `422` with a validation error message

### Response (success)

MobCash only requires **HTTP 200** or **HTTP 204** to consider it successful.

Recommended response:

```json
{
  "success": true,
  "message": "Balance updated",
  "data": {
    "referral_token": "694ae52f76f1c",
    "old_balance": "1000.00",
    "delta": "-50.00",
    "new_balance": "950.00"
  }
}
```

### Response (errors)

MobCash treats non-2xx as error and will show a user-facing message.

Recommended errors:

- `404 Not Found` (unknown referral_token)
- `422 Unprocessable Entity` (validation failed; e.g. negative balance)
- `500 Internal Server Error` (server failure)

Example 422:

```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "balance": ["Insufficient funds"]
  }
}
```

---

## 3) Non-functional requirements

### Idempotency (recommended)

To avoid double-charging on retries, it is strongly recommended to support an idempotency key:

- Request header: `Idempotency-Key: <uuid>`

If implemented, the server should treat repeated requests with the same key as a single update.

### Rate limits

Recommended: allow at least ~5 requests/second per client IP, or document limits.

### Security (recommended)

Currently MobCash calls the external API without authentication. For production, consider adding:

- API key header (e.g. `X-API-Key`) or
- HMAC signature header

If authentication is required, MobCash must be updated to send those credentials.


