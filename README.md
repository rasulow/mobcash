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

## Next steps (typical for MobCash)

- Agent roles + customer management
- Integrations with payment providers
- Audit logs + limits + KYC


