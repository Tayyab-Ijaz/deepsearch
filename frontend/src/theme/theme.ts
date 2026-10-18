import * as SecureStore from 'expo-secure-store';
import { createContext, createElement, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { Platform } from 'react-native';

export type ThemeMode = 'light' | 'dark';

type ThemeContextValue = { mode: ThemeMode; setMode: (mode: ThemeMode) => void };
const ThemeContext = createContext<ThemeContextValue>({ mode: 'light', setMode: () => {} });
const THEME_KEY = 'deepsearch.theme';

async function readMode(): Promise<ThemeMode | null> {
  try {
    const value = Platform.OS === 'web' ? globalThis.localStorage?.getItem(THEME_KEY) : await SecureStore.getItemAsync(THEME_KEY);
    return value === 'dark' || value === 'light' ? value : null;
  } catch { return null; }
}

async function writeMode(mode: ThemeMode): Promise<void> {
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.setItem(THEME_KEY, mode);
    else await SecureStore.setItemAsync(THEME_KEY, mode);
  } catch { /* Keep the choice for this session if storage is unavailable. */ }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>('light');
  useEffect(() => { void readMode().then((saved) => { if (saved) setModeState(saved); }); }, []);
  const setMode = useCallback((next: ThemeMode) => { setModeState(next); void writeMode(next); }, []);
  return createElement(ThemeContext.Provider, { value: { mode, setMode } }, children);
}

export function useThemeMode() { return useContext(ThemeContext); }

export type Theme = {
  dark: boolean;
  bg: string;
  card: string;
  label: string;
  secondary: string;
  tertiary: string;
  separator: string;
  fill: string;
  accent: string;
  green: string;
  orange: string;
  red: string;
};

const light: Theme = {
  dark: false,
  bg: '#F2F2F7',
  card: '#FFFFFF',
  label: '#000000',
  secondary: 'rgba(60,60,67,0.6)',
  tertiary: 'rgba(60,60,67,0.3)',
  separator: 'rgba(60,60,67,0.2)',
  fill: 'rgba(120,120,128,0.12)',
  accent: '#111111',
  green: '#34C759',
  orange: '#FF9500',
  red: '#FF3B30',
};

const dark: Theme = {
  dark: true,
  bg: '#0B0B0D',
  card: '#1C1C1E',
  label: '#F5F5F7',
  secondary: 'rgba(235,235,245,0.68)',
  tertiary: 'rgba(235,235,245,0.38)',
  separator: 'rgba(235,235,245,0.14)',
  fill: 'rgba(120,120,128,0.28)',
  accent: '#F5F5F7',
  green: '#30D158',
  orange: '#FF9F0A',
  red: '#FF453A',
};

export function useTheme(): Theme {
  return useThemeMode().mode === 'dark' ? dark : light;
}

export const type = {
  largeTitle: { fontSize: 34, fontWeight: '700' as const },
  title: { fontSize: 28, fontWeight: '700' as const },
  headline: { fontSize: 17, fontWeight: '600' as const },
  body: { fontSize: 17 },
  subhead: { fontSize: 15 },
  footnote: { fontSize: 13 },
  caption: { fontSize: 12 },
};
