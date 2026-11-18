from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app
from .conftest import authenticate
from app.services.transcript_parser import parse_platform_export, parse_transcript


def test_parser_supports_whatsapp_json_and_csv():
    wa = parse_transcript(
        b"1/2/2024, 10:00 - Alex: I love hiking\n1/2/2024, 10:01 - Sam: Nice!\n",
        "chat.txt",
    )
    assert wa.format_detected == "whatsapp"
    assert wa.speakers == ["Alex", "Sam"]
    assert wa.messages[0].timestamp

    js = parse_transcript(b'[{"from":"Alex","body":"I prefer trains","date":"2024-02-01"}]', "chat.json")
    assert js.format_detected == "json" and js.messages[0].sender == "Alex"

    csv_data = b"sender,message,timestamp\nAlex,Remote work is useful,2024-03-01\nSam,Agreed,2024-03-02\n"
    csv_result = parse_transcript(csv_data, "chat.csv")
    assert csv_result.format_detected == "csv" and len(csv_result.messages) == 2


def test_platform_parsers_support_social_json_html_and_zip():
    instagram_payload = {
        "thread_path": "inbox/alex",
        "participants": [{"name": "Alex"}],
        "messages": [
            {"sender_name": "Alex", "timestamp_ms": 1768492200000, "content": "hello 👋"},
            {"sender_name": "Me", "photos": [{"uri": "x"}]},
        ],
    }
    instagram = parse_platform_export(
        __import__("json").dumps(instagram_payload).encode(),
        "instagram.json", "instagram",
    )
    assert instagram.platform == "instagram"
    assert instagram.participants == ["Alex", "Me"]
    assert instagram.messages[0].timestamp and "hello" in instagram.messages[0].text
    assert "Attachment" in instagram.messages[1].text

    telegram = parse_platform_export(
        b'{"name":"Alex","type":"personal_chat","messages":[{"id":1,"date":"2026-01-15T18:30:00","from":"Alex","text":[{"type":"plain","text":"hello"}]}]}',
        "result.json", "telegram",
    )
    assert telegram.messages[0].sender == "Alex" and telegram.messages[0].timestamp == "2026-01-15T18:30:00"

    html = b'<div class="_a6-g"><div class="from_name">Alex</div><div class="text">Hello from HTML</div><div class="date"><span title="2026-01-15T18:30:00"></span></div></div><div class="_a6-g"><div class="from_name">Me</div><div class="text">Hi</div></div>'
    messenger = parse_platform_export(html, "messages.html", "messenger")
    assert messenger.platform == "messenger" and len(messenger.messages) == 2 and messenger.messages[0].timestamp == "2026-01-15T18:30:00"

    import zipfile
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("chat.txt", "Alex: zipped hello\nMe: reply\n")
    zipped_result = parse_platform_export(archive.getvalue(), "whatsapp-export.zip", "whatsapp")
    assert zipped_result.platform == "whatsapp" and zipped_result.messages[0].text == "zipped hello"


def test_virtual_friend_upload_chat_unknown_and_isolation():
    with TestClient(app) as client:
        authenticate(client, "alex-audit@example.com")
        first = client.post("/api/virtual-friends/", json={"name": "Alex"})
        second = client.post("/api/virtual-friends/", json={"name": "Sam"})
        assert first.status_code == 201 and second.status_code == 201
        alex, sam = first.json(), second.json()

        body = b"1/2/2024, 10:00 - Alex: I love hiking and quiet mountains.\n1/2/2024, 10:01 - User: You should go this weekend.\n"
        uploaded = client.post(
            f"/api/virtual-friends/{alex['id']}/transcripts/upload",
            files={"file": ("same.txt", io.BytesIO(body), "text/plain")},
            data={"target_speaker": "Alex"},
        )
        assert uploaded.status_code == 200, uploaded.text

        unknown = client.post(
            "/api/virtual-friends/chat",
            json={"friend_id": alex["id"], "message": "What do they think about quantum taxation?"},
        )
        assert unknown.status_code == 200
        assert "couldn't find enough evidence" in unknown.json()["message"].lower()
        assert unknown.json()["confidence"] == "INSUFFICIENT"

        cross_friend = client.post(
            "/api/virtual-friends/chat",
            json={"friend_id": sam["id"], "message": "What do they say about hiking?"},
        )
        assert cross_friend.status_code == 200
        assert cross_friend.json()["evidence"] == []


def test_duplicate_filename_deletion_and_reprocess():
    with TestClient(app) as client:
        authenticate(client, "delete-audit@example.com")
        friend = client.post("/api/virtual-friends/", json={"name": "Delete Test"}).json()
        endpoint = f"/api/virtual-friends/{friend['id']}/transcripts/upload"
        payload = b"A: I like tea\nB: Good to know\n"
        one = client.post(endpoint, files={"file": ("same.txt", io.BytesIO(payload), "text/plain")}).json()
        two = client.post(endpoint, files={"file": ("same.txt", io.BytesIO(payload), "text/plain")}).json()
        assert client.post(f"/api/virtual-friends/{friend['id']}/transcripts/{two['transcript_id']}/reprocess").status_code == 200
        assert client.delete(f"/api/virtual-friends/{friend['id']}/transcripts/{one['transcript_id']}").status_code == 204
        remaining = client.get(f"/api/virtual-friends/{friend['id']}/transcripts").json()
        assert [item["id"] for item in remaining] == [two["transcript_id"]]


def test_import_preview_requires_explicit_participant_confirmation():
    with TestClient(app) as client:
        authenticate(client, "import-audit@example.com")
        content = b'{"messages":[{"sender_name":"Alex","timestamp_ms":1768492200000,"content":"I like tea"},{"sender_name":"Me","content":"Nice"}]}'
        preview = client.post(
            "/api/virtual-friends/imports/preview",
            files={"file": ("instagram.json", io.BytesIO(content), "application/json")},
            data={"platform": "instagram"},
        )
        assert preview.status_code == 201, preview.text
        body = preview.json()
        assert body["participants"] == ["Alex", "Me"]
        invalid = client.post(f"/api/virtual-friends/imports/{body['import_id']}/confirm", json={"target_speaker": "Unknown"})
        assert invalid.status_code == 422
        confirmed = client.post(
            f"/api/virtual-friends/imports/{body['import_id']}/confirm",
            json={"target_speaker": "Alex", "friend_name": "Alex imported"},
        )
        assert confirmed.status_code == 201, confirmed.text
        assert confirmed.json()["message_count"] == 1

