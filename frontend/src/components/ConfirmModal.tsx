import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, Text, TextInput, View } from 'react-native';
import { type, useTheme } from '../theme/theme';
import { ErrorText, NO_OUTLINE } from './ui';

type Props = {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  destructive?: boolean;
  /** When set, the person must type their password before confirming. */
  passwordLabel?: string;
  busy?: boolean;
  error?: string | null;
  onConfirm: (password: string) => void;
  onCancel: () => void;
};

/** One dialog for every confirmation, so it looks and works the same on iPhone, Android and web. */
export function ConfirmModal({ visible, title, message, confirmLabel, destructive, passwordLabel, busy, error, onConfirm, onCancel }: Props) {
  const t = useTheme();
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (!visible) setPassword('');
  }, [visible]);

  const needsPassword = passwordLabel !== undefined;
  const canConfirm = !busy && (!needsPassword || password.length > 0);
  const confirmColor = destructive ? t.red : t.accent;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
        <View style={{ width: '100%', maxWidth: 320, borderRadius: 14, backgroundColor: t.card, overflow: 'hidden' }}>
          <View style={{ padding: 20, gap: 8 }}>
            <Text accessibilityRole="header" style={[type.headline, { color: t.label, textAlign: 'center' }]}>
              {title}
            </Text>
            <Text style={[type.footnote, { color: t.secondary, textAlign: 'center' }]}>{message}</Text>
            {needsPassword ? (
              <TextInput
                value={password}
                onChangeText={setPassword}
                placeholder={passwordLabel}
                placeholderTextColor={t.tertiary}
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
                textContentType="password"
                style={[type.body, { color: t.label, backgroundColor: t.fill, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, marginTop: 8 }, NO_OUTLINE]}
              />
            ) : null}
            {error ? <ErrorText message={error} /> : null}
          </View>
          <View style={{ flexDirection: 'row', gap: 8, padding: 10, borderTopWidth: 0.5, borderTopColor: t.separator }}>
            <Pressable accessibilityRole="button" onPress={onCancel} style={{ flex: 1, padding: 12, alignItems: 'center', borderRadius: 999, backgroundColor: t.fill }}>
              <Text style={[type.body, { color: t.accent }]}>Cancel</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              disabled={!canConfirm}
              onPress={() => onConfirm(password)}
              style={{ flex: 1, padding: 12, alignItems: 'center', borderRadius: 999, backgroundColor: destructive ? `${t.red}18` : t.fill, opacity: canConfirm ? 1 : 0.4 }}>
              <Text style={[type.body, { color: confirmColor, fontWeight: '600' }]}>{confirmLabel}</Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
