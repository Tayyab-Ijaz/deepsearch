import { getApp, getApps, initializeApp } from 'firebase/app';
import { getAuth, initializeAuth } from 'firebase/auth';
import type { Auth } from 'firebase/auth';
import { Platform } from 'react-native';

const config = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

export function getFirebaseAuth(): Auth {
  if (!config.apiKey || !config.authDomain || !config.projectId || !config.appId) {
    throw new Error('Add the Firebase Web App config to frontend/.env, then restart Expo.');
  }
  const app = getApps().length ? getApp() : initializeApp(config);
  if (Platform.OS === 'web') return getAuth(app);
  try {
    // Firebase Auth can still exchange native Google credentials; browser persistence is web-only.
    return initializeAuth(app);
  } catch {
    return getAuth(app);
  }
}
