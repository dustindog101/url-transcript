from url_transcript.urls import parse_url, UnsupportedURLError
import pytest


def test_youtube_watch():
    p = parse_url("https://www.youtube.com/watch?v=l1kiTz-19iQ")
    assert p.platform == "youtube"
    assert p.video_id == "l1kiTz-19iQ"


def test_youtube_shorts():
    p = parse_url("https://youtube.com/shorts/fVcAJTLCdaw?si=abc")
    assert p.platform == "youtube"
    assert p.video_id == "fVcAJTLCdaw"


def test_tiktok():
    p = parse_url(
        "https://www.tiktok.com/@deujbds/video/7675641781211467021?is_from_webapp=1&sender_device=pc"
    )
    assert p.platform == "tiktok"
    assert p.video_id == "7675641781211467021"


def test_instagram_reels():
    p = parse_url("https://www.instagram.com/reels/Dcr7BNSN2se/")
    assert p.platform == "instagram"
    assert p.video_id == "Dcr7BNSN2se"


def test_bad():
    with pytest.raises(UnsupportedURLError):
        parse_url("https://example.com/video/1")
