# Building the iOS app (.ipa) with Xcode

DeepSearch AI is an Expo (React Native) app. The repo contains the JavaScript app and Expo config; Expo generates the
native Xcode project on your Mac with one command. The app talks to the live backend by default, so **a fresh clone
builds a working app with no `.env` file and no secrets**.

| | |
| --- | --- |
| Bundle ID | `com.deepsearchai.peoplefinder` |
| Version / build | `1.0.0` / `1` (in `frontend/app.json`) |
| Sign-in | Email and password only (with Forgot password) |
| Backend | `https://deepsearch-seven-xi.vercel.app` (built into release builds) |
| Public pages for App Store Connect | `/privacy`, `/terms`, `/support` on the backend address above |

## Needs

- A Mac with Xcode (the version Expo SDK 57 / React Native 0.86 requires, see the Expo docs for SDK 57) and the command line tools
- Node.js (current LTS) and CocoaPods (`brew install cocoapods`)
- An Apple Developer account, with the App ID `com.deepsearchai.peoplefinder` registered (Xcode can register it when you pick your team)

## Steps

```bash
git clone https://github.com/Tayyab-Ijaz/deepsearch.git
cd deepsearch/frontend
npm ci
npx expo prebuild --platform ios      # generates frontend/ios and runs pod install
open ios/*.xcworkspace
```

In Xcode:

1. Select the app target, then **Signing & Capabilities**: choose your **Team** and leave "Automatically manage signing" on. The bundle ID is already set.
2. Choose the scheme's build configuration **Release** (Product, Scheme, Edit Scheme, Run) and the destination **Any iOS Device (arm64)**.
3. **Product, Archive.**
4. In the Organizer: **Distribute App**, then **App Store Connect** (upload for TestFlight/review) or **Export** to get an `.ipa` file.

Notes:

- `frontend/ios` is generated and git-ignored. Do not edit it by hand. Change settings in `frontend/app.json` and run `npx expo prebuild --platform ios --clean` again.
- **For every new upload** increase `ios.buildNumber` in `frontend/app.json` (`"1"`, `"2"`, ...), then prebuild again. Change `version` for a new release.
- To point a build at another server, set `EXPO_PUBLIC_API_URL` (https) before `npx expo prebuild` and before archiving. Otherwise do nothing.
- Release builds only allow secure (https) connections, apart from local-network testing.

## Before submitting in App Store Connect

- **Privacy Policy URL:** `https://deepsearch-seven-xi.vercel.app/privacy`
- **Support URL:** `https://deepsearch-seven-xi.vercel.app/support`   **Support email:** `info@wellminddatasolutions.com`
- **App Privacy answers:** the app collects email address, name (optional) and a user ID, linked to the user, for app functionality. The names users search for are sent to third parties (Serper search, Google Gemini) and are not stored by us; answer the "Search History" question with that in mind. Saved profiles are stored per user. No tracking.
- **Review notes:** the app searches public web pages for a name, requires the user to confirm they are searching for themselves, someone who agreed, or a public figure, and offers in-app account deletion. Apple needs a **demo account**: create one in the app and enter its email and password under "App Review Information".
- **Screenshots, age rating and description** are done in App Store Connect.
- Review the wording of the Privacy Policy and Terms (`backend/app/pages.py`) with whoever is responsible for legal matters before release.

## After the first TestFlight install, check

Create an account, sign in, run a search (you should see about 20 results with pictures and a Show more button), save a profile,
tap **Forgot password?** (a code arrives from `info@wellminddatasolutions.com`), delete the test account.

## Who owns what (the backend is not part of the Xcode build)

- **Hosting:** Vercel project connected to this repo, Root Directory `backend`. Settings come from Vercel environment variables (`backend/.env.example` lists them). Pushing to `main` redeploys.
- **Database:** Cloud Firestore in the Firebase project `findrip-people-find-app`. Make sure the company account has the **Owner** role there; see `backend/FIREBASE_SETUP.md`.
- **Search and AI:** Serper (search and pictures) and Google Gemini (summaries), each with its own API key in Vercel. A search costs roughly 25 to 55 Serper requests; the depth can be reduced with `SEARCH_PAGES`, `IMAGE_PAGES` and `IMAGE_LOOKUPS`.
- **Email:** Resend, domain `wellminddatasolutions.com` (verified). The key is `RESEND_API_KEY` in Vercel.
- **No secrets in the app.** Never put the Firebase service account, Serper, Gemini or Resend keys in the app or in Git.

## Troubleshooting

- *"No profiles for com.deepsearchai.peoplefinder were found"*: register the App ID in the Apple Developer portal, or let Xcode do it by selecting your team.
- *`pod install` fails*: update CocoaPods, then `cd ios && pod repo update && pod install`.
- *Pictures or results missing in testing*: check `https://deepsearch-seven-xi.vercel.app/api/health` first.
- *The app cannot reach the server*: a debug build on a device defaults to `localhost`. Build the Release configuration, or set `EXPO_PUBLIC_API_URL`.
