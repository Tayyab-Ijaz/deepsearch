import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SymbolView } from 'expo-symbols';
import { useRouter } from 'expo-router';
import { BrandMark } from '../components/BrandMark';
import { BusyOverlay, Button, ErrorText, Group, IconField } from '../components/ui';
import { APP_NAME } from '../lib/config';
import { useAuth } from '../lib/auth';
import { errorText } from '../lib/api';
import { haptic } from '../lib/utils';
import { type, useTheme } from '../theme/theme';

type Mode = 'signIn' | 'register';

export default function SignIn() {
  const t = useTheme();
  const router = useRouter();
  const { signIn, register } = useAuth();
  const [mode, setMode] = useState<Mode>('signIn');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const emailRef = useRef<TextInput>(null);
  const passwordRef = useRef<TextInput>(null);
  const valid = email.includes('@') && password.length > 0 && (mode === 'signIn' || password.length >= 8);

  async function submit() {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      const cleanEmail = email.trim().toLowerCase();
      if (mode === 'signIn') await signIn(cleanEmail, password);
      else await register(cleanEmail, password, name.trim() || undefined);
      haptic('success');
    } catch (e) {
      haptic('error');
      setError(errorText(e));
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: t.bg }}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', padding: 24, width: '100%', maxWidth: 480, alignSelf: 'center' }}>
        <View style={{ alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <BrandMark size={80} />
          <Text style={[type.title, { color: t.label, textAlign: 'center' }]}>{APP_NAME}</Text>
          <Text style={[type.subhead, { color: t.secondary, textAlign: 'center' }]}>
            Find public profiles and check usernames and links, responsibly.
          </Text>
        </View>

        <View style={{ flexDirection: 'row', backgroundColor: t.fill, borderRadius: 999, padding: 3, marginTop: 24 }}>
          {(['signIn', 'register'] as const).map((m) => (
            <Text
              key={m}
              accessibilityRole="button"
              accessibilityState={{ selected: mode === m }}
              onPress={() => {
                setMode(m);
                setError(null);
              }}
              style={[
                type.footnote,
                {
                  flex: 1,
                  textAlign: 'center',
                  paddingVertical: 7,
                  fontWeight: '600',
                  borderRadius: 999,
                  overflow: 'hidden',
                  color: t.label,
                  backgroundColor: mode === m ? t.card : 'transparent',
                },
              ]}>
              {m === 'signIn' ? 'Sign In' : 'Create Account'}
            </Text>
          ))}
        </View>

        <Group>
          {mode === 'register' ? (
            <IconField
              icon="person-outline"
              placeholder="Name (optional)"
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
              textContentType="name"
              returnKeyType="next"
              onSubmitEditing={() => emailRef.current?.focus()}
            />
          ) : null}
          <IconField
            icon="mail-outline"
            inputRef={emailRef}
            placeholder="Email"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="emailAddress"
            autoComplete="email"
            returnKeyType="next"
            onSubmitEditing={() => passwordRef.current?.focus()}
          />
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <IconField
              icon="lock-closed-outline"
              inputRef={passwordRef}
              placeholder={mode === 'register' ? 'Password (8+ characters)' : 'Password'}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!passwordVisible}
              autoCapitalize="none"
              textContentType={mode === 'register' ? 'newPassword' : 'password'}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              returnKeyType="go"
              onSubmitEditing={submit}
              containerStyle={{ flex: 1 }}
            />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={passwordVisible ? 'Hide password' : 'Show password'}
              accessibilityState={{ checked: passwordVisible }}
              onPress={() => setPasswordVisible((visible) => !visible)}
              hitSlop={10}
              style={{ paddingHorizontal: 16, paddingVertical: 12 }}>
              <SymbolView name={{ ios: passwordVisible ? 'eye.slash' : 'eye', android: passwordVisible ? 'visibility_off' : 'visibility', web: passwordVisible ? 'visibility_off' : 'visibility' }} size={20} tintColor={t.secondary} weight="regular" />
            </Pressable>
          </View>
        </Group>

        {error ? (
          <View style={{ marginTop: 16 }}>
            <ErrorText message={error} />
          </View>
        ) : null}

        <View style={{ marginTop: 24 }}>
          <Button title={mode === 'signIn' ? 'Sign In' : 'Create Account'} onPress={submit} loading={busy} disabled={!valid} />
        </View>

        <Text style={[type.footnote, { color: t.secondary, textAlign: 'center', marginTop: 20 }]}>
          By continuing you agree to the{' '}
          <Text style={{ color: t.accent }} onPress={() => router.push('/terms')}>
            Terms of Use
          </Text>{' '}
          and the{' '}
          <Text style={{ color: t.accent }} onPress={() => router.push('/privacy')}>
            Privacy Policy
          </Text>
          .
        </Text>
      </ScrollView>
      <BusyOverlay visible={busy} title="Please wait…" message={mode === 'signIn' ? 'Signing you in' : 'Creating your account'} />
    </KeyboardAvoidingView>
  );
}
