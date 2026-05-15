#!/usr/bin/env python3
"""
StayinPuri Booking Alert Service
- 5 iCal feeds: Asiyana (Airbnb, Agoda) + Tulsi Vihar (Airbnb, Agoda, Booking.com)
- Silent polling — Telegram only fires on new booking / cancellation / modification
- Style B banner messages
"""

import os
import sqlite3
import logging
import time
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID")
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))
TZ                    = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
DB_PATH               = os.getenv("DB_PATH", "./bookings.db")
LOG_PATH              = os.getenv("LOG_PATH", "./stayinpuri.log")

# ── All 5 property+platform feeds ────────────────────────────────────────────
PROPERTIES = [
    {
        "name":     "Asiyana Apartment",
        "platform": "Airbnb",
        "ical_url": os.getenv("ASIYANA_AIRBNB_ICAL_URL", ""),
    },
    {
        "name":     "Asiyana Apartment",
        "platform": "Agoda",
        "ical_url": os.getenv("ASIYANA_AGODA_ICAL_URL", ""),
    },
    {
        "name":     "Tulsi Vihar Apartment",
        "platform": "Airbnb",
        "ical_url": os.getenv("TULSI_AIRBNB_ICAL_URL", ""),
    },
    {
        "name":     "Tulsi Vihar Apartment",
        "platform": "Agoda",
        "ical_url": os.getenv("TULSI_AGODA_ICAL_URL", ""),
    },
    {
        "name":     "Tulsi Vihar Apartment",
        "platform": "Booking.com",
        "ical_url": os.getenv("TULSI_BOOKING_ICAL_URL", ""),
    },
    # Future: Asiyana on Booking.com — just add ASIYANA_BOOKING_ICAL_URL to .env
    # {
    #     "name":     "Asiyana Apartment",
    #     "platform": "Booking.com",
    #     "ical_url": os.getenv("ASIYANA_BOOKING_ICAL_URL", ""),
    # },
]

PLATFORM_EMOJI = {
    "Airbnb":      "🏠",
    "Booking.com": "🅱️",
    "Agoda":       "🌏",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_PATH),
    ],
)
log = logging.getLogger(__name__)


