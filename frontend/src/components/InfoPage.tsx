import { Ionicons } from '@expo/vector-icons';
import { ReactNode } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen } from './ui';
import { type, useTheme } from '../theme/theme';

export function InfoPage({ icon, eyebrow, title, intro, children }: {
  icon: keyof typeof Ionicons.glyphMap;
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
}) {
  const t = useTheme();
  const router = useRouter();
  return (
    <Screen>
      <Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={() => router.back()} style={{ width: 42, height: 42, borderRadius: 21, backgroundColor: t.card, borderWidth: 1, borderColor: t.separator, alignItems: 'center', justifyContent: 'center', marginBottom: 24 }}>
        <Ionicons name="arrow-back" size={20} color={t.label} />
      </Pressable>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 12 }}>
        <View style={{ width: 58, height: 58, borderRadius: 19, backgroundColor: t.card, borderWidth: 1, borderColor: t.separator, alignItems: 'center', justifyContent: 'center' }}>
          <Ionicons name={icon} size={27} color={t.accent} />
        </View>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={[type.caption, { color: t.secondary, fontWeight: '800', letterSpacing: 1.35, textTransform: 'uppercase' }]}>{eyebrow}</Text>
          <View style={{ height: 3, width: 34, borderRadius: 2, backgroundColor: t.accent }} />
        </View>
      </View>
      <Text style={[type.title, { color: t.label, fontSize: 35, lineHeight: 40, fontWeight: '800', letterSpacing: -0.8, marginTop: 2 }]}>{title}</Text>
      <Text style={[type.subhead, { color: t.secondary, fontSize: 16, fontWeight: '500', lineHeight: 24, marginTop: 9, marginBottom: 22 }]}>{intro}</Text>
      <View style={{ gap: 12 }}>{children}</View>
    </Screen>
  );
}

export function InfoSection({ title, children }: { title: string; children: string }) {
  const t = useTheme();
  return (
    <View style={{ backgroundColor: t.card, borderRadius: 16, borderWidth: 1, borderColor: t.separator, padding: 16, gap: 7 }}>
      <Text style={[type.headline, { color: t.label, fontSize: 18, fontWeight: '700', letterSpacing: -0.2 }]}>{title}</Text>
      <Text style={[type.subhead, { color: t.secondary, lineHeight: 22 }]}>{children}</Text>
    </View>
  );
}
