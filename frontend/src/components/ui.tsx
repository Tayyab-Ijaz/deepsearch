import { Ionicons } from '@expo/vector-icons';
import { SymbolView, type AndroidSymbol, type SFSymbol } from 'expo-symbols';
import { Children, ComponentProps, ReactNode, Ref, useEffect, useRef } from 'react';
import {
  ActivityIndicator,
  Animated,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from 'react-native';
import { type, useTheme } from '../theme/theme';

/** Browsers draw a heavy outline on focused inputs. Phones ignore this. */
export const NO_OUTLINE = Platform.select({ web: { outlineStyle: 'none' } as object, default: {} });

export type IconName = ComponentProps<typeof Ionicons>['name'];

export function BusyOverlay({ visible, title, message }: { visible: boolean; title: string; message: string }) {
  const t = useTheme();
  return (
    <Modal visible={visible} transparent animationType="fade" statusBarTranslucent onRequestClose={() => {}}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.28)', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <View accessibilityRole="progressbar" accessibilityLabel={`${title}. ${message}`} style={{ minWidth: 220, maxWidth: 280, flexDirection: 'row', alignItems: 'center', gap: 13, backgroundColor: t.card, borderRadius: 14, borderWidth: 1, borderColor: t.separator, paddingHorizontal: 20, paddingVertical: 17, shadowColor: '#000', shadowOpacity: 0.14, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 8 }}>
          <ActivityIndicator size="small" color={t.dark ? '#FFFFFF' : '#111111'} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={[type.subhead, { color: t.label, fontWeight: '600' }]}>{title || 'Please wait…'}</Text>
            <Text numberOfLines={1} style={[type.caption, { color: t.secondary }]}>{message || 'Please wait…'}</Text>
          </View>
        </View>
      </View>
    </Modal>
  );
}

export function ResultsSkeleton({ count = 3 }: { count?: number }) {
  const t = useTheme();
  const opacity = useRef(new Animated.Value(0.38)).current;
  useEffect(() => {
    const pulse = Animated.loop(Animated.sequence([
      Animated.timing(opacity, { toValue: 0.82, duration: 720, useNativeDriver: true }),
      Animated.timing(opacity, { toValue: 0.38, duration: 720, useNativeDriver: true }),
    ]));
    pulse.start();
    return () => pulse.stop();
  }, [opacity]);
  const block = (width: number | `${number}%`, height: number, radius = 6) => <Animated.View style={{ width, height, borderRadius: radius, backgroundColor: t.fill, opacity }} />;
  return (
    <View accessibilityLabel="Loading search results" style={{ gap: 10, marginTop: 24 }}>
      {Array.from({ length: count }, (_, i) => (
        <View key={i} style={{ width: '100%', minHeight: 142, flexDirection: 'row', gap: 14, alignItems: 'center', backgroundColor: t.card, borderRadius: 16, borderWidth: 1, borderColor: t.separator, padding: 14 }}>
          {block(112, 112, 18)}
          <View style={{ flex: 1, gap: 9 }}>
            {block('42%', 10)}{block('76%', 17, 5)}{block('58%', 11)}{block('94%', 10)}{block('68%', 10)}
          </View>
        </View>
      ))}
    </View>
  );
}

/** A scrolling page on the grouped background with room above the floating tab bar. */
export function Screen({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: t.bg }}
      contentInsetAdjustmentBehavior="automatic"
      keyboardDismissMode="interactive"
      keyboardShouldPersistTaps="handled"
      contentContainerStyle={{ padding: 16, paddingBottom: 148, width: '100%', maxWidth: 640, alignSelf: 'center' }}>
      {children}
    </ScrollView>
  );
}

