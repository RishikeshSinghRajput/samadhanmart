# SamadhanMart

SamadhanMart is a local marketplace and services portal for Bihar districts. The workspace contains a FastAPI + SQL Server backend and a separate React/Vite frontend.

## 1. Prepare SQL Server

1. Use Python 3.12–3.14 (recommended for current `pyodbc` Windows wheels), install Microsoft ODBC Driver 18 for SQL Server, and enable Windows Authentication access for the Windows account running FastAPI.
2. For a new database, open [backend/schema.sql](./backend/schema.sql) in SSMS connected to `LAPTOP-9S16DEOO` and execute it. The script creates `MultiServiceDB` when it does not exist and creates the tables and indexes idempotently.
   For an existing database, run [backend/migrate_approval_workflow.sql](./backend/migrate_approval_workflow.sql) to add approval/activity tracking, state/district fields, and the `Users.IsAdmin` flag. The migration maps existing `Role='admin'` rows to `IsAdmin=1`; other users remain `IsAdmin=0`.
3. Optionally run [backend/seed_demo.sql](./backend/seed_demo.sql) to create repeatable, linked demo records in all seven tables. It inserts demo electronics, OTP audit history, local chemist inventory and orders, advocates, and future consultation slots.

Run the seed only after the schema script, in SSMS with `MultiServiceDB` selected. The generated `DEMO-*` OTP log hashes are placeholders for audit-history examples, not usable codes; use the API to create a live listing and its real verification codes.

The default SQLAlchemy ODBC connection string is:

```text
DRIVER={ODBC Driver 18 for SQL Server};SERVER=LAPTOP-9S16DEOO;DATABASE=MultiServiceDB;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;
```

To point to another SQL Server, set `SQLSERVER_CONNECTION_STRING` before starting the backend.

## 2. Start the backend

From a PowerShell terminal in `backend`:

```powershell
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OTP_HASH_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:SAMADHAN_EXPOSE_MOCK_OTP = "true"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Generate `OTP_HASH_SECRET` locally; the API requires it to be at least 32 characters. To create an administrator, manually insert a row in `dbo.Users` using SSMS. From the workspace root, generate a password hash interactively:

```powershell
python .\backend\generate_admin_password_hash.py
```

Copy the printed hash (never the password) into the SQL below, replacing the sample identity values and `<PASTE_HASH_HERE>`. This assigns admin status only to the manually entered account; the database check constraint enforces that `Role='admin'` and `IsAdmin=1` stay in sync.

```sql
INSERT INTO dbo.Users
    (FullName, Role, Phone, Email, PasswordHash, IsAdmin, ApprovalStatus, State, District, ApprovedAt)
VALUES
    (N'SamadhanMart Administrator', 'admin', N'+919876543210',
     N'admin@example.com', N'<PASTE_HASH_HERE>', 1, 'APPROVED',
     N'Bihar', N'Siwan', SYSDATETIME());
```

Open **`http://localhost:5173/admin`** for the separate admin sign-in and dashboard. No admin link is displayed in the public marketplace, and the API checks the database role and `IsAdmin` flag on every protected request. Admin accounts are deliberately not created by the demo seed script. Sellers and advocates use **Seller / Advocate** to request registration; after admin approval, they can sign in there.

Seller/chemist and advocate registrations and marketplace location filters use dependent India-wide state and district dropdowns. Pending registrations cannot sign in or list medicines/electronics or appear as verified advocates until an admin approves them. Admin approvals and marketplace listing, order, and consultation events are recorded in `ActivityLogs`. Use `SAMADHAN_EXPOSE_MOCK_OTP=true` only for local development: when both delivery providers are in mock mode, the create-listing response includes the OTP so the verification flow can be tested without sending messages. Do not enable this in a publicly accessible deployment. Set `EMAIL_WEBHOOK_URL` and `WHATSAPP_WEBHOOK_URL` to provider/webhook endpoints to enable dispatch; each endpoint receives a JSON object containing `channel`, `recipient`, `message`, and `item_id`. Provider errors are recorded as `FAILED` dispatches.

