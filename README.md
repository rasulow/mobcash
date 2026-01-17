# MobCash (Django)

Starter Django web app with a mobile-friendly web interface (Bootstrap) for a simple “wallet + transactions” flow.

## Run the project (Windows / PowerShell)

### 1) Create venv + install deps

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

### 2) Create your environment file

```powershell
copy env.example .env
```

### 3) Run migrations

```powershell
.\.venv\Scripts\python manage.py migrate
```

### 4) Create a user (recommended: superuser)

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

### 5) Start the server

```powershell
.\.venv\Scripts\python manage.py runserver
```

Open:
- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
 - API Swagger: `http://127.0.0.1:8000/api/docs/`
 - API ReDoc: `http://127.0.0.1:8000/api/redoc/`

### External API (required for client search / sending balance)

By default it uses:
- `YILDIZTOP_API_BASE=https://yildiztop.com/api`

You can override it in `.env` if needed.

## Static files (production)

This project is configured with **WhiteNoise**, so after you run:

```powershell
.\.venv\Scripts\python manage.py collectstatic --noinput
```

the app can serve static files from `staticfiles/` (useful for simple deployments).

## What’s implemented

- Login/logout (Django auth)
- Responsive UI (Bootstrap 5 via CDN)
- Wallet per local user (stored `Wallet.balance`)
- Create transaction:
  - choose external client (searchable dropdown, referral token search)
  - if amount > wallet balance → show warning and do not send / do not store
  - if sent successfully → POST update-balance to external API, store transaction history, decrement wallet balance
- Dashboard showing wallet balance + latest transactions

## API (DRF + Swagger)

All API endpoints are available in Swagger:
- `GET /api/docs/` (Swagger UI)
- `GET /api/redoc/` (ReDoc)

### Auth header

Use header for protected endpoints:
- `Authorization: Bearer <access_token>`

### Roles

Roles are derived from `is_superuser` and Django groups:
- `superadmin`: `is_superuser=True`
- `main_cashier`: group `main_cashier`
- `cashier`: group `cashier`

### Authentication (JWT Bearer)

- `POST /api/auth/token/`: получить `access`/`refresh` + информацию о роли пользователя (`superadmin/main_cashier/cashier/user`)
- `POST /api/auth/token/refresh/`: обновить `access` по `refresh`
- `POST /api/auth/token/verify/`: проверить токен
- `POST /api/auth/password/change/`: сменить пароль текущего пользователя (все роли)
  - Body:

```json
{
  "old_password": "old",
  "new_password": "new",
  "new_password2": "new"
}
```

### Main API (`/api/`)

#### Wallets

- `GET /api/wallets/`: список всех кошельков
  - Access: `superadmin` или `main_cashier`
- `GET /api/wallets/me/`: мой кошелёк (баланс/валюта)
  - Access: любой авторизованный пользователь

#### Transactions

- `GET /api/transactions/`: список транзакций
  - Access:
    - обычный пользователь: только свои
    - `main_cashier` / `superadmin`: все (опционально `?user_id=...`)
- `GET /api/transactions/{id}/`: детали транзакции
  - Access: владелец или `main_cashier` / `superadmin`
- `POST /api/transactions/`: создать транзакцию (внешний вызов `update-balance`)
  - Body:

```json
{
  "referral_token": "abc123",
  "amount": "10.00",
  "type": "deposit",
  "note": "optional"
}
```

#### Wallet Transfers (main_cashier)

- `GET /api/wallet-transfers/`: список переводов кошельков
  - Access: только `main_cashier`
  - Optional filter: `?transaction_type=deposit|withdraw`
- `POST /api/wallet-transfers/`: перевод между локальными кошельками
  - Access: только `main_cashier`
  - Body:

```json
{
  "to_user_id": 456,
  "amount": "25.00",
  "transaction_type": "deposit"
}
```

Rules:
- recipient must be in group `cashier`
- cannot transfer to self
- cannot transfer to `superadmin` or `main_cashier` via this endpoint

### Cashier API (`/api/cashier/`)

- `POST /api/cashier/users/`: создать аккаунт **cashier**
  - Access: `main_cashier` или `superadmin`
  - Note: группа `cashier` ставится принудительно

### Admin API (`/api/admin/`)

#### Users

- `/api/admin/users/`:
  - `superadmin`: полный CRUD
  - `main_cashier`: `GET` list/retrieve + `POST` create **cashier**
    - Видимость: `main_cashier` видит только пользователей группы `cashier` (не видит `superadmin`)

#### Groups (superadmin)

- `GET/POST /api/admin/groups/`
- `GET/PATCH/PUT/DELETE /api/admin/groups/{id}/`

#### Wallets (superadmin)

- `GET /api/admin/wallets/`
- `POST /api/admin/wallets/`: создать кошелёк пользователю
- `PATCH/PUT /api/admin/wallets/{id}/`
- `GET /api/admin/wallets/me/`: мой кошелёк (superadmin)
- `POST /api/admin/wallets/me/increase-balance/`: увеличить баланс суперюзера
  - Body:

```json
{ "amount": "1000.00" }
```

#### Transactions (superadmin)

- `GET /api/admin/transactions/`
- `GET /api/admin/transactions/{id}/`

#### Wallet Transfers (superadmin)

- `GET /api/admin/wallet-transfers/`
- `GET /api/admin/wallet-transfers/{id}/`
- `POST /api/admin/wallet-transfers/`: перевод суперюзера -> `main_cashier`/`cashier` (deposit) или обратный (withdraw)
  - Body:

```json
{
  "to_user_id": 123,
  "amount": "50.00",
  "transaction_type": "deposit"
}
```

### SPM API (`/api/spm/`)

Access for deposit/withdraw/send-code:
- `superadmin`, `main_cashier`, `cashier` (JWT required)

- `POST /api/spm/deposit/`: депозит в SPM
  - Request (preferred):

```json
{
  "amount": 100,
  "userName": "test24",
  "txnId": "<TXN_ID>",
  "remarks": "Test Deposit"
}
```

  - Local wallet: уменьшается на `amount`

- `POST /api/spm/withdraw/send-code/`: отправить код подтверждения на email пользователя SPM
  - Request:

```json
{ "userName": "test24" }
```

  - Response returns `txnId` (UUID) which must be used in `/withdraw/`
  - Optionally returns `confirmationCode` in debug mode

- `POST /api/spm/withdraw/`: вывод из SPM (2-step)
  - Request:

```json
{
  "amount": 100,
  "userName": "test24",
  "txnId": "<TXN_ID>",
  "confirmationCode": "123456",
  "remarks": "Test Withdraw"
}
```

  - Local wallet: увеличивается на `amount` после успеха

- `POST /api/spm/deposit/get-status/`: статус депозита по `txnId`
- `POST /api/spm/get-by-username/`: получить пользователя SPM по `userName`
- `POST /api/spm/session/`: создать/удалить сессию
- `POST /api/spm/register/`: регистрация пользователя в SPM

### Integration API (`/api/integration/`)

Access: публичный (`AllowAny`), без JWT.

- `POST /api/integration/users/`: получить пользователей по date-range или lastupdated
- `POST /api/integration/txns/`: получить транзакции по `type` и date-range/lastupdated

## Next steps (typical for MobCash)

- Agent roles + customer management
- Integrations with payment providers
- Audit logs + limits + KYC


