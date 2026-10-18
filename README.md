# DeepSearch AI — People Finder

DeepSearch helps a person look for **public profile pages** associated with a name. It searches selected public websites, brings likely matches together, and lets a signed-in user save profiles or check whether a username appears to exist on public platforms. It is a discovery aid: a result is not proof that a page belongs to a particular person.

This repository has two parts:

- **Frontend:** an Expo and React Native app for web, iOS, and Android.
- **Backend:** a Python API that manages accounts, searches public web results, ranks matches, and optionally writes short AI summaries.

Both live on the `main` branch: the Expo app in `frontend/` and the API in `backend/`.

## What a user can do

- Create an account with email and password, or continue with Google through Firebase Authentication.
- Search a name, optionally adding a location to narrow the search.
- Review public results from LinkedIn, Instagram, Facebook, TikTok, X, and the wider web.
- Open public result pages, save results, and remove saved results.
- Check a username on public platforms. This feature is experimental: some platforms block automated requests, so “unchecked” does not mean that an account does not exist.
- Request an optional short summary of the search snippets. Summaries are not identity verification.

The app asks users to confirm that they are searching for themselves, someone who agreed, or a well-known public figure. It is designed for public-page discovery, not private account access, background checks, or sensitive-trait inference.

## How the parts fit together

```text
Expo app → DeepSearch API → Brave Search API or Serper API
                         ↘ Firebase Authentication / Cloud Firestore
                         ↘ Gemini API (optional summaries)
```

The frontend sends requests to the backend URL in `EXPO_PUBLIC_API_URL`. Search-provider keys, Gemini keys, Firebase Admin credentials, and the JWT signing secret belong on the backend only. The app does not need the private search-provider keys.

## Pricing and what one search costs

**Prices and published free offers below were checked on October 16, 2026.** Provider prices and free offers can change; use the linked provider pricing pages before budgeting or launching. Prices are in US dollars and exclude any applicable tax. Hosting, data transfer, and currency conversion are separate and are not included in the API estimates.

### One app search makes six web-search requests

The backend runs one query for each of six search areas (LinkedIn, Instagram, Facebook, TikTok, X, and general web). Therefore, an uncached search is usually **six provider requests**, not one. These requests run in parallel. A short-lived in-memory cache (15 minutes by default) can avoid repeating an identical provider query on the same running server; it is not a durable or shared cache across multiple server instances.

| Search provider | Published pricing / free offer | Approximate cost for one uncached app search (6 requests) |
| --- | --- | --- |
| **Serper** (Google results; default preference in the example configuration) | 2,500 free queries are advertised for new accounts. Prepaid packs: $50 / 50,000 ($1.00 per 1,000); $375 / 500,000 ($0.75 per 1,000); $1,250 / 2.5 million ($0.50 per 1,000); $3,750 / 12.5 million ($0.30 per 1,000). Paid pack credits are listed as valid for six months. | About **$0.006** at the $50 pack rate; then about **$0.0045**, **$0.003**, or **$0.0018** at the larger pack rates. The 2,500-query offer covers about **416 complete six-request searches**, with a few credits left over. |
| **Brave Search API** | $5 per 1,000 Search requests and $5 in monthly credits are advertised. | About **$0.03** before credits. $5 in credits covers about **166** complete six-request searches (with a small balance left). |

These estimates assume all six provider requests are new and successful. A cache hit can lower the cost; retries, provider billing rules, taxes, and optional features can change the final invoice. The backend's configurable accounting defaults are `$0.001` per Serper request and `$0.005` per Brave request, matching the published entry rates above; treat application metrics as estimates, not the provider's invoice.

### Optional image lookup

For each result, the backend first tries to read the page's Open Graph preview image. That uses the app's own request to the public result page and does not consume a search-provider credit, though it still uses backend bandwidth. Google Images fallback is **off by default**. If enabled, it can make an additional Serper Images request for each result that has no page preview (up to 30 results in the current configuration), so in the worst case it can add as many as 30 Serper requests to a search. Cached image queries can reduce that number. The code's search cost metric should not be treated as exact when this optional fallback is enabled alongside Brave; check provider usage dashboards for billing.

