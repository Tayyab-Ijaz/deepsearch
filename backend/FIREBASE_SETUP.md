# Firebase setup

Cloud Firestore is the only persistent database. Firebase Admin credentials are required at startup; the API does not fall back to local SQLite. Account records, refresh tokens, daily usage, and aggregate run metrics are stored in Firestore. The service-account key stays on the backend and must never be placed in the mobile app.

## Firestore and backend Admin SDK

1. In Firebase Console, create a Cloud Firestore database.
2. Under **Project settings → Service accounts**, generate a private key and keep the JSON private.
3. Save it as `backend/secrets/firebase-service-account.json` (this path is git-ignored).
4. Set `FIREBASE_PROJECT_ID` and `FIREBASE_CREDENTIALS=secrets/firebase-service-account.json` in `backend/.env`.
5. Install `backend/requirements.txt` and restart the API.

## Google Continue with Firebase Authentication

1. In Firebase Console, open **Authentication → Sign-in method** and enable **Google**. Set the support email and save.
2. In **Project settings → General → Your apps**, register a **Web app** if there is not one already. Copy its Firebase web config values (`apiKey`, `authDomain`, `projectId`, and `appId`) to `frontend/.env` as `EXPO_PUBLIC_FIREBASE_API_KEY`, `EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN`, `EXPO_PUBLIC_FIREBASE_PROJECT_ID`, and `EXPO_PUBLIC_FIREBASE_APP_ID`.
3. Restart Expo after changing environment values. The web app uses Firebase's Google provider popup; no separate Google OAuth client ID is entered in the backend.
4. The mobile app exchanges its Google credential with Firebase, then sends a Firebase ID token to the API. The API verifies that token with Firebase Admin before creating a Firestore-backed application session.

For native iOS/Android builds, Expo's browser-based Google flow also needs the platform OAuth client IDs in `frontend/.env` (`EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` plus the matching Android or iOS client ID). These are public client identifiers, not client secrets, and are not backend settings. For an Expo Go browser session, Google OAuth redirect restrictions may require a development build with the app's configured scheme.

Do not paste the service-account JSON or private keys into chat or commit them. Firestore client rules should deny direct app access; reads and writes go through the API.

## Deploying the API on Vercel

1. Import the repository (`main` branch) and set the project **Root Directory** to `backend`. Vercel finds `app/main.py` automatically; `vercel.json` sets a 60 second function limit and `.python-version` selects Python 3.12.
2. Under **Project Settings → Environment Variables**, add the values from `.env.example` (see `.env.vercel` for a ready list). Put `FIREBASE_CREDENTIALS` as the service-account JSON on a single line. Leave `CORS_ORIGINS` empty and `DEBUG=false` for an iOS-only app.
3. Deploy, then open `https://<your-project>.vercel.app/api/health`. Set the same address (https) as `EXPO_PUBLIC_API_URL` in the EAS build environment.
4. In Firebase Console → Firestore → **TTL**, add a policy on collection `rate_limits` for field `expires_at` so login-attempt records clean themselves up.
5. Deploy `firestore.rules` (they deny all direct client access; the API uses the Admin SDK).
