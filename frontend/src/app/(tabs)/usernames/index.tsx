import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Button, Chip, ErrorText, Group, IconField, ResultsSkeleton, Screen, Tile, ToggleRow } from '../../../components/ui';
import { api, errorText } from '../../../lib/api';
import { useAuth } from '../../../lib/auth';
import type { UsernameResponse, UsernameRow, UsernameVerdict } from '../../../lib/types';
import { haptic, openLink, webUrl } from '../../../lib/utils';
import { type, useTheme, Theme } from '../../../theme/theme';

const ORDER: UsernameVerdict[] = ['confirmed', 'unverified', 'not_found', 'unchecked'];

const META: Record<UsernameVerdict, { title: string; short: string; note: string; icon: keyof typeof Ionicons.glyphMap; color: (t: Theme) => string }> = {
  confirmed: { title: 'Confirmed to exist', short: 'Confirmed', note: 'The page exists and the platform rejects made-up names.', icon: 'checkmark-circle', color: (t) => t.green },
  unverified: { title: 'Exists, but unverified', short: 'Unverified', note: 'These platforms say yes to any name, or the check did not finish. Treat as a lead.', icon: 'help-circle', color: (t) => t.orange },
  not_found: { title: 'Not found', short: 'Not found', note: 'No profile with this name.', icon: 'close-circle-outline', color: (t) => t.secondary },
  unchecked: { title: 'Could not check', short: 'No answer', note: 'Blocked or timed out. Try again later or from another network.', icon: 'alert-circle-outline', color: (t) => t.red },
};

function PlatformRow({ row }: { row: UsernameRow }) {
  const t = useTheme();
  const meta = META[row.verdict];
  const link = webUrl(row.url);
  const brand = row.key === 'instagram' ? '#C13584' : row.key === 'github' ? '#24292F' : row.key === 'linkedin' ? '#0A66C2' : row.key === 'youtube' ? '#FF0000' : t.accent;
  return (
    <Pressable accessibilityRole={link ? 'button' : undefined} accessibilityLabel={`${row.platform}: ${meta.short}`} onPress={link ? () => void openLink(link) : undefined} style={({ pressed }) => ({ width: '48%', minHeight: 190, padding: 13, borderRadius: 16, borderWidth: 1, borderColor: t.separator, backgroundColor: t.card, opacity: pressed ? 0.78 : 1 })}>
      <View style={{ flex: 1, alignItems: 'flex-start' }}>
        <View style={{ width: 48, height: 48, borderRadius: 14, backgroundColor: `${brand}18`, alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
          <Ionicons name={row.key === 'github' ? 'logo-github' : row.key === 'instagram' ? 'logo-instagram' : row.key === 'linkedin' ? 'logo-linkedin' : row.key === 'youtube' ? 'logo-youtube' : 'globe-outline'} size={25} color={brand} />
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: 4 }}>
          <Text numberOfLines={1} style={[type.headline, { color: t.label, flex: 1 }]}>{row.platform}</Text>
          <Ionicons name={meta.icon} size={18} color={meta.color(t)} />
        </View>
        {row.experimental ? <View style={{ marginTop: 5 }}><Chip text="Experimental" color={t.secondary} /></View> : null}
        <Text style={[type.caption, { color: t.secondary, marginTop: 7 }]}>{row.reason}</Text>
        {link ? <Text style={[type.caption, { color: t.accent, fontWeight: '600', marginTop: 'auto', paddingTop: 8 }]}>Open profile ↗</Text> : null}
      </View>
    </Pressable>
  );
}

export default function UsernamesScreen() {
  const t = useTheme();
  const { refreshUsage } = useAuth();
  const [username, setUsername] = useState('');
  const [consent, setConsent] = useState(false);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<UsernameResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cleaned = username.trim().replace(/@/g, '');
  const canCheck = cleaned.length >= 2 && consent && !checking;

  async function check() {
    if (!canCheck) return;
    setChecking(true);
    setError(null);
    try {
      const res = await api.post<UsernameResponse>('api/username', { username: cleaned, consent });
      setResult(res);
      haptic('success');
      void refreshUsage();
    } catch (e) {
      setResult(null);
      setError(errorText(e));
      haptic('error');
    } finally {
      setChecking(false);
    }
  }

  const rows = (verdict: UsernameVerdict) => result?.platforms.filter((p) => p.verdict === verdict) ?? [];

  return (
    <Screen>
      <Group
        title="Check a username"
        footer="We look at each platform's public page and report whether the name exists. A name that exists is not proof of who owns it.">
        <IconField icon="at-outline" placeholder="Username, for example ayesha.k" value={username} onChangeText={setUsername} autoCapitalize="none" autoCorrect={false} textContentType="username" returnKeyType="search" onSubmitEditing={check} />
      </Group>

      <View style={{ marginTop: 20 }}>
        <ToggleRow value={consent} onChange={setConsent}>
          <Text style={[type.subhead, { color: t.label, fontWeight: '600' }]}>I am searching for myself, someone who agreed, or a well-known public figure.</Text>
        </ToggleRow>
      </View>

      <View style={{ marginTop: 24 }}>
        <Button title={checking ? 'Checking…' : 'Check Platforms'} icon="search" onPress={check} loading={checking} disabled={!canCheck} />
      </View>

      {checking ? <ResultsSkeleton count={4} /> : null}

      {error ? (
        <View style={{ marginTop: 16 }}>
          <ErrorText message={error} />
        </View>
      ) : null}

      {result ? (
        <>
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 24 }}>
            {ORDER.map((v) => (
              <Tile key={v} count={rows(v).length} label={META[v].short} color={META[v].color(t)} />
            ))}
          </View>
          <Text style={[type.footnote, { color: t.secondary, marginTop: 8, marginHorizontal: 4 }]}>
            Checked {result.platforms.length} platforms for “{result.username}” in {(result.took_ms / 1000).toFixed(1)} s.
          </Text>
          {ORDER.map((v) =>
            rows(v).length > 0 ? (
              <View key={v} style={{ marginTop: 24, gap: 10 }}>
                <Text style={[type.footnote, { color: t.secondary, marginLeft: 16, textTransform: 'uppercase' }]}>{`${META[v].title} (${rows(v).length})`}</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: 10 }}>
                  {rows(v).map((row) => <PlatformRow key={row.key} row={row} />)}
                </View>
                <Text style={[type.footnote, { color: t.secondary, marginHorizontal: 16 }]}>{META[v].note}</Text>
              </View>
            ) : null,
          )}
        </>
      ) : null}
    </Screen>
  );
}
