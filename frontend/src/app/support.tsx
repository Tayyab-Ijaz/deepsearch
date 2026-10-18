import { useState } from 'react';
import { Linking, Text, View } from 'react-native';
import { InfoPage, InfoSection } from '../components/InfoPage';
import { Button, ErrorText } from '../components/ui';
import { SUPPORT_EMAIL } from '../lib/config';
import { type, useTheme } from '../theme/theme';

export default function SupportScreen() {
  const t = useTheme();
  const [error, setError] = useState<string | null>(null);
  async function contact() {
    setError(null);
    try { await Linking.openURL(`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent('DeepSearch AI support')}`); }
    catch { setError('Could not open an email app on this device.'); }
  }
  return (
    <InfoPage icon="chatbubble-ellipses-outline" eyebrow="A real person can help" title="Let us sort it out" intro="Tell us what happened and where you got stuck. Include the screen or step that needs attention.">
      <InfoSection title="Email support">{SUPPORT_EMAIL}</InfoSection>
      <View style={{ marginTop: 4 }}><Button title="Write to Support" icon="mail-outline" onPress={() => void contact()} /></View>
      {error ? <ErrorText message={error} /> : null}
      <Text style={[type.caption, { color: t.secondary, textAlign: 'center', marginTop: 4 }]}>Support contact is configured by the app owner.</Text>
    </InfoPage>
  );
}