# ── Database ──────────────────────────────────────────────────────────────────
def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            uid           TEXT PRIMARY KEY,
            property_name TEXT,
            platform      TEXT,
            summary       TEXT,
            dtstart       TEXT,
            dtend         TEXT,
            status        TEXT DEFAULT 'CONFIRMED',
            hash          TEXT,
            first_seen    TEXT,
            last_seen     TEXT
        )
    """)
    conn.commit()
    conn.close()
    log.info("Database ready: %s", DB_PATH)


def get_conn():
    return sqlite3.connect(DB_PATH)


# ── Helpers ───────────────────────────────────────────────────────────────────
def nights(dtstart: str, dtend: str) -> int:
    try:
        d1 = datetime.fromisoformat(dtstart).date()
        d2 = datetime.fromisoformat(dtend).date()
        return (d2 - d1).days
    except Exception:
        return 0


def fmt_date(d: str) -> str:
    """2026-04-27  ->  27 Apr 2026 (Mon)"""
    try:
        return datetime.fromisoformat(d).strftime("%d %b %Y (%a)")
    except Exception:
        return d


def now_ist() -> str:
    return datetime.now(TZ).strftime("%d %b %Y, %I:%M %p")


# ── iCal Fetcher ──────────────────────────────────────────────────────────────
def fetch_ical(prop: dict) -> list:
    url  = prop["ical_url"]
    name = prop["name"]

    if not url or not name:
        return []

    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "StayinPuri/1.0"})
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("Fetch failed [%s / %s]: %s", name, prop["platform"], e)
        return []

    bookings = []
    try:
        cal = Calendar.from_ical(resp.content)
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            uid     = str(component.get("UID", ""))
            summary = str(component.get("SUMMARY", "Booking"))
            status  = str(component.get("STATUS", "CONFIRMED")).upper()

            dtstart = component.get("DTSTART")
            dtend   = component.get("DTEND")
            if not dtstart or not dtend:
                continue

            start_dt  = dtstart.dt
            end_dt    = dtend.dt
            start_str = (start_dt.date() if hasattr(start_dt, "date") else start_dt).isoformat()
            end_str   = (end_dt.date()   if hasattr(end_dt,   "date") else end_dt).isoformat()

            platform = prop["platform"]

            # ── Platform-specific BLOCKED detection ───────────────────────────
            # Each platform uses different summary text for owner blocks vs bookings:
            #
            # Airbnb:      "Airbnb (Not available)" or "Blocked" = OWNER BLOCK
            #              Real bookings have guest ref codes as summary
            #
            # Booking.com: "CLOSED - Not available" = REAL GUEST BOOKING (privacy masked)
            #              Booking.com never sends real guest names in iCal
            #
            # Agoda:       "BOOKED" = REAL GUEST BOOKING
            #              "Not available" = OWNER BLOCK
            #
            summary_lower = summary.lower()

            if platform == "Airbnb":
                # Airbnb owner blocks say "Not available" or "Blocked"
                if any(x in summary_lower for x in ["not available", "blocked", "unavailable"]):
                    status = "BLOCKED"

            elif platform == "Booking.com":
                # Booking.com masks ALL bookings as "CLOSED - Not available"
                # These are REAL bookings, not owner blocks — keep as CONFIRMED
                # Only mark BLOCKED if iCal STATUS field is explicitly CANCELLED
                if status == "CANCELLED":
                    pass  # keep as CANCELLED
                else:
                    status = "CONFIRMED"  # always confirmed for Booking.com

            elif platform == "Agoda":
                # Agoda: "Not available" = owner block, "BOOKED" = real booking
                if any(x in summary_lower for x in ["not available", "unavailable", "closed"]):
                    status = "BLOCKED"

            content_hash = hashlib.md5(
                f"{uid}{start_str}{end_str}{status}".encode()
            ).hexdigest()

            bookings.append({
                "uid":           uid,
                "property_name": name,
                "platform":      prop["platform"],
                "summary":       summary,
                "dtstart":       start_str,
                "dtend":         end_str,
                "status":        status,
                "hash":          content_hash,
            })
    except Exception as e:
        log.error("Parse error [%s]: %s", name, e)

    log.info("Fetched %d events — %s / %s", len(bookings), name, prop["platform"])
    return bookings


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message: str, retries: int = 3):
    """Send Telegram message with retry on failure."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       message,
                "parse_mode": "HTML",
            }, timeout=10)
            resp.raise_for_status()
            log.info("Telegram sent OK")
            return
        except requests.RequestException as e:
            log.error("Telegram attempt %d/%d failed: %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(2 * attempt)


# ── Message Formatters — Style 4 ─────────────────────────────────────────────
PROPERTY_EMOJI = {
    "Asiyana Apartment":     "🏠",
    "Tulsi Vihar Apartment": "🏡",
}


def _prop_short(name: str) -> str:
    """Asiyana Apartment -> ASIYANA"""
    return name.replace(" Apartment", "").upper()


def _platform_str(platform: str) -> str:
    colors = {
        "Airbnb":      "Airbnb",
        "Booking.com": "Booking.com",
        "Agoda":       "Agoda",
    }
    return colors.get(platform, platform)


def _body(b: dict) -> str:
    n         = nights(b["dtstart"], b["dtend"])
    night_str = f"{n} night{'s' if n != 1 else ''}"
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>{fmt_date(b['dtstart'])}</b> → <b>{fmt_date(b['dtend'])}</b>\n"
        f"🌙 {night_str}   📦 <b>{_platform_str(b['platform'])}</b>\n"
        f"🔖 <code>{b['uid'][:20]}</code>\n"
        f"⏰ {now_ist()} IST"
    )


def msg_new(b: dict) -> str:
    p_emoji = PROPERTY_EMOJI.get(b["property_name"], "🏡")
    short   = _prop_short(b["property_name"])
    return (
        f"{p_emoji} <b>{short}</b>  ·  ✅ <b>BOOKED</b>\n"
        f"{_body(b)}"
    )


