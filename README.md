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

### Authentication (JWT Bearer)

- `POST /api/auth/token/`: получить `access`/`refresh` + информацию о роли пользователя (`superadmin/main_cashier/cashier/user`)
- `POST /api/auth/token/refresh/`: обновить `access` по `refresh`
- `POST /api/auth/token/verify/`: проверить токен

Use header:
- `Authorization: Bearer <access_token>`

### Client API (for logged-in users)

- `GET /api/wallets/me/`: мой кошелёк (баланс/валюта)
- `GET /api/transactions/`: список транзакций (обычный пользователь — только свои; `main_cashier` и `superadmin` — все, можно фильтровать)
- `GET /api/transactions/{id}/`: детали транзакции (с проверкой прав)
- `POST /api/transactions/`: создать транзакцию (делает внешний запрос `update-balance` и сохраняет историю)
- `GET /api/wallet-transfers/`: список переводов кошельков (**только** `main_cashier`)
- `POST /api/wallet-transfers/`: перевод из кошелька кассира другому пользователю (**только** `main_cashier`)

### Cashier API (create cashier accounts)

- `POST /api/cashier/users/`: создать аккаунт **cashier** (доступ: `main_cashier` или `superadmin`, группа `cashier` ставится принудительно)

### Superadmin API (admin-only)

Доступ только для `is_superuser`:

- `GET/POST /api/admin/users/`, `GET/PATCH/PUT/DELETE /api/admin/users/{id}/`: управление пользователями (включая группы/пароль)
- `GET/POST /api/admin/groups/`, `GET/PATCH/PUT/DELETE /api/admin/groups/{id}/`: управление группами и permissions
- `GET /api/admin/wallets/`, `PATCH/PUT /api/admin/wallets/{id}/`: просмотр/редактирование кошельков
- `GET /api/admin/transactions/`, `GET /api/admin/transactions/{id}/`: просмотр всех транзакций
- `GET /api/admin/wallet-transfers/`, `GET /api/admin/wallet-transfers/{id}/`: просмотр всех переводов кошельков

## Next steps (typical for MobCash)

- Agent roles + customer management
- Integrations with payment providers
- Audit logs + limits + KYC