/** Rounded white block with a small heading above and a note below, like Settings on iPhone. */
export function Group({ title, footer, children }: { title?: string; footer?: string; children: ReactNode }) {
  const t = useTheme();
  const items = Children.toArray(children);
  if (items.length === 0) return null;
  return (
    <View style={{ marginTop: 24 }}>
      {title ? (
        <Text style={[type.footnote, { color: t.secondary, marginLeft: 16, marginBottom: 6, textTransform: 'uppercase' }]}>{title}</Text>
      ) : null}
      <View style={{ backgroundColor: t.card, borderRadius: 12, overflow: 'hidden' }}>
        {items.map((child, index) => (
          <View key={index}>
            {index > 0 ? <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: t.separator }} /> : null}
            {child}
          </View>
        ))}
      </View>
      {footer ? <Text style={[type.footnote, { color: t.secondary, marginHorizontal: 16, marginTop: 6 }]}>{footer}</Text> : null}
    </View>
  );
}

export function Row({
  children,
  onPress,
  disabled,
  style,
  label,
}: {
  children: ReactNode;
  onPress?: () => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  label?: string;
}) {
  const t = useTheme();
  const base: ViewStyle = { paddingHorizontal: 16, paddingVertical: 12, minHeight: 44, justifyContent: 'center' };
  if (!onPress) return <View style={[base, style]}>{children}</View>;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [base, style, { backgroundColor: pressed ? t.fill : 'transparent', opacity: disabled ? 0.4 : 1 }]}>
      {children}
    </Pressable>
  );
}

export function Field({ inputRef, ...props }: TextInputProps & { inputRef?: Ref<TextInput> }) {
  const t = useTheme();
  return (
    <TextInput
      ref={inputRef}
      placeholderTextColor={t.tertiary}
      selectionColor={t.accent}
      {...props}
      style={[type.body, { color: t.label, paddingHorizontal: 16, paddingVertical: 12, minHeight: 44 }, NO_OUTLINE, props.style]}
    />
  );
}

const FIELD_SYMBOLS: Record<string, { ios: SFSymbol; android: AndroidSymbol; web: AndroidSymbol }> = {
  'person-outline': { ios: 'person', android: 'person', web: 'person' },
  'location-outline': { ios: 'mappin.and.ellipse', android: 'location_on', web: 'location_on' },
  'at-outline': { ios: 'at', android: 'alternate_email', web: 'alternate_email' },
  'mail-outline': { ios: 'envelope', android: 'mail', web: 'mail' },
  'lock-closed-outline': { ios: 'lock', android: 'lock', web: 'lock' },
  search: { ios: 'magnifyingglass', android: 'search', web: 'search' },
};

export function IconField({ icon, inputRef, containerStyle, ...props }: TextInputProps & { icon: keyof typeof FIELD_SYMBOLS; inputRef?: Ref<TextInput>; containerStyle?: StyleProp<ViewStyle> }) {
  const t = useTheme();
  return (
    <View style={[{ minHeight: 54, flexDirection: 'row', alignItems: 'center', paddingLeft: 16, paddingRight: 4 }, containerStyle]}>
      <SymbolView name={FIELD_SYMBOLS[icon]} size={18} tintColor={t.secondary} weight="regular" />
      <Field inputRef={inputRef} {...props} style={[{ flex: 1, paddingHorizontal: 12 }, props.style]} />
    </View>
  );
}

export function ToggleRow({ value, onChange, children }: { value: boolean; onChange: (v: boolean) => void; children: ReactNode }) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      onPress={() => onChange(!value)}
      style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16, borderRadius: 16, borderWidth: 1, borderColor: value ? `${t.accent}80` : t.separator, backgroundColor: value ? `${t.accent}0A` : t.card, opacity: pressed ? 0.82 : 1 })}>
      <View style={{ width: 38, height: 38, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: `${t.accent}16` }}>
        <Ionicons name={value ? 'shield-checkmark' : 'shield-checkmark-outline'} size={21} color={t.accent} />
      </View>
      <View style={{ flex: 1, gap: 3 }}>
        {children}
        <Text style={[type.caption, { color: value ? t.accent : t.secondary }]}>{value ? 'Consent confirmed' : 'Required before searching'}</Text>
      </View>
      <View style={{ width: 48, height: 28, borderRadius: 14, justifyContent: 'center', backgroundColor: value ? t.accent : t.fill }}>
        <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: t.card, transform: [{ translateX: value ? 23 : 3 }], shadowColor: '#000000', shadowOpacity: 0.16, shadowRadius: 2, shadowOffset: { width: 0, height: 1 }, elevation: 1 }} />
      </View>
    </Pressable>
  );
}

