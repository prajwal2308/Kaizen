# Reel Notes

Share a reel to it. Get the takeaway back as a notification. Never rewatch.

This is the backend plus an iOS Shortcut — deliberately **not** an App Store app.
It gives you the real share-sheet UX on your own iPhone today, with no Apple
Developer account, no Mac, and no App Store review. When the habit proves out,
the iOS app replaces the Shortcut and nothing here changes except `notify.py`.

## How it works

```
iOS share sheet → Shortcut → POST /ingest → 202 immediately (share sheet closes)
                                              │
                            yt-dlp ───────────┤ download reel
                            ffmpeg ───────────┤ 16 kHz mono audio + 4 stills
                            whisper ──────────┤ transcript
                            Claude ───────────┤ typed note (title, takeaways,
                                              │   steps, key facts, caveats)
                            SQLite + FTS5 ────┤ stored and searchable
                            ntfy ─────────────┘ push to your lock screen
```

Two design decisions worth knowing:

**The stills are not decoration.** Reels routinely put the numbers, formulas and
lists on screen and never say them out loud. Four frames go to Claude alongside
the transcript, so a "how to calculate X" reel yields the actual calculation.

**One note schema, not one per category.** Category-specific guidance lives in
the prompt; the schema stays flat. The `steps` field is the one that earns its
keep — it is the difference between "explains a budgeting rule" and a procedure
you can follow without opening the video again.

## The honest caveat

Meta offers no API that returns a third-party reel's media, so ingestion uses
yt-dlp against URLs you already have access to. That means:

- It needs a logged-in cookie jar for most Instagram and Facebook links.
- It will break periodically when Meta changes something. Budget for upkeep.
- It is against Meta's ToS. Fine for archiving your own saves to your own
  server; think hard before pointing it at other people.

Nothing here rehosts video. Only derived notes, one transcript, and one
thumbnail per reel are stored.

## Run it locally

```bash
cd reelnotes
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # needs ffmpeg on PATH
cp .env.example .env                     # then fill it in
set -a && source .env && set +a
uvicorn app.main:app --reload
```

Open `http://localhost:8000/?k=$REELNOTES_API_KEY`.

`REELNOTES_API_KEY` is required — the service refuses to start without one. It
downloads and transcribes whatever URL it is handed, so an unauthenticated
instance is somebody else's free compute.

## Cookies

Most Instagram and Facebook URLs return a login wall to a server. Export cookies
from a browser where you are logged in (any "Netscape format" cookie exporter
extension), save as `cookies.txt`, and point `YTDLP_COOKIES_FILE` at it. Treat
that file like a password — it *is* your session.

## Deploy

The `Dockerfile` installs ffmpeg and runs uvicorn on `$PORT`; it works as-is on
Railway, Fly, or Render.

```bash
fly launch --dockerfile Dockerfile
fly volumes create data --size 1          # notes must outlive a redeploy
fly secrets set REELNOTES_API_KEY=... ANTHROPIC_API_KEY=... NTFY_TOPIC=...
```

Mount the volume at `/data` and set `REELNOTES_DB=/data/reelnotes.sqlite3`. Set
`PUBLIC_BASE_URL` to your deployed URL so notifications are tappable.

## Push notifications

Install the **ntfy** app (free, iOS and Android) and subscribe to the topic you
set as `NTFY_TOPIC`. Anyone who guesses the topic name can read your notes, so
make it long and random.

This is a stand-in for APNs. It costs nothing and needs no developer account;
the tradeoff is a generic app icon on the notification.

## The iOS Shortcut

1. **Shortcuts** app → **+** → name it *Save Reel*.
2. Open shortcut details (ⓘ) → turn on **Show in Share Sheet**. Set accepted
   input to **URLs** and **Text** (Instagram sometimes shares text with the URL
   inside it; the server pulls the URL out either way).
3. Add one action: **Get Contents of URL**.
   - URL: `https://your-app.fly.dev/ingest`
   - Method: **POST**
   - Headers: `X-API-Key` = your key, `Content-Type` = `application/json`
   - Request Body: **JSON**, one field — key `url`, type Text, value
     **Shortcut Input**
4. Add nothing else. No "Show Result" action — the point is that it closes
   instantly and the answer arrives later as a notification.

Now: reel → Share → *Save Reel* → the sheet closes. Thirty seconds later the
takeaway lands on your lock screen.

## Reading your notes

- Notification → tap → the note.
- `https://your-app/?k=<key>` — newest first, with search that covers titles,
  takeaways, steps, key facts and the full transcript. Bookmark it to your home
  screen. (Newest first is not a feature so much as a correction.)
- `GET /api/notes?q=...` with the `X-API-Key` header, if you want the JSON.

## Costs

Per reel: transcription is free on the local `faster-whisper` backend (slower on
a small box) or about $0.006/minute hosted; the Claude call runs a fraction of a
cent for a 60-second reel. The server is the only real line item.

Set `REELNOTES_ASR=openai` with an `OPENAI_API_KEY` if CPU whisper is too slow
on your host — it is the one place this project talks to a non-Anthropic model,
because Claude does not do speech-to-text.

## Deliberately not built yet

Wait until the habit is proven before adding: a real job queue (background tasks
run in-process, which is fine for one user), multi-user auth, the iOS app, and
the finance-reel calculator that turns `steps` into inputs you can edit. The
open question this is meant to answer is not "does it work" — it is whether you
actually read the notifications.

## Tests

```bash
cd reelnotes && python -m pytest -q && python -m ruff check app tests
```

The suite covers storage and search, the extraction request shape, and the HTTP
surface. It does not cover the yt-dlp download — that depends on Meta's servers
and a live session, so it fails loudly at runtime instead.
