# INDUSTRIA AI — Supabase Authentication Setup Guide

**Architecture:** Hybrid Authentication (Supabase GoTrue Auth + FastAPI Bearer JWT Verification + Neon PostgreSQL)  
**Standard:** PRD v1.2 §8.1 (Multi-tenancy & Organisation Isolation) & §13.2 (Authentication Flow)

---

## 1. Overview of the Hybrid Architecture

INDUSTRIA AI uses a **hybrid authentication architecture**:
- **When Supabase credentials are configured in `.env`:**
  - The React frontend uses `@supabase/supabase-js` to sign up, log in, manage sessions, and refresh tokens directly through Supabase Auth (GoTrue).
  - The frontend attaches the Supabase access token (`Bearer <supabase_jwt>`) to all API requests.
  - The FastAPI backend validates the Supabase token using either the project's `SUPABASE_JWT_SECRET` (fast local HS256 validation) or the Supabase Auth verification endpoint (`GET {SUPABASE_URL}/auth/v1/user`).
  - Upon successful validation, the backend resolves or auto-provisions the user in PostgreSQL, assigning them to their tenant `Organisation` and preserving multi-tenancy boundaries.
- **When Supabase credentials are omitted:**
  - The application automatically falls back to **Local Dev Auth mode**, using Argon2-hashed local passwords and HMAC-SHA256 JWTs so offline development and CI/CD test suites run without external dependencies.

---

## 2. Step-by-Step Configuration

### Step 1: Retrieve Your Supabase Credentials

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Navigate to **Project Settings** (gear icon in the bottom left) $\rightarrow$ **API**:
   - **Project URL:** Copy the URL (e.g. `https://xyzcompany.supabase.co`).
   - **Project API Keys:** Copy the `anon` / `public` key (e.g. `eyJhbGciOi...`).
3. Under the same **API** settings page (or **Configuration** $\rightarrow$ **JWT Settings** depending on Supabase UI version):
   - **JWT Secret:** Copy the JWT Secret string used to verify tokens.

---

### Step 2: Add Keys to `.env`

Open `.env` in the root of the project (or copy from `.env.example`) and add your values:

```bash
# Supabase Authentication (Backend API)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-public-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Supabase Authentication (Frontend Client)
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-public-key
```

> [!NOTE]
> Vite requires frontend environment variables to be prefixed with `VITE_`. Both the backend and frontend variables are read from the single root `.env` file.

---

### Step 3: Configure Supabase Auth Settings (Recommended for Dev)

In your Supabase project dashboard under **Authentication** $\rightarrow$ **Providers** $\rightarrow$ **Email**:
1. **Confirm email:** If testing locally, you may toggle off **"Confirm email"** to allow newly registered users to sign in immediately without clicking an email verification link.
   - *If "Confirm email" remains enabled:* The UI will display a notification informing the user to check their email for the activation link before signing in.
2. **Secure password:** Ensure minimum password length complies with PRD v1.2 (minimum 12 characters).

---

### Step 4: Restart Dev Servers

Restart both the FastAPI backend and Vite frontend to reload the new environment variables:

```powershell
# Terminal 1: Backend
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --port 8000 --reload

# Terminal 2: Frontend
npm --prefix frontend run dev
```

Open `http://localhost:3000/`. You will see the green **"⚡ Supabase Auth Active"** status badge in the authentication dialog!

---

## 3. How Multi-Tenancy & User Auto-Provisioning Works

When a new user signs up via Supabase:
1. Supabase creates the identity in `auth.users` with `email`, `id` (UUID), and `user_metadata`:
   - `full_name`: Lead engineer name.
   - `organisation_name`: Company / plant name.
2. On their first authenticated API request, the FastAPI dependency `get_current_user`:
   - Validates the Supabase JWT.
   - Looks up the user in the PostgreSQL `users` table.
   - If not found, auto-provisions an `Organisation` record (or links to the active organisation if `MULTI_ORG_ENABLED=false`) and creates the `User` record with role `ORG_ADMIN`.
   - All subsequent analyses, dataset uploads, and equipment models are partitioned strictly by `organisation_id`.

---

## 4. Verification Tests

To verify Supabase authentication logic programmatically:

```powershell
# Run the dedicated Supabase auth test suite
& ".\.venv\Scripts\python.exe" -m pytest backend/tests/test_supabase_auth.py -v

# Run the complete auth and multi-tenancy verification
& ".\.venv\Scripts\python.exe" -m pytest backend/tests/test_auth_and_tenancy.py -v
```

