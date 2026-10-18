import { useEffect, useRef, useState } from 'react';
import { Image, Pressable, Text, View } from 'react-native';
import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';
import { GoogleAuthProvider, signInWithCredential, signInWithPopup } from 'firebase/auth';
import { Platform } from 'react-native';
import { getFirebaseAuth } from '../lib/firebase';
import { type, useTheme } from '../theme/theme';

WebBrowser.maybeCompleteAuthSession();

const configuredIds = {
  web: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
  ios: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
  android: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
};
const hasValidClientId = (value: string | undefined) => Boolean(value && value.endsWith('.apps.googleusercontent.com') && !value.toLowerCase().startsWith('your-'));
const ids = {
  web: configuredIds.web || 'not-configured.apps.googleusercontent.com',
  ios: configuredIds.ios || 'not-configured.apps.googleusercontent.com',
  android: configuredIds.android || 'not-configured.apps.googleusercontent.com',
};

function googleErrorMessage(error: unknown): string {
  const code = error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';
  if (code.includes('popup-closed-by-user') || code.includes('cancelled')) return 'Google sign-in was cancelled.';
  if (code.includes('unauthorized-domain')) return 'Google sign-in is not enabled for this app address.';
  if (code.includes('operation-not-allowed')) return 'Google sign-in is currently unavailable. Please use email and password.';
  if (code.includes('network-request-failed')) return 'Check your internet connection and try Google sign-in again.';
  return 'Google sign-in could not be completed. Please try again.';
}

export function GoogleContinueButton({ onIdToken, onError, disabled = false }: {
  onIdToken: (token: string) => Promise<void>;
  onError: (message: string) => void;
  disabled?: boolean;
}) {
  const t = useTheme();
  const [working, setWorking] = useState(false);
  const handledResponse = useRef(false);
  const [request, response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: ids.web,
    webClientId: ids.web,
    iosClientId: ids.ios,
    androidClientId: ids.android,
    selectAccount: true,
  }, { scheme: 'deepsearch' });

  useEffect(() => {
    if (!response || response.type === 'cancel' || response.type === 'dismiss') {
      handledResponse.current = false;
      return;
    }
    if (response.type === 'error' && !handledResponse.current) {
      handledResponse.current = true;
      onError('Google sign-in could not be completed. Please try again.');
      return;
    }
    if (response.type !== 'success' || handledResponse.current) return;
    handledResponse.current = true;
    const googleIdToken = response.params?.id_token;
    if (!googleIdToken) {
      onError('Google sign-in could not be completed. Please try again.');
      return;
    }
    setWorking(true);
    void (async () => {
      const auth = getFirebaseAuth();
      const credential = GoogleAuthProvider.credential(googleIdToken);
      const result = await signInWithCredential(auth, credential);
      await onIdToken(await result.user.getIdToken());
    })().catch((error: unknown) => {
      onError(googleErrorMessage(error));
    }).finally(() => setWorking(false));
  }, [response, onIdToken, onError]);

  const missingIds = Platform.OS !== 'web' && (!hasValidClientId(configuredIds.web) || (Platform.OS === 'ios' && !hasValidClientId(configuredIds.ios)) || (Platform.OS === 'android' && !hasValidClientId(configuredIds.android)));
  const unavailable = disabled || working;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Continue Google"
      disabled={unavailable}
      onPress={() => {
        if (Platform.OS === 'web') {
          setWorking(true);
          onError('');
          void (async () => {
            const result = await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
            await onIdToken(await result.user.getIdToken());
          })().catch((error: unknown) => {
            onError(googleErrorMessage(error));
          }).finally(() => setWorking(false));
          return;
        }
        if (missingIds) {
          onError('Google sign-in is not available on this device yet. Please use email and password or contact support.');
          return;
        }
        if (!request) {
          onError('Google sign-in is not ready yet. Please try again in a moment.');
          return;
        }
        handledResponse.current = false;
        onError('');
        void promptAsync();
      }}
      style={({ pressed }) => ({ minHeight: 50, borderRadius: 999, borderWidth: 1, borderColor: t.separator, backgroundColor: t.card, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, opacity: pressed ? 0.78 : 1 })}>
      <View accessibilityElementsHidden style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' }}>
        <Image source={{ uri: 'https://developers.google.com/static/identity/images/g-logo.png' }} resizeMode="contain" style={{ width: 20, height: 20 }} />
      </View>
      <Text style={[type.subhead, { color: t.label, fontWeight: '700' }]}>Continue Google</Text>
    </Pressable>
  );
}
