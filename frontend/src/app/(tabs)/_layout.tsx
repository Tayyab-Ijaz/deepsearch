import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import type { BottomTabBarProps } from 'expo-router/build/react-navigation/bottom-tabs';
import { Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { IconName } from '../../components/ui';
import { type } from '../../theme/theme';

const TAB_ICONS: Record<string, { inactive: IconName; active: IconName; label: string }> = {
  people: { inactive: 'people-outline', active: 'people', label: 'People' },
  usernames: { inactive: 'at-outline', active: 'at', label: 'Usernames' },
  saved: { inactive: 'bookmark-outline', active: 'bookmark', label: 'Saved' },
  account: { inactive: 'person-circle-outline', active: 'person-circle', label: 'Account' },
};

function FloatingNotchTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  const barColor = '#141519';

  return (
    <View style={{ position: 'absolute', left: 14, right: 14, bottom: Math.max(insets.bottom, 8), height: 76, flexDirection: 'row', alignItems: 'stretch', paddingHorizontal: 6, paddingVertical: 5, backgroundColor: barColor, borderRadius: 999, borderWidth: 1, borderColor: 'rgba(255,255,255,0.12)', shadowColor: '#000000', shadowOpacity: 0.2, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 8, zIndex: 10 }}>
      {state.routes.map((route, index) => {
        const focused = state.index === index;
        const config = TAB_ICONS[route.name];
        if (!config) return null;
        const title = descriptors[route.key].options.title ?? config.label;

        function onPress() {
          const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
          if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
        }

        function onLongPress() {
          navigation.emit({ type: 'tabLongPress', target: route.key });
        }

        return (
          <Pressable
            key={route.key}
            accessibilityRole="button"
            accessibilityState={focused ? { selected: true } : {}}
            accessibilityLabel={descriptors[route.key].options.tabBarAccessibilityLabel ?? `${title} tab`}
            testID={descriptors[route.key].options.tabBarButtonTestID}
            onPress={onPress}
            onLongPress={onLongPress}
            style={{ flex: 1, minWidth: 0, alignItems: 'center', justifyContent: 'center', borderRadius: 999 }}>
            <View style={{ width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', borderWidth: focused ? 1 : 0, borderColor: focused ? 'rgba(255,255,255,0.72)' : 'transparent', backgroundColor: focused ? 'rgba(255,255,255,0.10)' : 'transparent' }}>
              <Ionicons name={focused ? config.active : config.inactive} size={21} color={focused ? '#FFFFFF' : '#A6A7AD'} />
            </View>
            <Text numberOfLines={1} style={[type.caption, { maxWidth: '100%', marginTop: 1, marginBottom: 1, color: focused ? '#FFFFFF' : '#A6A7AD', fontSize: 11, lineHeight: 15, fontWeight: focused ? '700' : '500' }]}>{title}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      tabBar={(props) => <FloatingNotchTabBar {...props} />}
      screenOptions={{ headerShown: false, tabBarHideOnKeyboard: true }}>
      <Tabs.Screen name="people" options={{ title: 'People' }} />
      <Tabs.Screen name="usernames" options={{ title: 'Usernames' }} />
      <Tabs.Screen name="saved" options={{ title: 'Saved' }} />
      <Tabs.Screen name="account" options={{ title: 'Account' }} />
    </Tabs>
  );
}
