import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const ACCESS = 'deepsearch.access';
const REFRESH = 'deepsearch.refresh';
const OPTIONS: SecureStore.SecureStoreOptions = { keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY };

const memory: { access: string | null; refresh: string | null } = { access: null, refresh: null };

// Phones use the Keychain / Keystore. The web has no secure storage, so it falls back to localStorage.
async function read(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  }
  try {
    return await SecureStore.getItemAsync(key, OPTIONS);
  } catch {
    return null;
  }
}

async function write(key: string, value: string | null): Promise<void> {
  if (Platform.OS === 'web') {
    try {
      if (value === null) globalThis.localStorage?.removeItem(key);
      else globalThis.localStorage?.setItem(key, value);
    } catch {
      // storage blocked: keep going with the in-memory copy
    }
    return;
  }
  try {
    if (value === null) await SecureStore.deleteItemAsync(key, OPTIONS);
    else await SecureStore.setItemAsync(key, value, OPTIONS);
  } catch {
    // keep going with the in-memory copy
  }
}

export async function loadTokens(): Promise<void> {
  memory.access = await read(ACCESS);
  memory.refresh = await read(REFRESH);
}

export async function saveTokens(access: string, refresh: string): Promise<void> {
  memory.access = access;
  memory.refresh = refresh;
  await Promise.all([write(ACCESS, access), write(REFRESH, refresh)]);
}

export async function clearTokens(): Promise<void> {
  memory.access = null;
  memory.refresh = null;
  await Promise.all([write(ACCESS, null), write(REFRESH, null)]);
}

export const getAccessToken = () => memory.access;
export const getRefreshToken = () => memory.refresh;
export const hasTokens = () => memory.refresh !== null;
