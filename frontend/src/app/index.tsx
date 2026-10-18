import { Redirect } from 'expo-router';
import { useAuth } from '../lib/auth';

/** Entry point: send people to the app or to sign-in, depending on their saved session. */
export default function Index() {
  const { status } = useAuth();
  return <Redirect href={status === 'signedIn' ? '/people' : '/sign-in'} />;
}
