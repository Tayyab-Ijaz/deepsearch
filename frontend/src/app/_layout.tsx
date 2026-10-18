import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, Platform, Text, View } from 'react-native';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { BrandMark } from '../components/BrandMark';
import { AuthProvider, useAuth } from '../lib/auth';
import { APP_NAME } from '../lib/config';
import { ThemeProvider, type, useTheme } from '../theme/theme';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AuthProvider><Navigator /></AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

function Navigator() {
  const { status } = useAuth();
  const t = useTheme();

  useEffect(() => {
    if (Platform.OS !== 'web' || typeof document === 'undefined') return;
    const styleId = 'deepsearch-autofill-theme';
    let style = document.getElementById(styleId) as HTMLStyleElement | null;
    if (!style) {
      style = document.createElement('style');
      style.id = styleId;
      document.head.appendChild(style);
    }
    style.textContent = `
      input:-webkit-autofill,
      input:-webkit-autofill:hover,
      input:-webkit-autofill:focus,
      textarea:-webkit-autofill,
      select:-webkit-autofill {
        -webkit-box-shadow: 0 0 0 1000px ${t.card} inset !important;
        box-shadow: 0 0 0 1000px ${t.card} inset !important;
        -webkit-text-fill-color: ${t.label} !important;
        caret-color: ${t.label} !important;
      }
    `;
    return () => style?.remove();
  }, [t.card, t.label]);

  if (status === 'loading') {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28, backgroundColor: t.bg }}>
        <StatusBar style={t.dark ? 'light' : 'dark'} />
        <View style={{ width: 104, height: 104, borderRadius: 30, alignItems: 'center', justifyContent: 'center', backgroundColor: t.card, shadowColor: '#000000', shadowOpacity: t.dark ? 0.3 : 0.08, shadowRadius: 20, shadowOffset: { width: 0, height: 8 }, elevation: 5 }}>
          <BrandMark size={66} />
        </View>
        <Text style={[type.title, { color: t.label, fontSize: 23, marginTop: 22, textAlign: 'center' }]}>{APP_NAME}</Text>
        <Text style={[type.subhead, { color: t.secondary, textAlign: 'center', marginTop: 5 }]}>Public profiles, clearer context.</Text>
        <View accessibilityRole="progressbar" accessibilityLabel="Preparing your workspace" style={{ flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: 28 }}>
          <ActivityIndicator size="small" color={t.accent} />
          <Text style={[type.caption, { color: t.secondary }]}>Preparing your workspace</Text>
        </View>
        <Text style={[type.caption, { color: t.tertiary, position: 'absolute', bottom: 28, letterSpacing: 0.8 }]}>SEARCH RESPONSIBLY · PUBLIC SOURCES ONLY</Text>
      </View>
    );
  }

  return (
    <>
      <StatusBar style={t.dark ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="privacy" />
        <Stack.Screen name="terms" />
        <Stack.Screen name="support" />
        <Stack.Screen name="review" />
        <Stack.Protected guard={status === 'signedIn'}>
          <Stack.Screen name="(tabs)" />
        </Stack.Protected>
        <Stack.Protected guard={status === 'signedOut'}>
          <Stack.Screen name="sign-in" />
          <Stack.Screen name="forgot-password" />
        </Stack.Protected>
      </Stack>
    </>
  );
}