The prescription upload endpoint accepts PDF, JPEG, and PNG files up to 10 MB and stores them under `backend/uploads/prescriptions`. Do not expose that directory as a public static folder; protect prescription access and add retention controls before production.

## 3. Start the frontend

In another PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Visit the Vite URL (normally `http://localhost:5173`). Set `VITE_API_URL` before `npm run dev` if the API is hosted somewhere other than `http://localhost:8000/api`. In production, set `VITE_API_URL` to the deployed API's `/api` URL when the frontend and backend use different domains. Without it, production uses the same-origin `/api` path.

## 4. Deploy on Vercel

The `backend` service uses `backend` as its root and `main:app` as its FastAPI entrypoint; Vercel installs dependencies from `backend/requirements.txt`. The `frontend` service builds the Vite app from `frontend`. Configure these environment variables in the Vercel project before deploying:

- `OTP_HASH_SECRET`: a unique random value of at least 32 characters. Generate it locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`; do not commit it.
- `SQLSERVER_CONNECTION_STRING`: a connection string for a SQL Server instance reachable from Vercel. The local Windows-authentication default is not suitable for Vercel; use a hosted database and an appropriate SQL login.
- `CORS_ORIGINS`: comma-separated deployed frontend origins when the frontend and API use different domains.
- `VITE_API_URL`: the deployed API's `/api` URL when the frontend and API use different domains. Set this in the frontend's Vercel project before building.

The API requires a hosted SQL Server and valid credentials to serve data. The API's `/api/health` endpoint checks application liveness only; it does not verify database connectivity. If Vercel still reports `FUNCTION_INVOCATION_FAILED`, inspect the deployment's Function Logs for the Python traceback: the generic error page does not identify whether startup failed due to a missing environment variable, dependency, or database driver.

## API overview

- `POST /api/electronics/create` — creates a pending listing and dispatches/mock-dispatches separate six-digit OTPs to email and WhatsApp.
- `POST /api/electronics/verify` — records every OTP attempt and publishes a verified listing only when both channel codes match; OTPs expire after 10 minutes and allow at most five attempts.
- `GET /api/electronics` — verified listings with optional `category`, `min_price`, `max_price`, and `district` filters.
- `GET /api/medicines` — available local stock with optional `district` and `search`.
- `POST /api/medicines/prescriptions` — validates and saves a prescription upload; returns a storage path for the order request.
- `POST /api/medicines/order` — atomically reserves available stock and records customer/prescription details.
- Medicine orders can optionally include a 30-, 60-, or 90-day chronic refill schedule; this records the next requested refill date for chemist follow-up (it does not automatically place a later order).
- `GET /api/advocates` — returns verified advocates; supports `specialization` (`Civil`, `Criminal`, `Corporate`, `Land Disputes`) and `district`.
- `POST /api/advocates/book` — reserves a future 30-minute consultation slot; SQL Server enforces one booking per advocate/slot.
- `GET /api/health` — API liveness check. Interactive API documentation is at `/docs`.
- `POST /api/auth/register` and `POST /api/auth/login` — seller/advocate registration request and approved-account sign-in.
- `GET /api/admin/requests` and `POST /api/admin/requests/{user_id}/decision` — admin-only request review and approval/rejection.
- `GET /api/admin/activity` — admin-only registration, listing, order, and booking activity log.

OTP values are HMAC-SHA256 hashed in SQL Server rather than stored as readable codes. Verification and dispatch events are recorded in `ItemVerificationLogs`.

## Production readiness

The sample portal includes basic password authentication and role-gated admin approval, but does not include payment processing or provider-specific webhook signing. Add deployment-grade session revocation, rate limiting, identity proofing, and prescription access controls before real customer or prescription data is used. Restrict CORS, use HTTPS, move uploads to private object storage, configure secrets through a secret manager, and apply database migrations/backups in production.