export function Button({
  title,
  onPress,
  loading,
  disabled,
  destructive,
  icon,
}: {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  destructive?: boolean;
  icon?: IconName;
}) {
  const t = useTheme();
  const off = disabled || loading;
  const background = destructive ? t.red : t.dark ? '#F5F5F7' : '#111111';
  const foreground = destructive ? '#FFFFFF' : t.dark ? '#111111' : '#FFFFFF';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!off, busy: !!loading }}
      disabled={off}
      onPress={onPress}
      style={({ pressed }) => ({
        backgroundColor: background,
        opacity: disabled && !loading ? 0.4 : pressed ? 0.8 : 1,
        borderRadius: 999,
        minHeight: 50,
        paddingHorizontal: 20,
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        gap: 8,
      })}>
      {icon ? <Ionicons name={icon} size={18} color={foreground} /> : null}
      <Text style={[type.headline, { color: foreground }]}>{title}</Text>
    </Pressable>
  );
}

/** Plain blue text button for rows inside a Group. */
export function TextAction({ title, onPress, loading, disabled, destructive, icon }: {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  destructive?: boolean;
  icon?: IconName;
}) {
  const t = useTheme();
  const color = destructive ? t.red : t.accent;
  return (
    <Row onPress={() => { if (!disabled && !loading) onPress(); }} disabled={disabled} label={title}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        {icon ? <Ionicons name={icon} size={18} color={color} /> : null}
        <Text style={[type.body, { color, fontWeight: '600' }]}>{title}</Text>
      </View>
    </Row>
  );
}

export function ErrorText({ message }: { message: string }) {
  const t = useTheme();
  return (
    <View accessibilityRole="alert" style={{ flexDirection: 'row', gap: 8, alignItems: 'flex-start' }}>
      <Ionicons name="warning" size={18} color={t.red} style={{ marginTop: 1 }} />
      <Text style={[type.subhead, { color: t.red, flex: 1 }]}>{message}</Text>
    </View>
  );
}

export function Tile({ count, label, color }: { count: number; label: string; color: string }) {
  const t = useTheme();
  return (
    <View
      accessible
      accessibilityLabel={`${count} ${label}`}
      style={{ flex: 1, alignItems: 'center', paddingVertical: 12, borderRadius: 12, backgroundColor: t.card }}>
      <Text style={[type.title, { color, fontSize: 24 }]}>{count}</Text>
      <Text style={[type.caption, { color: t.secondary, textAlign: 'center' }]}>{label}</Text>
    </View>
  );
}

export function Chip({ text, color }: { text: string; color: string }) {
  return (
    <View style={{ alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, overflow: 'hidden' }}>
      <View style={[StyleSheet.absoluteFill, { backgroundColor: color, opacity: 0.14 }]} />
      <Text style={[type.caption, { color, fontWeight: '600' }]}>{text}</Text>
    </View>
  );
}

export function ProgressBar({ value, max }: { value: number; max: number }) {
  const t = useTheme();
  const pct = Math.max(0, Math.min(1, max > 0 ? value / max : 0));
  return (
    <View style={{ height: 6, borderRadius: 3, backgroundColor: t.fill, overflow: 'hidden', marginTop: 8 }}>
      <View style={{ width: `${pct * 100}%`, height: '100%', backgroundColor: pct >= 1 ? t.red : t.accent }} />
    </View>
  );
}
