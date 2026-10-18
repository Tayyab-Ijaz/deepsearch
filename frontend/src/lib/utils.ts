import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';
import * as WebBrowser from 'expo-web-browser';

/** Only plain web links are ever opened from the app. */
export function webUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : null;
  } catch {
    return null;
  }
}

export async function openLink(value: string | null | undefined): Promise<void> {
  const url = webUrl(value);
  if (url) await WebBrowser.openBrowserAsync(url);
}

export function haptic(kind: 'success' | 'error' | 'tap'): void {
  if (Platform.OS === 'web') return;
  if (kind === 'tap') void Haptics.selectionAsync();
  else void Haptics.notificationAsync(kind === 'success' ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Error);
}

export const clean = (value: string) => value.trim();
