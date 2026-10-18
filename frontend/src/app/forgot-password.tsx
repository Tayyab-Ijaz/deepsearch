import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { SymbolView } from 'expo-symbols';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { BrandMark } from '../components/BrandMark';
import { BusyOverlay, Button, ErrorText, Group, IconField } from '../components/ui';
import { api, errorText } from '../lib/api';
import { haptic } from '../lib/utils';
import { type, useTheme } from '../theme/theme';

type Step = 'email' | 'code' | 'done';

export default function ForgotPassword() {
  const t = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ email?: string }>();
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState(typeof params.email === 'string' ? params.email : '');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const cleanEmail = email.trim().toLowerCase();
  const emailValid = cleanEmail.includes('@') && cleanEmail.length > 3;
  const resetValid = code.length === 6 && password.length >= 8;

  function leave() {
    if (router.canGoBack()) router.back();
    else router.replace('/sign-in');
  }

  async function sendCode() {
    if (!emailValid || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.post('api/auth/forgot-password', { email: cleanEmail }, false);
      setStep('code');
      setCooldown(30);
      haptic('success');
    } catch (e) {
      haptic('error');
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  async function submitReset() {
    if (!resetValid || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.post('api/auth/reset-password', { email: cleanEmail, code, new_password: password }, false);
      setStep('done');
      haptic('success');
    } catch (e) {
      haptic('error');
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const title = step === 'email' ? 'Forgot your password?' : step === 'code' ? 'Check your email' : 'Password updated';
  const intro =
    step === 'email'
      ? 'Enter the email you signed up with and we will send you a 6-digit code.'
      : step === 'code'
        ? `If an account exists for ${cleanEmail}, a 6-digit code is on its way. It expires in 15 minutes.`
        : 'Your password has been changed and your other devices have been signed out. Sign in with your new password.';

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: t.bg }}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', padding: 24, width: '100%', maxWidth: 480, alignSelf: 'center' }}>
        <View style={{ alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <BrandMark size={72} />
          <Text style={[type.title, { color: t.label, textAlign: 'center' }]}>{title}</Text>
          <Text style={[type.subhead, { color: t.secondary, textAlign: 'center' }]}>{intro}</Text>
        </View>

        {step === 'email' ? (
          <>
            <Group>
              <IconField
                icon="mail-outline"
                placeholder="Email"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                textContentType="emailAddress"
                autoComplete="email"
                returnKeyType="send"
                onSubmitEditing={sendCode}
              />
            </Group>
            {error ? <View style={{ marginTop: 16 }}><ErrorText message={error} /></View> : null}
            <View style={{ marginTop: 24 }}>
              <Button title="Send Code" onPress={sendCode} loading={busy} disabled={!emailValid} />
            </View>
          </>
        ) : null}

        {step === 'code' ? (
          <>
            <Group>
              <IconField
                icon="lock-closed-outline"
                placeholder="6-digit code"
                value={code}
                onChangeText={(value) => setCode(value.replace(/\D/g, '').slice(0, 6))}
                keyboardType="number-pad"
                textContentType="oneTimeCode"
                autoComplete="sms-otp"
                maxLength={6}
                autoCorrect={false}
                returnKeyType="next"
              />
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <IconField
                  icon="lock-closed-outline"
                  placeholder="New password (8+ characters)"
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!passwordVisible}
                  autoCapitalize="none"
                  textContentType="newPassword"
                  autoComplete="new-password"
                  returnKeyType="go"
                  onSubmitEditing={submitReset}
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
            {error ? <View style={{ marginTop: 16 }}><ErrorText message={error} /></View> : null}
            <View style={{ marginTop: 24 }}>
              <Button title="Reset Password" onPress={submitReset} loading={busy} disabled={!resetValid} />
            </View>
            <Pressable
              accessibilityRole="button"
              disabled={cooldown > 0 || busy}
              onPress={sendCode}
              hitSlop={8}
              style={{ alignSelf: 'center', paddingVertical: 16, opacity: cooldown > 0 ? 0.5 : 1 }}>
              <Text style={[type.subhead, { color: t.accent, fontWeight: '600' }]}>{cooldown > 0 ? `Send a new code in ${cooldown}s` : 'Send a new code'}</Text>
            </Pressable>
          </>
        ) : null}

        {step === 'done' ? (
          <View style={{ marginTop: 24 }}>
            <Button title="Back to Sign In" onPress={() => router.replace('/sign-in')} />
          </View>
        ) : null}

        {step !== 'done' ? (
          <Pressable accessibilityRole="button" onPress={leave} hitSlop={8} style={{ alignSelf: 'center', paddingVertical: 12 }}>
            <Text style={[type.subhead, { color: t.secondary }]}>Back to sign in</Text>
          </Pressable>
        ) : null}
      </ScrollView>
      <BusyOverlay visible={busy} title="Please wait…" message={step === 'email' ? 'Sending your code' : 'Updating your password'} />
    </KeyboardAvoidingView>
  );
}
