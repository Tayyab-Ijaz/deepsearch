import { Stack } from 'expo-router';
import { Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { type, useTheme } from '../theme/theme';

type TabPageHeaderProps = { title: string; subtitle: string };

function TabPageHeader({ title, subtitle }: TabPageHeaderProps) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View style={{ backgroundColor: t.bg, paddingTop: insets.top + 8, paddingHorizontal: 22, paddingBottom: 12 }}>
      <Text style={{ color: t.label, fontSize: 29, lineHeight: 34, fontWeight: '800', letterSpacing: -0.45 }}>{title}</Text>
      <Text style={[type.caption, { color: t.secondary, lineHeight: 17, marginTop: 2 }]}>{subtitle}</Text>
    </View>
  );
}

/** Each tab owns a consistent page header, including its subtitle, above its scrollable content. */
export function TabStack({ title, subtitle }: TabPageHeaderProps) {
  const t = useTheme();
  return (
    <Stack
      screenOptions={{
        header: () => <TabPageHeader title={title} subtitle={subtitle} />,
        contentStyle: { backgroundColor: t.bg },
      }}>
      <Stack.Screen name="index" options={{ title }} />
    </Stack>
  );
}
