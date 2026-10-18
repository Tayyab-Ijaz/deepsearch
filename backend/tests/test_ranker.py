from app.services.ranker import RawHit, canonical, classify_url, label_for, name_similarity, rank, title_to_name


def test_title_to_name():
    assert title_to_name("John Smith (@johnsmith) • Instagram photos and videos") == "John Smith"
    assert title_to_name("John Smith - Engineer - Acme | LinkedIn") == "John Smith"
    assert title_to_name("John Smith | Facebook") == "John Smith"


def test_similarity_orders_sensibly():
    exact = name_similarity("John Smith", "John Smith")
    close = name_similarity("John Smith", "Jonathan Smith")
    far = name_similarity("John Smith", "Maria Garcia")
    assert exact > close > far
    assert exact >= 0.99 and far < 0.5


def test_initials_match():
    assert name_similarity("J Smith", "John Smith") >= 0.85


def test_non_latin_names():
    assert name_similarity("محمد علي", "محمد علي") >= 0.99
    assert name_similarity("أحمد", "فاطمة") < 0.5


def test_classify_urls():
    assert classify_url("https://www.linkedin.com/in/john-smith-1a2b3c4d")[0] == "linkedin"
    assert classify_url("https://www.instagram.com/johnsmith/")[0] == "instagram"
    assert classify_url("https://www.instagram.com/p/AbC123/") is None
    assert classify_url("https://www.instagram.com/reel/AbC123/") is None
    assert classify_url("https://www.facebook.com/groups/12345") is None
    assert classify_url("https://x.com/home") is None
    assert classify_url("https://x.com/johnsmith")[0] == "x"
    assert classify_url("https://www.tiktok.com/@john.smith")[0] == "tiktok"
    assert classify_url("https://www.tiktok.com/discover/john") is None
    assert classify_url("https://johnsmith.dev/about")[0] == "web"
    assert classify_url("javascript:alert(1)") is None


def test_canonical_dedupes():
    assert canonical("https://www.instagram.com/JohnSmith/") == canonical("https://instagram.com/johnsmith")


def test_rank_drops_junk_and_never_invents():
    hits = [
        RawHit("John Smith - Engineer | LinkedIn", "https://www.linkedin.com/in/john-smith-1a2b3c4d", "NYC", provider="brave"),
        RawHit("John Smith (@johnsmith) • Instagram photos", "https://www.instagram.com/johnsmith/", "bio", provider="brave"),
        RawHit("Post by someone", "https://www.instagram.com/p/XyZ/", "", provider="brave"),
        RawHit("Totally Different Person | LinkedIn", "https://www.linkedin.com/in/other-person-99887766", "", provider="brave"),
        RawHit("John Smith duplicate", "https://instagram.com/johnsmith", "", provider="brave"),
    ]
    res = rank(hits, "John Smith", limit=5)
    urls = [r.profile_url for r in res]
    assert len(res) == 2  # fewer than 5 is fine: nothing is invented to fill the list
    assert not any("/p/" in u for u in urls)
    assert all(r.match_label in ("strong_match", "possible_match", "weak_match") for r in res)


def test_labels():
    assert label_for(0.9) == "strong_match"
    assert label_for(0.7) == "possible_match"
    assert label_for(0.5) == "weak_match"


def test_new_platform_profiles_are_recognised():
    from app.services.ranker import classify_url
    assert classify_url("https://www.youtube.com/@BarackObama/videos") == ("youtube", "@BarackObama".lstrip("@"))
    assert classify_url("https://www.youtube.com/watch?v=abc") is None
    assert classify_url("https://www.threads.com/@barackobama") == ("threads", "barackobama")
    assert classify_url("https://www.threads.net/@x/post/abc") is None
    assert classify_url("https://github.com/octocat") == ("github", "octocat")
    assert classify_url("https://github.com/octocat/hello-world") is None
    assert classify_url("https://github.com/features") is None
    assert classify_url("https://de.pinterest.com/johnsmith/") == ("pinterest", "johnsmith")
    assert classify_url("https://www.pinterest.com/pin/123/") is None


def test_same_profile_from_two_sources_is_merged_and_keeps_its_picture():
    hits = [
        RawHit(title="John Smith - Engineer | LinkedIn", url="https://uk.linkedin.com/in/john-smith-1", snippet="London", position=2),
        RawHit(title="John Smith | LinkedIn", url="https://www.linkedin.com/in/John-Smith-1/", thumbnail="https://img.example/a.jpg",
               provider="serper-images", position=100),
    ]
    res = rank(hits, "John Smith", limit=10)
    assert len(res) == 1
    assert res[0].image_url == "https://img.example/a.jpg" and res[0].description == "London"


def test_github_style_title_uses_the_real_name():
    assert title_to_name("octocat (The Octocat) · GitHub") == "The Octocat"


def test_relevant_count_counts_distinct_real_matches():
    from app.services.ranker import relevant_count
    hits = [RawHit(title="John Smith | LinkedIn", url="https://www.linkedin.com/in/john-smith-1"),
            RawHit(title="John Smith | LinkedIn", url="https://uk.linkedin.com/in/john-smith-1"),   # same profile
            RawHit(title="Jane Roe | LinkedIn", url="https://www.linkedin.com/in/jane-roe")]
    assert relevant_count(hits, "John Smith", None, "linkedin") == 1
