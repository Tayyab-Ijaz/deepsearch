import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, ApiError, setSessionExpiredHandler } from './api';
import { getFirebaseAuth } from './firebase';
import { signOut as firebaseSignOut } from 'firebase/auth';
import { clearTokens, getRefreshToken, hasTokens, loadTokens, saveTokens } from './tokens';
import type { AuthSession, FeaturesResponse, MeResponse, Usage, User } from './types';

type Status = 'loading' | 'signedOut' | 'signedIn';

type AuthContextValue = {
  status: Status;
  user: User | null;
  usage: Usage | null;
  aiSummary: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  googleSignIn: (idToken: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  signOut: () => Promise<void>;
  deleteAccount: (password?: string) => Promise<void>;
  refreshUsage: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUser] = useState<User | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [aiSummary, setAiSummary] = useState(false);

  const reset = useCallback(() => {
    setUser(null);
    setUsage(null);
    setAiSummary(false);
    setStatus('signedOut');
  }, []);

  const loadProfile = useCallback(async () => {
    const me = await api.get<MeResponse>('api/auth/me');
    setUser(me.user);
    setUsage(me.usage);
    try {
      const features = await api.get<FeaturesResponse>('api/features');
      setAiSummary(features.ai_summary);
    } catch {
      setAiSummary(false);
    }
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(reset);
    (async () => {
      await loadTokens();
      if (!hasTokens()) {
        setStatus('signedOut');
        return;
      }
      try {
        await loadProfile();
        setStatus('signedIn');
      } catch (error) {
        // Expired: back to sign-in. Offline: stay signed in and load details later.
        if (error instanceof ApiError && error.sessionExpired) setStatus('signedOut');
        else setStatus('signedIn');
      }
    })();
    return () => setSessionExpiredHandler(null);
  }, [loadProfile, reset]);

  const finishSignIn = useCallback(
    async (session: AuthSession) => {
      await saveTokens(session.access_token, session.refresh_token);
      setUser(session.user);
      setStatus('signedIn');
      try {
        await loadProfile();
      } catch {
        // details load again on the next screen
      }
    },
    [loadProfile],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const session = await api.post<AuthSession>('api/auth/login', { email, password }, false);
      await finishSignIn(session);
    },
    [finishSignIn],
  );

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const session = await api.post<AuthSession>('api/auth/register', { email, password, display_name: displayName ?? null }, false);
      await finishSignIn(session);
    },
    [finishSignIn],
  );

  const googleSignIn = useCallback(
    async (idToken: string) => {
      const session = await api.post<AuthSession>('api/auth/firebase', { id_token: idToken }, false);
      await finishSignIn(session);
    },
    [finishSignIn],
  );

  const signOut = useCallback(async () => {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        await api.post('api/auth/logout', { refresh_token: refresh }, false);
      } catch {
        // signing out locally is enough
      }
    }
    await clearTokens();
    try { await firebaseSignOut(getFirebaseAuth()); } catch { /* email/password sessions may not have Firebase Auth */ }
    reset();
  }, [reset]);

  const deleteAccount = useCallback(
    async (password?: string) => {
      await api.del('api/auth/account', password ? { password } : {});
      await clearTokens();
      reset();
    },
    [reset],
  );

  const refreshUsage = useCallback(async () => {
    try {
      const me = await api.get<MeResponse>('api/auth/me');
      setUser(me.user);
      setUsage(me.usage);
    } catch {
      // the counter is a nice-to-have
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, usage, aiSummary, signIn, googleSignIn, register, signOut, deleteAccount, refreshUsage }),
    [status, user, usage, aiSummary, signIn, googleSignIn, register, signOut, deleteAccount, refreshUsage],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
