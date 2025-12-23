# MobCash (Django)

Starter Django web app with a mobile-friendly web interface (Bootstrap) for a simple “wallet + transactions” flow.

## Quickstart (Windows / PowerShell)

Create venv + install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Create your environment file:

```powershell
copy env.example .env
```

Run migrations + create admin user:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
```

Start the server:

```powershell
.\.venv\Scripts\python manage.py runserver
```

Open:
- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## What’s implemented

- Login/logout (Django auth)
- Responsive UI (Bootstrap 5 via CDN)
- Wallet model per user
- Transactions: deposit/withdraw with pending/approved/rejected status
- Simple dashboard showing balance + latest transactions

## Next steps (typical for MobCash)

- Agent roles + customer management
- Manual approval flow (agent/admin approves pending tx)
- Integrations with payment providers
- Audit logs + limits + KYC