### Optional AI summary

The summary is a separate request to Gemini and is not included in the six-search estimate. The configured model is `gemini-3.5-flash-lite`. Google's published standard pricing lists a free tier and, beyond it, **$0.30 per million input tokens** and **$2.50 per million output tokens**. For scale, an illustrative summary using 1,000 input tokens and 100 output tokens would cost about **$0.00055** at those paid rates; the real amount depends on snippet length and generated output. There is no Google Search grounding in this app's summary request, so Google Search grounding fees do not apply to this call. Gemini free-tier eligibility and quotas depend on the Google AI account and current terms.

### Provider-free does not mean the whole app is free

The source code does not include API credits or establish whether a live hosted service is currently running. An operator must supply provider credentials and pay any usage above the providers' current free offers. The app also depends on hosting and Firebase. Firebase publishes no-cost allowances (for example, Firestore currently lists 50,000 reads and 20,000 writes per day, plus 1 GiB stored data for the Standard edition); usage beyond the applicable allowances may be billed under the selected Firebase/Google Cloud plan. Some hosting products require a billing plan even where usage stays within a no-cost quota. Confirm the actual project plan, region, billing account, and quotas before launch.

## Current built-in limits and behavior

- Each signed-in user is limited to **40 search actions per day** by default. Name searches and username checks both use this search-action allowance. The daily counter is an application limit, not a provider free quota.
- Each signed-in user is limited to **40 AI summaries per day** by default.
- Search results are capped at **30** by default. The six queries request up to 10 provider results each before ranking and deduplication.
- Search query results are cached in server memory for **15 minutes** by default. Cache is lost when the process restarts and is not shared between server replicas.
- Provider selection is automatic: use Brave when a Brave key is configured, otherwise Serper. You can explicitly configure a provider preference on the backend.
- Username checking directly requests public platform URLs; it does not call Brave/Serper and is reported as zero search-provider API cost. Platforms may block or change their pages, so results can be inconclusive.
- Email/password accounts, refresh tokens, saved results, usage counts, and aggregate run metrics are stored through Firebase Admin and Cloud Firestore. The local SQLite databases under `backend/app/data` are not the production persistence layer.
- The backend includes API endpoints for health, sign-up/sign-in, Google/Firebase sign-in, token refresh/logout, account deletion, saved results, name search, username checks, and summaries. Interactive API documentation is disabled unless backend `DEBUG=true`.

## Run locally

### 1. Set up Firebase

Create a Firebase project, enable Google sign-in if you want that option, and create a Cloud Firestore database. Follow [`backend/FIREBASE_SETUP.md`](backend/FIREBASE_SETUP.md). Keep the Firebase service-account JSON private and put it under `backend/secrets/`; never put it in the app or commit it.

### 2. Configure the backend

Copy `backend/.env.example` to `backend/.env`, then fill in the values. At minimum, set a strong random `JWT_SECRET`, `FIREBASE_PROJECT_ID`, and `FIREBASE_CREDENTIALS`. Add **at least one** of `BRAVE_API_KEY` or `SERPER_API_KEY` for people search. Add `GEMINI_API_KEY` only if you want AI summaries. Provider keys must remain in this backend environment file.

Install and start the API from the `backend` folder:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API health check is `http://localhost:8000/api/health`. For local interactive API docs, set `DEBUG=true`; then open `http://localhost:8000/docs`.

### 3. Configure the frontend

