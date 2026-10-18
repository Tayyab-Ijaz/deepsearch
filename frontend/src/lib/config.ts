export const APP_NAME = 'DeepSearch AI - People Finder';

/** The live server. Release builds (Xcode Archive, EAS) use this unless EXPO_PUBLIC_API_URL says otherwise. */
const PRODUCTION_URL = 'https://deepsearch-seven-xi.vercel.app';

/**
 * Server address. Development builds default to a server on this computer; release builds default to the live
 * server, so a build made from a fresh clone (no .env file) still works. Set EXPO_PUBLIC_API_URL to override (see .env.example).
 */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? (__DEV__ ? 'http://localhost:8000' : PRODUCTION_URL)).replace(/\/+$/, '');

// Public pages served by the backend. Use these in App Store Connect (Privacy Policy URL, Support URL).
export const PRIVACY_URL = `${PRODUCTION_URL}/privacy`;
export const TERMS_URL = `${PRODUCTION_URL}/terms`;
export const SUPPORT_URL = `${PRODUCTION_URL}/support`;
export const SUPPORT_EMAIL = 'info@wellminddatasolutions.com';
