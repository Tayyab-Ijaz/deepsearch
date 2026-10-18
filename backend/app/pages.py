"""Public pages the App Store asks for: privacy policy, terms and a support page.

They state what the service really does (see the services folder). If the service changes, change this text too."""
from __future__ import annotations

SUPPORT_EMAIL = "info@wellminddatasolutions.com"
UPDATED = "October 2026"

_STYLE = """
:root{--bg:#fff;--fg:#16181d;--muted:#5b6270;--line:#e3e6eb;--accent:#2a3350}
@media (prefers-color-scheme:dark){:root{--bg:#101216;--fg:#eceef2;--muted:#9aa2b1;--line:#262a33;--accent:#aab6e0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
main{max-width:720px;margin:0 auto;padding:32px 20px 64px}h1{font-size:30px;line-height:1.2;margin:0 0 4px}
h2{font-size:19px;margin:30px 0 6px}p,li{margin:8px 0}ul{padding-left:22px}a{color:var(--accent)}
.meta{color:var(--muted);font-size:14px;margin-bottom:18px}nav{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);font-size:14px}
nav a{margin-right:16px}
"""


def render(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title} - DeepSearch AI</title><style>{_STYLE}</style></head><body><main>"
        f'<h1>{title}</h1><div class="meta">DeepSearch AI &middot; Last updated {UPDATED}</div>{body}'
        '<nav><a href="/privacy">Privacy Policy</a><a href="/terms">Terms of Use</a><a href="/support">Support</a></nav>'
        "</main></body></html>"
    )


PRIVACY = f"""
<p>DeepSearch AI helps you find <strong>public profile pages</strong> that match a name. This policy explains what we
collect, who processes it, and the choices you have. Questions: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>.</p>

<h2>What we store</h2>
<ul>
<li><strong>Your account:</strong> email address, an optional display name, and a salted hash of your password
(never the password itself).</li>
<li><strong>Sessions:</strong> hashes of sign-in tokens, so you stay signed in and can sign out.</li>
<li><strong>Usage:</strong> how many searches and summaries you used today, to apply daily limits.</li>
<li><strong>Saved profiles:</strong> the public profiles you choose to save (name, platform, link, picture link).</li>
<li><strong>Security records:</strong> sign-in and reset attempts, kept as hashes with an expiry, to stop abuse.</li>
<li><strong>Aggregate metrics:</strong> counts and timings of searches. These do not contain the names searched
or the results.</li>
</ul>

<h2>What we do not store</h2>
<p>We do not store the names you search for or the search results. Results are held in server memory for about
15 minutes to avoid repeating the same request, then discarded.</p>

<h2>Who processes data for us</h2>
<ul>
<li><strong>Google Cloud / Firebase (Cloud Firestore):</strong> stores the account data above.</li>
<li><strong>Vercel:</strong> hosts the service.</li>
<li><strong>Serper (Google search results):</strong> receives the name, and the optional location, you search for,
to find public web pages and pictures.</li>
<li><strong>Google Gemini:</strong> if you request an AI summary, receives the searched name and the public search
snippets you selected.</li>
<li><strong>Resend:</strong> sends the one-time code email if you reset your password; it receives your email address
and the code.</li>
</ul>
<p>Our server may also request a public result page itself, only to read its preview picture. We never sign in to
any account and never access private profiles.</p>

<h2>Searching responsibly</h2>
<p>Search only for yourself, someone who has agreed, or a well-known public figure. You confirm this before each
search. A result is a public page that shares a name; it is not proof that the page belongs to a particular person.</p>

<h2>Your choices</h2>
<ul>
<li><strong>Delete your account:</strong> in the app, open Account and choose Delete Account. This permanently removes
your account, sessions, usage records and saved profiles.</li>
<li><strong>Anything else:</strong> email us to ask what we hold about you or to have it corrected or removed.</li>
<li><strong>Information about you in search results:</strong> we do not host these pages; we only link to public pages
that search engines already index. To have a page removed, contact the website that publishes it, or ask the search
engine to remove it.</li>
</ul>

<h2>Retention</h2>
<p>Account data is kept until you delete your account. Password-reset codes expire after 15 minutes and are deleted
when used. Security records expire automatically.</p>

<h2>Children</h2>
<p>The service is not directed to children.</p>

<h2>Changes</h2>
<p>If we change this policy we will update the date above.</p>
"""

TERMS = f"""
<p>By creating an account or using DeepSearch AI you agree to these terms.</p>

<h2>Permitted use</h2>
<p>Search only for yourself, someone who has agreed, or a well-known public figure. Do not use the service to stalk,
harass, impersonate, discriminate against, or expose anyone, or to make decisions about employment, credit,
housing or safety.</p>

<h2>Public information only</h2>
<p>The service searches pages that search engines can access publicly. It does not access private accounts or
bypass sign-in and privacy controls, and you must not try to use it that way.</p>

<h2>Results are not identity verification</h2>
<p>A matching name, username, or public page does not prove who owns an account or that separate profiles belong to
the same person. Results can be incomplete, outdated or about someone else with the same name. Verify information
independently before relying on it.</p>

<h2>Your account</h2>
<p>Keep your password private. You are responsible for activity on your account. We may apply daily usage limits and
may suspend accounts that break these terms.</p>

<h2>Third-party services</h2>
<p>Search, AI summaries and email are provided by third parties under their own terms and privacy practices (see our
<a href="/privacy">Privacy Policy</a>). They may be unavailable at times.</p>

<h2>No warranty</h2>
<p>The service is provided as is, without warranties. To the extent the law allows, we are not liable for losses
arising from its use or from decisions made on its results.</p>

<h2>Contact</h2>
<p><a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
"""

SUPPORT = f"""
<p>Need help? A person reads every message. Email
<a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a> and tell us what happened, which screen you were on, and the
email address of your account (never your password).</p>

<h2>Common questions</h2>
<p><strong>I forgot my password.</strong> On the sign-in screen tap <em>Forgot password?</em>. We email a 6-digit code
that works for 15 minutes.</p>
<p><strong>I did not receive the code.</strong> Check your spam folder, wait a minute, and request a new one. Each address
can request a few codes every 15 minutes.</p>
<p><strong>How do I delete my account and data?</strong> In the app open Account, then Delete Account. This permanently
removes your account and saved profiles.</p>
<p><strong>A profile about me appears in results.</strong> DeepSearch AI only links to public pages that search engines
already index and does not host them. To remove a page, contact the website that publishes it or ask the search engine
to remove it. We can also help you find the right place to ask.</p>
<p><strong>Why was a result wrong?</strong> Results match names only and can be about someone else. See our
<a href="/terms">Terms of Use</a>.</p>
"""
