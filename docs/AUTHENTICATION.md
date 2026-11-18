# Authentication

The API uses bearer tokens issued by `/api/auth/register` and `/api/auth/login`.
Passwords are stored as PBKDF2-HMAC-SHA256 hashes with per-password salts. Tokens are signed with `AUTH_SECRET`, expire according to `AUTH_TOKEN_TTL_SECONDS`, and are revoked by incrementing the user's token version at logout.

Protected resources carry `owner_id` on users, personas, virtual friends, and staged imports. Private resources are only returned to their owner. The bundled demo persona may be read by any authenticated account, but cannot be deleted by another account.

## Local setup

Set a random secret in `backend/.env`:

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$env:AUTH_SECRET = [Convert]::ToBase64String($bytes)
```

For a persistent setup, put the value in the local environment file rather than relying on a shell-only variable. Never commit it.

Register or log in through the frontend at `/auth`, or call:

```powershell
Invoke-RestMethod http://localhost:8000/api/auth/register -Method Post -ContentType application/json -Body '{"email":"you@example.com","password":"a password with 12+ characters","display_name":"You"}'
```

Pass the returned `access_token` as `Authorization: Bearer <token>` to protected APIs.
