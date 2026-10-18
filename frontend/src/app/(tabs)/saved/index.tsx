import { useCallback, useMemo, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { PersonRow } from '../../../components/PersonRow';
import { Button, ErrorText, Group, IconField, ResultsSkeleton, Screen } from '../../../components/ui';
import { api, errorText } from '../../../lib/api';
import type { SavedPeopleResponse, SavedPerson } from '../../../lib/types';
import { haptic } from '../../../lib/utils';
import { type, useTheme } from '../../../theme/theme';

type MatchFilter = 'all' | 'strong_match' | 'possible_match' | 'weak_match';

function FilterChip({ title, selected, onPress }: { title: string; selected: boolean; onPress: () => void }) {
  const t = useTheme();
  return <Pressable accessibilityRole="button" accessibilityState={{ selected }} onPress={onPress} style={{ paddingHorizontal: 13, paddingVertical: 8, borderRadius: 999, backgroundColor: selected ? t.accent : t.card, borderWidth: 1, borderColor: selected ? t.accent : t.separator }}><Text style={[type.caption, { color: selected ? (t.dark ? '#111111' : '#FFFFFF') : t.secondary, fontWeight: '600' }]}>{title}</Text></Pressable>;
}

export default function SavedScreen() {
  const t = useTheme();
  const router = useRouter();
  const [items, setItems] = useState<SavedPerson[]>([]);
  const [loading, setLoading] = useState(true);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [matchFilter, setMatchFilter] = useState<MatchFilter>('all');
  const [sortByName, setSortByName] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<SavedPeopleResponse>('api/saved');
      setItems(response.results);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void reload(); }, [reload]));

  const platforms = [...new Map(items.map(({ person }) => [person.platform_key, person.platform])).entries()];
  const filteredItems = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return items.filter(({ person }) => {
      const matchesQuery = !normalized || [person.name, person.platform, person.title, person.description].some((value) => value?.toLocaleLowerCase().includes(normalized));
      return matchesQuery && (platformFilter === 'all' || person.platform_key === platformFilter) && (matchFilter === 'all' || person.match_label === matchFilter);
    }).sort((a, b) => sortByName ? a.person.name.localeCompare(b.person.name) : b.saved_at - a.saved_at);
  }, [items, query, platformFilter, matchFilter, sortByName]);

  async function remove(item: SavedPerson) {
    if (removingId) return;
    setRemovingId(item.id);
    setError(null);
    try {
      await api.del(`api/saved/${item.id}`);
      setItems((previous) => previous.filter((saved) => saved.id !== item.id));
      haptic('success');
    } catch (e) {
      setError(errorText(e));
      haptic('error');
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <Screen>
      <Group title="Find a saved profile">
        <IconField icon="search" placeholder="Search name, role, or platform" value={query} onChangeText={setQuery} autoCapitalize="none" autoCorrect={false} returnKeyType="search" />
      </Group>

      {items.length > 0 ? (
        <View style={{ marginTop: 20, gap: 12 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 4 }}>
            <View>
              <Text style={[type.headline, { color: t.label }]}>{filteredItems.length} {filteredItems.length === 1 ? 'profile' : 'profiles'}</Text>
              <Text style={[type.caption, { color: t.secondary, marginTop: 2 }]}>Saved to your account</Text>
            </View>
            <Pressable accessibilityRole="button" onPress={() => setSortByName((value) => !value)} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: 999, borderWidth: 1, borderColor: t.separator, backgroundColor: t.card, paddingHorizontal: 12, paddingVertical: 8 }}>
              <Ionicons name={sortByName ? 'text-outline' : 'time-outline'} size={15} color={t.secondary} />
              <Text style={[type.caption, { color: t.label, fontWeight: '600' }]}>{sortByName ? 'A–Z' : 'Recent'}</Text>
            </Pressable>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 7, paddingHorizontal: 2 }}>
            {[['all', 'All matches'], ['strong_match', 'Strong'], ['possible_match', 'Possible'], ['weak_match', 'Weak']] .map(([value, label]) => <FilterChip key={value} title={label} selected={matchFilter === value} onPress={() => setMatchFilter(value as MatchFilter)} />)}
          </ScrollView>
          {platforms.length > 1 ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 7, paddingHorizontal: 2 }}>
            {[['all', 'Every platform'], ...platforms].map(([value, label]) => <FilterChip key={value} title={label} selected={platformFilter === value} onPress={() => setPlatformFilter(value)} />)}
          </ScrollView> : null}
          {filteredItems.length > 0 ? <View style={{ gap: 10 }}>{filteredItems.map((item) => <PersonRow key={item.id} person={item.person} saved saving={removingId === item.id} onToggleSave={() => void remove(item)} />)}</View> : (
            <View style={{ alignItems: 'center', paddingVertical: 28, gap: 6 }}>
              <Text style={[type.headline, { color: t.label }]}>No matching profiles</Text>
              <Text style={[type.subhead, { color: t.secondary, textAlign: 'center' }]}>Try a different name or clear one of the filters.</Text>
              <Pressable onPress={() => { setQuery(''); setPlatformFilter('all'); setMatchFilter('all'); }} hitSlop={8} style={{ padding: 8 }}><Text style={[type.footnote, { color: t.accent, fontWeight: '700' }]}>Clear filters</Text></Pressable>
            </View>
          )}
        </View>
      ) : null}

      {loading ? <ResultsSkeleton count={2} /> : null}
      {error ? <View style={{ marginTop: 18, gap: 12 }}><ErrorText message={error} /><Button title="Try again" icon="refresh" onPress={() => void reload()} /></View> : null}
      {!loading && !error && items.length === 0 ? (
        <View style={{ alignItems: 'center', marginTop: 28, padding: 24, borderRadius: 20, backgroundColor: t.card, borderWidth: 1, borderColor: t.separator }}>
          <View style={{ width: 58, height: 58, borderRadius: 29, alignItems: 'center', justifyContent: 'center', backgroundColor: t.fill }}><Ionicons name="bookmark-outline" size={25} color={t.accent} /></View>
          <Text style={[type.title, { color: t.label, fontSize: 21, marginTop: 16, textAlign: 'center' }]}>Your shortlist starts here</Text>
          <Text style={[type.subhead, { color: t.secondary, lineHeight: 21, textAlign: 'center', marginTop: 6 }]}>Save a profile from People search and it will be kept here for your next visit.</Text>
          <View style={{ width: '100%', marginTop: 18 }}><Button title="Explore people" icon="search" onPress={() => router.navigate('/people')} /></View>
        </View>
      ) : null}
    </Screen>
  );
}
