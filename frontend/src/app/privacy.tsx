import { InfoPage, InfoSection } from '../components/InfoPage';

export default function PrivacyScreen() {
  return (
    <InfoPage icon="lock-closed-outline" eyebrow="Your data, your choices" title="Privacy, made clear" intro="See what information powers a search, how it is used, and the choices you have along the way.">
      <InfoSection title="Account and security">Your account stores your email, optional display name, a salted password hash, sign-in token hashes, and daily usage counts. Passwords are never stored as plain text. If you reset your password, a one-time code is emailed to your address through our email provider (Resend) and is stored only as a short-lived hash. You can delete your account from Account settings.</InfoSection>
      <InfoSection title="Searches and providers">Search names and optional locations are sent to the configured web search provider to find public pages. Search result content is cached briefly in server memory to reduce repeat requests. Operational metrics store counts and timing, not the names or result profiles.</InfoSection>
      <InfoSection title="AI summaries">When you request a summary, the searched name and selected public search snippets are sent to Google Gemini to generate it. A summary may be incomplete and does not confirm that profiles belong to the same person.</InfoSection>
      <InfoSection title="Use responsibly">Only search for yourself, someone who agreed, or a well-known public figure. Do not use the app to harass, stalk, or expose private information.</InfoSection>
    </InfoPage>
  );
}
