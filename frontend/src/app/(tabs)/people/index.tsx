import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { PersonRow } from '../../../components/PersonRow';
import { Button, ErrorText, Group, IconField, ResultsSkeleton, Row, Screen, TextAction, ToggleRow } from '../../../components/ui';
import { api, errorText } from '../../../lib/api';
import { useAuth } from '../../../lib/auth';
import type { PersonResult, SavedPeopleResponse, SearchResponse, SummaryResponse } from '../../../lib/types';
import { haptic } from '../../../lib/utils';
import { type, useTheme } from '../../../theme/theme';

const cut = (value: string, max: number) => value.slice(0, max);
const PAGE_SIZE = 20;

export default function PeopleScreen() {
  const t = useTheme();
  const { aiSummary, refreshUsage } = useAuth();
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [consent, setConsent] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<PersonResult[]>([]);
  const [matchFilter, setMatchFilter] = useState<'all' | 'strong_match' | 'possible_match' | 'weak_match'>('all');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [shown, setShown] = useState(PAGE_SIZE);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [summarizing, setSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [savedProfiles, setSavedProfiles] = useState<Map<string, string>>(new Map());
  const [savingProfile, setSavingProfile] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    let active = true;
    void api.get<SavedPeopleResponse>('api/saved').then((res) => {
      if (active) setSavedProfiles(new Map(res.results.map((item) => [item.person.profile_url, item.id])));
    }).catch(() => {});
    return () => { active = false; };
  }, []));

  async function toggleSaved(person: PersonResult) {
    if (savingProfile) return;
    setSavingProfile(person.profile_url);
    setSaveError(null);
    try {
      if (savedProfiles.has(person.profile_url)) {
        const savedId = savedProfiles.get(person.profile_url);
        if (!savedId) throw new Error('Could not find this saved profile. Refresh and try again.');
        await api.del(`api/saved/${savedId}`);
        setSavedProfiles((previous) => { const next = new Map(previous); next.delete(person.profile_url); return next; });
      } else {
        const saved = await api.post<{ id: string }>('api/saved', person);
        setSavedProfiles((previous) => new Map(previous).set(person.profile_url, saved.id));
      }
      haptic('success');
    } catch (e) {
      setSaveError(errorText(e));
      haptic('error');
    } finally {
      setSavingProfile(null);
    }
  }

  const canSearch = name.trim().length >= 2 && consent && !searching;
  const platforms = [...new Set(results.map((result) => result.platform_key))];
  const visibleResults = results.filter((result) =>
    (matchFilter === 'all' || result.match_label === matchFilter) &&
    (platformFilter === 'all' || result.platform_key === platformFilter),
  );

  async function search() {
    if (!canSearch) return;
    setSearching(true);
    setError(null);
    setResults([]);
    setWarnings([]);
    setSearched(false);
    setSummary(null);
    setSummaryExpanded(false);
    setSummaryError(null);
    setMatchFilter('all');
    setPlatformFilter('all');
    setShown(PAGE_SIZE);
    try {
      const res = await api.post<SearchResponse>('api/search', {
        name: name.trim(),
        location: location.trim() || null,
        consent,
      });
      setResults(res.results);
      setWarnings(res.warnings);
      setSearched(true);
      haptic('success');
      void refreshUsage();
      if (aiSummary && res.results.length > 0) void summarize(res.results, name.trim());
    } catch (e) {
      setResults([]);
      setWarnings([]);
      setError(errorText(e));
      haptic('error');
    } finally {
      setSearching(false);
    }
  }

  async function summarize(items: PersonResult[] = results, searchedName = name.trim()) {
    if (summarizing || items.length === 0) return;
    setSummarizing(true);
    setSummaryError(null);
    try {
      const res = await api.post<SummaryResponse>('api/summary', {
        name: searchedName,
        consent,
        results: items.slice(0, 8).map((r) => ({
          platform: cut(r.platform, 40),
          title: cut(r.title, 290),
          description: cut(r.description, 580),
          profile_url: cut(r.profile_url, 1900),
        })),
      });
      setSummary(res);
      setSummaryExpanded(false);
      void refreshUsage();
    } catch (e) {
      setSummaryError(errorText(e));
    } finally {
      setSummarizing(false);
    }
  }

  return (
    <Screen>
      <Group title="Who are you looking for?">
        <IconField icon="person-outline" placeholder="Full name" value={name} onChangeText={setName} autoCapitalize="words" autoCorrect={false} textContentType="name" returnKeyType="search" onSubmitEditing={search} />
        <IconField icon="location-outline" placeholder="City or country (optional)" value={location} onChangeText={setLocation} autoCapitalize="words" />
      </Group>

      <View style={{ marginTop: 20, gap: 7 }}>
        <ToggleRow value={consent} onChange={setConsent}>
          <Text style={[type.subhead, { color: t.label, fontWeight: '600' }]}>I am searching for myself, someone who agreed, or a well-known public figure.</Text>
        </ToggleRow>
        <Text style={[type.footnote, { color: t.secondary, marginHorizontal: 8 }]}>Search results are public pages only. Searching for someone without their agreement is not allowed.</Text>
      </View>

      <View style={{ marginTop: 24 }}>
        <Button title={searching ? 'Searching…' : 'Search'} icon="search" onPress={search} loading={searching} disabled={!canSearch} />
      </View>

      {searching ? <ResultsSkeleton count={3} /> : null}

      {error ? (
        <View style={{ marginTop: 16 }}>
          <ErrorText message={error} />
        </View>
      ) : null}

      {searched && results.length === 0 && !error ? (
        <View style={{ alignItems: 'center', paddingVertical: 32, gap: 6 }}>
          <Text style={[type.headline, { color: t.label }]}>No profiles found</Text>
          <Text style={[type.subhead, { color: t.secondary, textAlign: 'center' }]}>Try the full name, or add a city or country.</Text>
        </View>
      ) : null}

      {results.length > 0 ? (
        <View style={{ marginTop: 24, gap: 10 }}>
          <Text style={[type.footnote, { color: t.secondary, marginLeft: 16, marginBottom: 2, textTransform: 'uppercase' }]}>{`${visibleResults.length} of ${results.length} possible profiles`}</Text>
          {aiSummary ? (
            <View style={{ backgroundColor: t.card, borderRadius: 16, borderWidth: 1, borderColor: t.separator, padding: 14 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: summary ? 8 : 0 }}>
                <Text style={[type.headline, { color: t.label, flex: 1 }]}>AI summary</Text>
                {summarizing ? <Text style={[type.caption, { color: t.secondary }]}>Preparing…</Text> : null}
              </View>
              {summary ? <><Text numberOfLines={summaryExpanded ? undefined : 2} style={[type.body, { color: t.label }]}>{summary.summary}</Text>{summary.summary.length > 100 ? <Pressable accessibilityRole="button" onPress={() => setSummaryExpanded((value) => !value)} hitSlop={8} style={{ alignSelf: 'flex-start', paddingVertical: 5 }}><Text style={[type.footnote, { color: t.accent, fontWeight: '700' }]}>{summaryExpanded ? 'Read less' : 'Read more'}</Text></Pressable> : null}<Text style={[type.caption, { color: t.secondary, marginTop: 8 }]}>{summary.disclaimer}</Text></> : <TextAction title={summarizing ? 'Writing summary…' : 'Summarize these results'} icon="sparkles-outline" onPress={summarize} loading={summarizing} />}
              {summaryError ? <View style={{ marginTop: 8 }}><ErrorText message={summaryError} /></View> : null}
            </View>
          ) : null}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 7, paddingHorizontal: 2 }}>
            {([['all', 'All matches'], ['strong_match', 'Strong'], ['possible_match', 'Possible'], ['weak_match', 'Weak']] as const).map(([value, label]) => {
              const selected = matchFilter === value;
              return <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected }} onPress={() => { setMatchFilter(value); setShown(PAGE_SIZE); }} style={{ paddingHorizontal: 13, paddingVertical: 8, borderRadius: 999, backgroundColor: selected ? t.accent : t.card, borderWidth: 1, borderColor: selected ? t.accent : t.separator }}><Text style={[type.caption, { color: selected ? (t.dark ? '#111111' : '#FFFFFF') : t.secondary, fontWeight: '600' }]}>{label}</Text></Pressable>;
            })}
          </ScrollView>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 7, paddingHorizontal: 2 }}>
            {['all', ...platforms].map((value) => {
              const selected = platformFilter === value;
              const label = value === 'all' ? 'Every platform' : results.find((result) => result.platform_key === value)?.platform ?? value;
              return <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected }} onPress={() => { setPlatformFilter(value); setShown(PAGE_SIZE); }} style={{ paddingHorizontal: 13, paddingVertical: 8, borderRadius: 999, backgroundColor: selected ? t.accent : t.card, borderWidth: 1, borderColor: selected ? t.accent : t.separator }}><Text style={[type.caption, { color: selected ? (t.dark ? '#111111' : '#FFFFFF') : t.secondary, fontWeight: '600' }]}>{label}</Text></Pressable>;
            })}
          </ScrollView>
          {visibleResults.length > 0 ? <View style={{ gap: 10 }}>{visibleResults.slice(0, shown).map((r) => <PersonRow key={r.profile_url} person={r} saved={savedProfiles.has(r.profile_url)} saving={savingProfile === r.profile_url} onToggleSave={() => void toggleSaved(r)} />)}{visibleResults.length > shown ? <TextAction title={`Show more (${visibleResults.length - shown} left)`} icon="chevron-down-outline" onPress={() => setShown((n) => n + PAGE_SIZE)} /> : null}</View> : <Text style={[type.subhead, { color: t.secondary, textAlign: 'center', paddingVertical: 18 }]}>No profiles match these filters.</Text>}
          <Text style={[type.footnote, { color: t.secondary, marginHorizontal: 16, marginTop: 2 }]}>Name match only. A matching name does not confirm it is the same person.</Text>
          {saveError ? <ErrorText message={saveError} /> : null}
        </View>
      ) : null}

      {warnings.length > 0 ? (
        <Group title="Partly unavailable">
          {warnings.map((w) => (
            <Row key={w}>
              <Text style={[type.footnote, { color: t.secondary }]}>{w}</Text>
            </Row>
          ))}
        </Group>
      ) : null}
    </Screen>
  );
}
