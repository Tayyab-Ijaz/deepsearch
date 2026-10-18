import { Image, View } from 'react-native';

// Logo is 437x549 (trimmed). `size` is the rendered height.
const RATIO = 437 / 549;

export function BrandMark({ size = 64 }: { size?: number }) {
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no"
      style={{ width: size * RATIO, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Image source={require('../../assets/logo.webp')} style={{ width: size * RATIO, height: size }} resizeMode="contain" />
    </View>
  );
}