Copy `frontend/.env.example` to `frontend/.env`. Set `EXPO_PUBLIC_API_URL` to the address the device can reach (for a physical phone, `localhost` means the phone itself, so use your computer's local network address). Add the Firebase **web app config** values for sign-in. These frontend values are public app configuration; do not put private service-account or search-provider keys here.

Install and start from the `frontend` folder:

```bash
npm ci
npm start
```

For web use `npm run web`; for iOS and Android use the Expo development flow shown by `npm start`. Native Google sign-in may need platform OAuth client IDs and an Expo development build; see the example environment file and Firebase setup notes.

### Configuration quick reference

Backend settings are documented with comments in `backend/.env.example`. Important ones:

| Setting | Purpose |
| --- | --- |
| `JWT_SECRET` | Secret used to sign application access tokens. Use a long random value. |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS` | Firebase project and private Admin SDK credential location. |
| `BRAVE_API_KEY`, `SERPER_API_KEY` | One or both search provider credentials. |
| `SEARCH_PROVIDER` | `auto`, `brave`, or `serper`. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional AI summary service and model. |
| `ENABLE_AI_SUMMARY` | Turn optional summaries on or off. |
| `ENABLE_RESULT_IMAGES` | Fetch public page preview images (enabled by default). |
| `ENABLE_GOOGLE_IMAGES` | Paid Serper Images fallback for missing previews (disabled by default). |
| `DAILY_SEARCH_LIMIT`, `DAILY_SUMMARY_LIMIT` | Per-account daily application limits. |
| `CORS_ORIGINS` | Comma-separated allowed web frontend origins. |

Frontend settings are in `frontend/.env.example`; use `EXPO_PUBLIC_API_URL` and the `EXPO_PUBLIC_FIREBASE_*` values.

## Project layout

```text
frontend/   Expo Router screens, UI components, Firebase client, API client, assets
backend/    FastAPI application, search providers, ranking, Firebase storage, tests
```

## Privacy, accuracy, and safe use

Search results come from public web indexes and may be outdated, incomplete, or about a different person with the same name. Always open the source and verify independently. The app does not verify a person's identity. Do not use it to harass, stalk, discriminate, or make high-impact decisions.

Search and summary inputs are sent to the configured third-party providers (Brave or Serper, and Gemini when summaries are used). Read each provider's current privacy and data-retention terms before operating this service. Keep server credentials private, configure HTTPS and allowed CORS origins for production, and review the in-app privacy and terms pages before public release. Before publishing, finish the checklist in [Release checklist](#release-checklist).

## Release checklist

Values that are intentionally not filled in yet. Set them before building for the App Store:

| Item | Where | Status |
| --- | --- | --- |
| iOS bundle identifier (and matching Android package) | `frontend/app.json` → `ios.bundleIdentifier`, `android.package` | Set to `com.deepsearchai.peoplefinder`; the Apple App ID must be created with exactly this identifier |
| Backend URL | EAS environment variable `EXPO_PUBLIC_API_URL`, `https://` only (e.g. `eas env:create`) | Waiting for the Vercel deployment |
| Firebase web config + Google client IDs | EAS environment variables `EXPO_PUBLIC_FIREBASE_*`, `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`, `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` (create with `eas env:create`; not committed because this repository is public) | Copy the Firebase values from `frontend/.env` on the original machine, or from the Firebase console; Google client IDs still need to be created |
| Privacy Policy and Terms URLs | `PRIVACY_URL`, `TERMS_URL` in `frontend/src/lib/config.ts`, plus the App Store Connect listing | Pages not hosted yet; Apple requires a working privacy URL |
| Support email | `SUPPORT_EMAIL` in `frontend/src/lib/config.ts` | Set to `info@wellminddatasolutions.com` |

Backend on Vercel: set Root Directory to `backend`, add the variables from `backend/.env.example` in Project Settings, and follow the Vercel section of [`backend/FIREBASE_SETUP.md`](backend/FIREBASE_SETUP.md).

## Tests and checks

Backend tests are in `backend/tests` and can be run with `pytest` from `backend` after installing requirements. Frontend has a TypeScript check via `npm run typecheck` and a web export via `npm run build:web`.

## Pricing sources

- [Brave Search API pricing](https://brave.com/search/api/)
- [Serper pricing](https://serper.dev/)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Firebase pricing](https://firebase.google.com/pricing)
- [Firebase pricing plans and billing](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans)

