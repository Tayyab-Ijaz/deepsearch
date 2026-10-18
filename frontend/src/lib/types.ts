export type User = { id: number; email: string; display_name: string | null; auth_provider?: 'password' };
export type AuthSession = { user: User; access_token: string; refresh_token: string; expires_in: number };
export type UsageCount = { used: number; limit: number };
export type Usage = { searches: UsageCount; summaries: UsageCount };
export type MeResponse = { user: User; usage: Usage };
export type FeaturesResponse = { ai_summary: boolean };

export type MatchLabel = 'strong_match' | 'possible_match' | 'weak_match';
export type PersonResult = {
  name: string;
  platform: string;
  platform_key: string;
  title: string;
  description: string;
  profile_url: string;
  image_url: string | null;
  match_label: MatchLabel;
  match_score: number;
  source: string;
};
export type SavedPerson = { id: string; person: PersonResult; saved_at: number };
export type SavedPeopleResponse = { results: SavedPerson[] };
export type SearchResponse = { results: PersonResult[]; took_ms: number; warnings: string[] };
export type SummaryResponse = { summary: string; disclaimer: string };

export type UsernameVerdict = 'confirmed' | 'unverified' | 'not_found' | 'unchecked';
export type UsernameRow = {
  key: string;
  platform: string;
  experimental: boolean;
  verdict: UsernameVerdict;
  reason: string;
  url: string | null;
};
export type UsernameResponse = { username: string; platforms: UsernameRow[]; took_ms: number };