def msg_cancelled(b: dict) -> str:
    p_emoji = PROPERTY_EMOJI.get(b["property_name"], "🏡")
    short   = _prop_short(b["property_name"])
    return (
        f"{p_emoji} <b>{short}</b>  ·  ❌ <b>CANCELLED</b>\n"
        f"{_body(b)}"
    )


def msg_modified(b: dict) -> str:
    p_emoji = PROPERTY_EMOJI.get(b["property_name"], "🏡")
    short   = _prop_short(b["property_name"])
    return (
        f"{p_emoji} <b>{short}</b>  ·  ✏️ <b>MODIFIED</b>\n"
        f"{_body(b)}"
    )


# ── Core Sync ─────────────────────────────────────────────────────────────────
def sync_property(prop: dict):
    bookings = fetch_ical(prop)
    if not bookings:
        return

    now_iso    = datetime.now(timezone.utc).isoformat()
    seen_uids  = {b["uid"] for b in bookings}
    conn       = get_conn()

    try:
        for b in bookings:
            row = conn.execute(
                "SELECT hash, status FROM bookings WHERE uid = ?", (b["uid"],)
            ).fetchone()

            if row is None:
                # New event — store all including BLOCKED
                conn.execute("""
                    INSERT INTO bookings
                      (uid, property_name, platform, summary, dtstart, dtend, status, hash, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b["uid"], b["property_name"], b["platform"], b["summary"],
                      b["dtstart"], b["dtend"], b["status"], b["hash"], now_iso, now_iso))
                conn.commit()

                if b["status"] not in ("CANCELLED", "BLOCKED"):
                    log.info("NEW: %s / %s / %s", b["property_name"], b["platform"], b["uid"])
                    send_telegram(msg_new(b))
                else:
                    log.info("STORED %s (no alert): %s / %s", b["status"], b["property_name"], b["uid"])

            else:
                old_hash, old_status = row
                conn.execute(
                    "UPDATE bookings SET last_seen=?, hash=?, status=? WHERE uid=?",
                    (now_iso, b["hash"], b["status"], b["uid"])
                )
                conn.commit()

                if old_status != "CANCELLED" and b["status"] == "CANCELLED":
                    log.info("CANCELLED: %s / %s / %s", b["property_name"], b["platform"], b["uid"])
                    send_telegram(msg_cancelled(b))

                elif old_hash != b["hash"] and b["status"] not in ("CANCELLED", "BLOCKED"):
                    log.info("MODIFIED: %s / %s / %s", b["property_name"], b["platform"], b["uid"])
                    send_telegram(msg_modified(b))

        # ── Detect disappeared bookings (platform removed event = cancellation) ──
        # Only check CONFIRMED bookings for this property+platform that vanished
        active_in_db = conn.execute("""
            SELECT uid, property_name, platform, summary, dtstart, dtend, status, hash
            FROM bookings
            WHERE property_name = ? AND platform = ?
              AND status NOT IN ('CANCELLED', 'BLOCKED')
              AND dtend >= ?
        """, (prop["name"], prop["platform"],
              datetime.now(TZ).date().isoformat())).fetchall()

        for row in active_in_db:
            uid = row[0]
            if uid not in seen_uids:
                # Booking vanished from feed — treat as cancellation
                b_ghost = {
                    "uid": row[0], "property_name": row[1], "platform": row[2],
                    "summary": row[3], "dtstart": row[4], "dtend": row[5],
                    "status": row[6], "hash": row[7],
                }
                conn.execute(
                    "UPDATE bookings SET status='CANCELLED', last_seen=? WHERE uid=?",
                    (now_iso, uid)
                )
                conn.commit()
                log.info("DISAPPEARED (cancellation): %s / %s / %s", prop["name"], prop["platform"], uid)
                send_telegram(msg_cancelled(b_ghost))

    finally:
        conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info("StayinPuri Alert Service starting — 5 feeds, silent polling")
    log.info("Properties: Asiyana (Airbnb, Agoda) | Tulsi Vihar (Airbnb, Agoda, Booking.com)")
    init_db()

    while True:
        log.info("── Poll cycle ──")
        for prop in PROPERTIES:
            sync_property(prop)
        log.info("── Done. Sleeping %d min ──", POLL_INTERVAL_MINUTES)
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
