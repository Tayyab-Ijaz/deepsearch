import { InfoPage, InfoSection } from '../components/InfoPage';

export default function TermsScreen() {
  return (
    <InfoPage icon="document-text-outline" eyebrow="Search with care" title="Use DeepSearch AI responsibly" intro="A few clear ground rules help keep public profile search useful, lawful, and respectful.">
      <InfoSection title="Permitted use">Search only for yourself, someone who has agreed, or a well-known public figure. Do not use this service to stalk, harass, impersonate, discriminate against, or expose anyone.</InfoSection>
      <InfoSection title="Public information only">The app searches pages that search engines can access publicly. It does not access private accounts or bypass sign-in and privacy controls.</InfoSection>
      <InfoSection title="Results are not identity verification">A matching name, username, or public page does not prove who owns an account or that separate profiles belong to the same person. Verify information independently before relying on it.</InfoSection>
      <InfoSection title="Third-party services">Search providers and Google Gemini process requests needed for search and summaries under their own terms and privacy practices. Results can be incomplete, outdated, or unavailable.</InfoSection>
      <InfoSection title="Limits and availability">The service is provided as-is, subject to account usage limits and provider availability. Do not rely on it for urgent, legal, employment, or safety decisions.</InfoSection>
    </InfoPage>
  );
}
