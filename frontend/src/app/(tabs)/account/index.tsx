import Constants from 'expo-constants';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, Text, View } from 'react-native';
import { ConfirmModal } from '../../../components/ConfirmModal';
import { BusyOverlay, Group, ProgressBar, Row, Screen, TextAction } from '../../../components/ui';
import { errorText } from '../../../lib/api';
import { useAuth } from '../../../lib/auth';
import { APP_NAME } from '../../../lib/config';
import type { UsageCount } from '../../../lib/types';
import { type, useTheme, useThemeMode } from '../../../theme/theme';

function Value({ label, value }: { label: string; value: string }) {
  const t = useTheme();
  return (
    <Row>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 16 }}>
        <Text style={[type.body, { color: t.label }]}>{label}</Text>
        <Text selectable style={[type.body, { color: t.secondary, flexShrink: 1 }]}>
          {value}
        </Text>
      </View>
    </Row>
  );
}

function UsageRow({ label, count }: { label: string; count: UsageCount }) {
  const t = useTheme();
  return (
    <Row>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Text style={[type.body, { color: t.label }]}>{label}</Text>
        <Text style={[type.body, { color: t.secondary }]}>
          {count.used} of {count.limit}
        </Text>
      </View>
      <ProgressBar value={count.used} max={count.limit} />
    </Row>
  );
}

function LinkRow({ title, onPress }: { title: string; onPress: () => void }) {
  const t = useTheme();
  return (
    <Row onPress={onPress} label={title}>
      <Text style={[type.body, { color: t.accent }]}>{title}</Text>
    </Row>
  );
}

export default function AccountScreen() {
  const t = useTheme();
  const { mode, setMode } = useThemeMode();
  const router = useRouter();
  const { user, usage, signOut, deleteAccount } = useAuth();
  const [dialog, setDialog] = useState<'signOut' | 'delete' | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const version = Constants.expoConfig?.version ?? '1.0.0';

  function close() {
    if (busy) return;
    setDialog(null);
    setError(null);
  }

  async function confirm(password: string) {
    setBusy(true);
    setError(null);
    try {
      if (dialog === 'delete') await deleteAccount(password);
      else await signOut();
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Group title="Account">
        <Value label="Email" value={user?.email ?? ''} />
        {user?.display_name ? <Value label="Name" value={user.display_name} /> : null}
      </Group>

      {usage ? (
        <Group title="Today" footer="Limits reset at midnight.">
          <UsageRow label="Searches" count={usage.searches} />
          <UsageRow label="Summaries" count={usage.summaries} />
        </Group>
      ) : null}

      <Group title="Appearance">
        <Row>
          <View style={{ flexDirection: 'row', backgroundColor: t.fill, borderRadius: 999, padding: 4, gap: 4 }}>
            {(['light', 'dark'] as const).map((option) => {
              const selected = mode === option;
              return (
                <Pressable key={option} accessibilityRole="button" accessibilityState={{ selected }} onPress={() => setMode(option)} style={{ flex: 1, minHeight: 44, borderRadius: 999, backgroundColor: selected ? t.card : 'transparent', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
                  <Ionicons name={option === 'light' ? 'sunny-outline' : 'moon-outline'} size={17} color={selected ? t.accent : t.secondary} />
                  <Text style={[type.subhead, { color: selected ? t.label : t.secondary, fontWeight: selected ? '600' : '400' }]}>{option === 'light' ? 'Light' : 'Dark'}</Text>
                </Pressable>
              );
            })}
          </View>
        </Row>
      </Group>

      <Group title="Responsible use">
        <Row>
          <Text style={[type.footnote, { color: t.secondary }]}>
            Use {APP_NAME} only for yourself, people who agreed, or well-known public figures. Do not use it to harass, stalk or expose anyone.
          </Text>
        </Row>
      </Group>

      <Group title="About">
        <Value label="Version" value={version} />
        <LinkRow title="Privacy Policy" onPress={() => router.push('/privacy')} />
        <LinkRow title="Terms of Use" onPress={() => router.push('/terms')} />
        <LinkRow title="Contact Support" onPress={() => router.push('/support')} />
      </Group>

      <Group title="Feedback">
        <LinkRow title="Review the App" onPress={() => router.push('/review')} />
      </Group>

      <Group>
        <TextAction title="Sign Out" destructive onPress={() => setDialog('signOut')} />
      </Group>

      <Group footer="Permanently deletes your account and sign-in data.">
        <TextAction title="Delete Account" destructive onPress={() => setDialog('delete')} />
      </Group>

      <ConfirmModal
        visible={dialog === 'signOut'}
        title={`Sign out of ${APP_NAME}?`}
        message="You will need to sign in again to use the app."
        confirmLabel="Sign Out"
        destructive
        busy={busy}
        error={error}
        onConfirm={confirm}
        onCancel={close}
      />
      <ConfirmModal
        visible={dialog === 'delete'}
        title="Delete Account"
        message={user?.auth_provider === 'google' ? 'This permanently deletes your account and its data.' : 'This permanently deletes your account. Enter your password to confirm.'}
        confirmLabel="Delete"
        destructive
        passwordLabel={user?.auth_provider === 'google' ? undefined : 'Password'}
        busy={busy}
        error={error}
        onConfirm={confirm}
        onCancel={close}
      />
      <BusyOverlay visible={busy && dialog === 'delete'} title="Please wait…" message="Deleting your account" />
    </Screen>
  );
}
