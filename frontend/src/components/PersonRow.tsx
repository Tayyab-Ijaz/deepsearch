import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { Image, Pressable, Text, View } from 'react-native';
import type { PersonResult } from '../lib/types';
import { openLink, webUrl } from '../lib/utils';
import { type, useTheme } from '../theme/theme';
import { Chip, IconName } from './ui';

const ICONS: Record<string, IconName> = { linkedin: 'briefcase', instagram: 'camera', facebook: 'people', tiktok: 'musical-notes', x: 'chatbubble', youtube: 'logo-youtube', threads: 'at', github: 'logo-github', pinterest: 'logo-pinterest' };

function Avatar({ person }: { person: PersonResult }) {
  const t = useTheme();
  const [failed, setFailed] = useState(false);
  const uri = person.image_url?.startsWith('https://') ? person.image_url : null;
  const box = { width: 112, height: 112, borderRadius: 18, overflow: 'hidden' as const };
  if (uri && !failed) return <Image source={{ uri }} accessibilityIgnoresInvertColors onError={() => setFailed(true)} style={[box, { backgroundColor: t.fill }]} resizeMode="cover" />;
  return <View style={[box, { backgroundColor: `${t.accent}1F`, alignItems: 'center', justifyContent: 'center' }]}><Ionicons name={ICONS[person.platform_key] ?? 'globe-outline'} size={40} color={t.accent} /></View>;
}

export function PersonRow({ person, saved = false, saving = false, onToggleSave }: { person: PersonResult; saved?: boolean; saving?: boolean; onToggleSave?: () => void }) {
  const t = useTheme();
  const match = person.match_label === 'strong_match' ? { text: 'Strong name match', color: t.green } : person.match_label === 'possible_match' ? { text: 'Possible match', color: t.orange } : { text: 'Weak match', color: t.secondary };
  return (
    <View style={{ width: '100%', minHeight: 142, backgroundColor: t.card, borderRadius: 16, borderWidth: 1, borderColor: t.separator, padding: 14 }}>
      <Pressable accessibilityRole="button" accessibilityLabel={`${person.name} on ${person.platform}`} disabled={!webUrl(person.profile_url)} onPress={() => void openLink(person.profile_url)} style={({ pressed }) => ({ flexDirection: 'row', gap: 14, alignItems: 'center', opacity: pressed ? 0.78 : 1 })}>
        <Avatar person={person} />
        <View style={{ flex: 1, minHeight: 112, gap: 4 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
            <Text style={[type.caption, { color: t.accent, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 }]}>{person.platform}</Text>
            <Chip text={`${Math.round(person.match_score * 100)}% match`} color={match.color} />
          </View>
          <Text numberOfLines={2} style={[type.headline, { color: t.label, marginTop: 2 }]}>{person.name}</Text>
          {person.title && person.title !== person.name ? <Text numberOfLines={1} style={[type.caption, { color: t.secondary }]}>{person.title}</Text> : null}
          {person.description ? <Text numberOfLines={2} style={[type.caption, { color: t.secondary, marginTop: 3 }]}>{person.description}</Text> : null}
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 'auto', paddingTop: 6 }}>
            <Text style={[type.caption, { color: match.color, fontWeight: '600' }]}>{match.text}</Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}><Text style={[type.caption, { color: t.accent, fontWeight: '600' }]}>View profile</Text><Ionicons name="arrow-up-right-box" size={14} color={t.accent} /></View>
          </View>
        </View>
      </Pressable>
      {onToggleSave ? <Pressable accessibilityRole="button" accessibilityLabel={saved ? 'Remove saved profile' : 'Save profile'} accessibilityState={{ busy: saving, selected: saved }} disabled={saving} onPress={onToggleSave} hitSlop={7} style={{ position: 'absolute', top: 22, left: 94, width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(17,17,19,0.78)', opacity: saving ? 0.55 : 1 }}><Ionicons name={saved ? 'bookmark' : 'bookmark-outline'} size={16} color="#FFFFFF" /></Pressable> : null}
    </View>
  );
}
