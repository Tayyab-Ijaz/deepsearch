import { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Linking, Pressable, Text, View } from 'react-native';
import { InfoPage, InfoSection } from '../components/InfoPage';
import { Button, ErrorText, Field } from '../components/ui';
import { SUPPORT_EMAIL } from '../lib/config';
import { haptic } from '../lib/utils';
import { type, useTheme } from '../theme/theme';

export default function ReviewScreen() {
  const t = useTheme();
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function submit() {
    if (!rating) { setError('Choose a star rating first.'); return; }
    setError(null);
    const subject = encodeURIComponent(`App feedback — ${rating}/5 stars`);
    const body = encodeURIComponent(`Rating: ${rating}/5\n\nFeedback:\n${message.trim() || '(No written feedback)'}`);
    try {
      await Linking.openURL(`mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`);
      setSent(true);
      haptic('success');
    } catch { setError('Could not open an email app. Please contact support directly.'); }
  }

  return (
    <InfoPage icon="star-outline" eyebrow="Your feedback moves us forward" title="Help shape DeepSearch AI" intro="Share a quick rating or an idea. Your feedback opens as an email draft for you to review before sending.">
      <InfoSection title="How is your experience?">Your feedback helps us improve search quality and the app experience.</InfoSection>
      <View style={{ backgroundColor: t.card, borderRadius: 16, borderWidth: 1, borderColor: t.separator, padding: 16, gap: 14 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 12 }}>
          {[1, 2, 3, 4, 5].map((star) => (
            <Pressable key={star} accessibilityRole="button" accessibilityLabel={`${star} star${star === 1 ? '' : 's'}`} accessibilityState={{ selected: rating === star }} onPress={() => { setRating(star); setSent(false); }} hitSlop={6}>
              <Ionicons name={star <= rating ? 'star' : 'star-outline'} size={34} color={star <= rating ? t.orange : t.tertiary} />
            </Pressable>
          ))}
        </View>
        <Field placeholder="What should we improve? (optional)" value={message} onChangeText={(value) => { setMessage(value); setSent(false); }} multiline textAlignVertical="top" style={{ minHeight: 110, borderRadius: 12, backgroundColor: t.bg, padding: 12, fontSize: 15 }} />
        <Button title={sent ? 'Email draft opened' : 'Continue by email'} icon="mail-outline" onPress={() => void submit()} disabled={sent} />
        {error ? <ErrorText message={error} /> : null}
        {sent ? <Text style={[type.caption, { color: t.secondary, textAlign: 'center' }]}>Your feedback is not sent until you send the email.</Text> : null}
      </View>
    </InfoPage>
  );
}
