# Firebase setup

Cloud Firestore is the only persistent database. Firebase Admin credentials are required at startup; the API does not fall back to local SQLite. Account records, refresh tokens, daily usage, saved profiles, login-attempt counters and aggregate run metrics are stored in Firestore. The service-account key stays on the backend and must never be placed in the mobile app.

## Firestore and backend Admin SDK

1. In Firebase Console, create a Cloud Firestore database.
2. Under **Project settings → Service accounts**, generate a private key and keep the JSON private.
3. Save it as `backend/secrets/firebase-service-account.json` (this path is git-ignored).
4. Set `FIREBASE_PROJECT_ID` and `FIREBASE_CREDENTIALS=secrets/firebase-service-account.json` in `backend/.env`.
5. Install `backend/requirements.txt` and restart the API.

## Sign-in

The app uses email and password only. Accounts, password hashes and sessions are handled by this API and stored in Firestore; Firebase Authentication is not used, so no sign-in provider needs to be enabled in the Firebase console and the mobile app needs no Firebase configuration.

Do not paste the service-account JSON or private keys into chat or commit them. Firestore client rules should deny direct app access; reads and writes go through the API.

## Deploying the API on Vercel

1. Import the repository (`main` branch) and set the project **Root Directory** to `backend`. Vercel finds `app/main.py` automatically; `vercel.json` sets a 60 second function limit and `.python-version` selects Python 3.12.
2. Under **Project Settings → Environment Variables**, add the values from `.env.example` (see `.env.vercel` for a ready list). Put `FIREBASE_CREDENTIALS` as the service-account JSON on a single line. Leave `CORS_ORIGINS` empty and `DEBUG=false` for an iOS-only app.
3. Deploy, then open `https://<your-project>.vercel.app/api/health`. Set the same address (https) as `EXPO_PUBLIC_API_URL` in the EAS build environment.
4. In Firebase Console → Firestore → **TTL**, add two policies so short-lived records clean themselves up: collection `rate_limits` field `expires_at`, and collection `password_resets` field `delete_after`.
5. Deploy `firestore.rules` (they deny all direct client access; the API uses the Admin SDK).

## Password reset email

Forgot-password sends a 6-digit code by email through [Resend](https://resend.com).

1. Create a Resend account, add and verify the domain `wellminddatasolutions.com` (a few DNS records).
2. Create an API key and add it in Vercel as `RESEND_API_KEY`. The sender is `EMAIL_FROM` (default `DeepSearch AI <info@wellminddatasolutions.com>`; set it to `contact@…` if you prefer).
3. Redeploy. Until the key is set, the app's reset request answers "not available right now" instead of failing silently.

Codes expire after 15 minutes, work once, lock after 5 wrong tries, and are stored only as keyed hashes in the `password_resets` collection. A successful reset signs out every other device.
