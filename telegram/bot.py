#!/usr/bin/env python3
"""
StayinPuri Telegram AI Bot — Final Build
=========================================
Architecture: service-oriented, channel-agnostic brain
Services: booking_service (live), train_service (placeholder)
Channels: Telegram (this file — thin adapter)

Features:
- Every group message handled (no @mention needed)
- Language auto-detect: Odia script / Romanized Odia / English
- Instant wait message in user's language
- AI (OpenRouter) with conversation history per chat
- Smart: asks which apartment if unclear (tap buttons)
- Smart: needs_clarification → asks follow-up before answering
- Clickable follow-up buttons in user's language
- Offline booking → "coming soon" in user's language
- BLOCKED dates treated same as booked for availability
- Train service: placeholder, ready for future integration
- Commands: /start /today /week /month /help /train (placeholder)
"""

import os, json, sqlite3, logging, time, re, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TZ                 = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
DB_PATH            = os.getenv("DB_PATH", "./bookings.db")
MODEL              = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")
LOG_PATH           = os.getenv("LOG_PATH", "./stayinpuri.log")
TELEGRAM_API       = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ── Future service keys (placeholders) ────────────────────────────────────────
RAILWAY_API_KEY    = os.getenv("RAILWAY_API_KEY", "")   # TODO: add when ready


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SERVICE: LANGUAGE DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROMAN_ODIA_KEYWORDS = {
    "khali", "achi", "nahi", "aaji", "aji", "kebe", "kete", "din",
    "hela", "gala", "thiba", "aasibe", "jaibe", "bhai", "puchha",
    "jaan", "mane", "purna", "aasa", "jaa",
    "ki", "ku", "ra", "te", "se", "mo",
    # Additional Romanized Odia words
    "darkar", "thila", "karibe", "karibu", "karicha",
    "pain", "para", "pari", "kara", "kari", "karu", "karuchu",
    "aste", "sahajya", "bujhi", "paruni", "janibe",
    "ghara", "ghar",
}

def detect_lang(text: str) -> tuple[bool, bool]:
    """Returns (is_odia_script, is_roman_odia)"""
    is_odia = any("\u0b00" <= c <= "\u0b7f" for c in text)
    if is_odia:
        return True, False
    words = set(re.sub(r"[^a-zA-Z\s]", "", text.lower()).split())
    is_roman = bool(words & ROMAN_ODIA_KEYWORDS)
    return False, is_roman

def wait_msg(is_odia: bool, is_roman: bool) -> str:
    if is_odia:  return "ଦୟାକରି ଅପେକ୍ଷା କରନ୍ତୁ... 🔍"
    if is_roman: return "Wait karo, check karuchu... 🔍"
    return "Checking... 🔍"

def offline_msg(is_odia: bool, is_roman: bool) -> str:
    if is_odia:  return "ଅଫ୍‌ଲାଇନ୍ booking ଶୀଘ୍ର ଆସୁଛି! 🔜\nଏବେ Airbnb ରେ dates manually block କରନ୍ତୁ। 🙏"
    if is_roman: return "Offline booking feature jaldi aasiba! 🔜\nEbe Airbnb re dates manually block kara. 🙏"
    return "Offline booking feature coming soon! 🔜\nFor now, please block the dates in Airbnb manually. 🙏"

def which_apt_msg(is_odia: bool, is_roman: bool) -> str:
    if is_odia:  return "କେଉଁ apartment?"
    if is_roman: return "Kounsi apartment? (Asiyana ki Tulsi Vihar?)"
    return "Which apartment?"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SERVICE: BOOKING DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_conn():
    return sqlite3.connect(DB_PATH)

def fmt_d(d: str, with_day: bool = False) -> str:
    """2026-04-27 → 27 Apr  or  27 Apr (Mon)"""
    try:
        dt = datetime.fromisoformat(d)
        return dt.strftime("%d %b (%a)") if with_day else dt.strftime("%d %b")
    except Exception:
        return d

def nights_count(ci: str, co: str) -> int:
    try:
        return (datetime.fromisoformat(co) - datetime.fromisoformat(ci)).days
    except Exception:
        return 0

def get_property_status(prop_filter: str, is_odia: bool = False, is_roman: bool = False) -> str:
    """
    Rich formatted availability status for a specific property.
    Used when AI detects availability question — bypasses AI formatting.
    Shows: active bookings, owner blocks, free gaps — all formatted.
    """
    today    = datetime.now(TZ).date()
    look_end = today + timedelta(days=90)
    conn     = get_conn()

    confirmed = conn.execute("""
        SELECT platform, dtstart, dtend FROM bookings
        WHERE property_name LIKE ? AND status NOT IN ('CANCELLED','BLOCKED') AND dtend > ?
        ORDER BY dtstart
    """, (f"%{prop_filter}%", today.isoformat())).fetchall()

    blocked = conn.execute("""
        SELECT platform, dtstart, dtend FROM bookings
        WHERE property_name LIKE ? AND status = 'BLOCKED' AND dtend > ?
        ORDER BY dtstart
    """, (f"%{prop_filter}%", today.isoformat())).fetchall()
    conn.close()

    prop_name = "Asiyana Apartment" if "Asiyana" in prop_filter else "Tulsi Vihar Apartment"
    emoji     = "🏠" if "Asiyana" in prop_filter else "🏡"

    lines = [f"{emoji} <b>{prop_name}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]

    PLAT_EMOJI = {"Airbnb": "🔴", "Booking.com": "🅱️", "Agoda": "🌏"}

    # ── Active/upcoming confirmed bookings ────────────────────────────────────
    if confirmed:
        if is_odia:   lines.append("📋 <b>ନিশ୍ଚିତ booking:</b>")
        elif is_roman: lines.append("📋 <b>Confirmed bookings:</b>")
        else:          lines.append("📋 <b>Confirmed bookings:</b>")
        for plat, ci, co in confirmed:
            n = nights_count(ci, co)
            pe = PLAT_EMOJI.get(plat, "📦")
            lines.append(f"   🔴 {fmt_d(ci, True)} → {fmt_d(co, True)}  ({n}n · {pe} {plat})")
    else:
        if is_odia:    lines.append("✅ <b>କୌଣସି confirmed booking ନାହିଁ</b>")
        elif is_roman: lines.append("✅ <b>Kono confirmed booking nahi</b>")
        else:          lines.append("✅ <b>No confirmed bookings</b>")

    # ── Owner blocked dates ───────────────────────────────────────────────────
    visible_blocks = [
        (plat, ci, co) for plat, ci, co in blocked
        if datetime.fromisoformat(ci).date() <= look_end
    ]
    if visible_blocks:
        lines.append("\n🔒 <b>Owner blocked:</b>")
        for plat, ci, co in visible_blocks:
            n = nights_count(ci, co)
            lines.append(f"   ⛔ {fmt_d(ci, True)} → {fmt_d(co, True)}  ({n}n · {plat})")

    # ── Free gaps (within 90 days only) ──────────────────────────────────────
    all_busy = sorted(
        [(datetime.fromisoformat(ci).date(), datetime.fromisoformat(co).date())
         for _, ci, co in confirmed + blocked],
        key=lambda x: x[0]
    )

    free_lines = []
    prev = today
    for ci_d, co_d in all_busy:
        ci_d = min(ci_d, look_end)  # cap to 90 days
        if ci_d > prev:
            days = (ci_d - prev).days
            if days >= 1:
                free_lines.append(f"   ✅ {prev.strftime('%d %b')} → {ci_d.strftime('%d %b')} ({days}d free)")
        prev = max(prev, co_d)
        if prev >= look_end:
            break
    if prev < look_end:
        free_lines.append(f"   ✅ {prev.strftime('%d %b')} onwards 🟢")

    if free_lines:
        if is_odia:    lines.append("\n📅 <b>ଖାଲି dates (next 90 days):</b>")
        elif is_roman: lines.append("\n📅 <b>Khali dates (next 90 days):</b>")
        else:          lines.append("\n📅 <b>Free dates (next 90 days):</b>")
        lines.extend(free_lines)

    return "\n".join(lines)


def get_bookings_context() -> str:
    """Full DB context for LLM — confirmed bookings + owner blocks."""
    today = datetime.now(TZ).date().isoformat()
    conn  = get_conn()

    confirmed = conn.execute("""
        SELECT property_name, platform, dtstart, dtend, status
        FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED') AND dtend > ?
        ORDER BY dtstart
    """, (today,)).fetchall()

    blocked = conn.execute("""
        SELECT property_name, platform, dtstart, dtend
        FROM bookings
        WHERE status = 'BLOCKED' AND dtend >= ?
        ORDER BY property_name, dtstart
    """, (today,)).fetchall()

    month_start = datetime.now(TZ).date().replace(day=1).isoformat()
    past = conn.execute("""
        SELECT property_name, platform, dtstart, dtend
        FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED')
          AND dtstart >= ? AND dtstart < ?
        ORDER BY dtstart
    """, (month_start, today)).fetchall()
    conn.close()

    if not confirmed and not blocked:
        return "No upcoming bookings or blocks. Both properties fully open."

    lines = []
    if confirmed:
        lines.append("CONFIRMED BOOKINGS:")
        for r in confirmed:
            prop, plat, ci, co, _ = r
            n = nights_count(ci, co)
            lines.append(f"  {prop} | {plat} | {ci} → {co} | {n} nights")
    if blocked:
        lines.append("OWNER-BLOCKED DATES (guests CANNOT book — treat as unavailable):")
        for r in blocked:
            prop, plat, ci, co = r
            n = nights_count(ci, co)
            lines.append(f"  {prop} | {plat} | {ci} → {co} | {n} nights | BLOCKED")
    if past:
        lines.append("PAST BOOKINGS THIS MONTH (for stats):")
        for r in past:
            prop, plat, ci, co = r
            n = nights_count(ci, co)
            lines.append(f"  {prop} | {plat} | {ci} → {co} | {n} nights")

    return "\n".join(lines)


def get_today_summary() -> str:
    today = datetime.now(TZ).date().isoformat()
    conn  = get_conn()
    checkins  = conn.execute("""
        SELECT property_name, platform, dtstart, dtend FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED') AND dtstart = ?
    """, (today,)).fetchall()
    checkouts = conn.execute("""
        SELECT property_name, platform, dtstart, dtend FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED') AND dtend = ?
    """, (today,)).fetchall()
    staying   = conn.execute("""
        SELECT property_name, platform, dtstart, dtend FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED') AND dtstart < ? AND dtend > ?
    """, (today, today)).fetchall()
    conn.close()

    def row(r):
        prop, plat, ci, co = r
        n = nights_count(ci, co)
        e = "🏠" if "Asiyana" in prop else "🏡"
        return f"{e} <b>{prop}</b> · {plat} · {fmt_d(ci)}→{fmt_d(co)} ({n}n)"

    dt_str = datetime.now(TZ).strftime("%d %b %Y (%a)")
    parts  = [f"📅 <b>{dt_str}</b>\n"]
    if not checkins and not checkouts and not staying:
        parts.append("✅ Both properties free today!\nଆଜି ଘର ଖାଲି ଅଛି। 🟢")
    else:
        if checkins:
            parts.append("🔵 <b>Check-in today:</b>\n" + "\n".join(row(r) for r in checkins))
        if checkouts:
            parts.append("🔴 <b>Check-out today:</b>\n" + "\n".join(row(r) for r in checkouts))
        active = [r for r in staying if r not in checkins]
        if active:
            parts.append("🟡 <b>Currently staying:</b>\n" + "\n".join(row(r) for r in active))
    return "\n\n".join(parts)


def get_week_summary() -> str:
    today    = datetime.now(TZ).date()
    week_end = today + timedelta(days=7)
    conn     = get_conn()
    rows     = conn.execute("""
        SELECT property_name, platform, dtstart, dtend FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED')
          AND dtstart < ? AND dtend > ?
        ORDER BY dtstart
    """, (week_end.isoformat(), today.isoformat())).fetchall()
    conn.close()

    if not rows:
        return f"📅 <b>Next 7 days</b>\n\n🟢 No bookings. Both properties free.\nଆସନ୍ତା ୭ ଦିନ ଘର ଖାଲି। "

    lines = [f"📅 <b>Next 7 days</b> ({today.strftime('%d %b')} → {week_end.strftime('%d %b')})\n"]
    for prop, plat, ci, co in rows:
        n = nights_count(ci, co)
        e = "🏠" if "Asiyana" in prop else "🏡"
        lines.append(f"{e} <b>{prop}</b>  ·  {plat}\n   {fmt_d(ci, True)} → {fmt_d(co, True)} · {n}n")
    return "\n".join(lines)


def get_month_summary() -> str:
    today       = datetime.now(TZ).date()
    month_start = today.replace(day=1)
    month_end   = (month_start.replace(month=month_start.month % 12 + 1, day=1)
                   if month_start.month < 12
                   else month_start.replace(year=month_start.year + 1, month=1, day=1))
    conn = get_conn()
    rows = conn.execute("""
        SELECT property_name, platform, dtstart, dtend FROM bookings
        WHERE status NOT IN ('CANCELLED','BLOCKED')
          AND dtstart < ? AND dtend > ?
        ORDER BY dtstart
    """, (month_end.isoformat(), month_start.isoformat())).fetchall()
    conn.close()

    month_name = today.strftime("%B %Y")
    if not rows:
        return f"📊 <b>{month_name}</b>\n\n🟢 No bookings this month."

    total = asi = tulsi = 0
    plats: dict = {}
    lines = [f"📊 <b>{month_name}</b>\n"]
    for prop, plat, ci, co in rows:
        n = nights_count(ci, co)
        total += n
        if "Asiyana" in prop: asi += n
        else: tulsi += n
        plats[plat] = plats.get(plat, 0) + n
        e = "🏠" if "Asiyana" in prop else "🏡"
        lines.append(f"{e} {prop} · {plat} · {fmt_d(ci)}→{fmt_d(co)} ({n}n)")

    top = max(plats, key=plats.get) if plats else "-"
    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🌙 Total: <b>{total} nights</b>",
        f"🏠 Asiyana: <b>{asi}n</b>  🏡 Tulsi: <b>{tulsi}n</b>",
        f"🏆 Top platform: <b>{top}</b>",
    ]
    return "\n".join(lines)


def get_free_slots(prop_filter: str = None) -> str:
    today    = datetime.now(TZ).date()
    look_end = today + timedelta(days=60)
    conn     = get_conn()
    rows     = conn.execute("""
        SELECT property_name, dtstart, dtend FROM bookings
        WHERE status NOT IN ('CANCELLED') AND dtend > ?
        ORDER BY property_name, dtstart
    """, (today.isoformat(),)).fetchall()
    conn.close()

    props: dict = {}
    for prop, ci, co in rows:
        if prop_filter and prop_filter.lower() not in prop.lower():
            continue
        props.setdefault(prop, []).append((ci, co))

    if not props:
        return "🟢 No upcoming bookings — everything is free!"

    lines = ["🔍 <b>Free slots — next 60 days</b>\n"]
    for prop, bookings in props.items():
        e = "🏠" if "Asiyana" in prop else "🏡"
        lines.append(f"{e} <b>{prop}</b>")
        prev = today
        found = False
        for ci, co in sorted(bookings):
            ci_d = datetime.fromisoformat(ci).date()
            co_d = datetime.fromisoformat(co).date()
            if ci_d > prev:
                days = (ci_d - prev).days
                lines.append(f"   ✅ {prev.strftime('%d %b')} → {ci_d.strftime('%d %b')} ({days} days free)")
                found = True
            prev = max(prev, co_d)
        if prev < look_end:
            lines.append(f"   ✅ From {prev.strftime('%d %b')} onwards 🟢")
            found = True
        if not found:
            lines.append("   🔴 Fully booked / blocked (next 60 days)")
    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SERVICE: TRAIN (PLACEHOLDER — ready for future integration)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TODO: Replace placeholder functions with real API calls when key is ready
# Recommended API: indianrailapi.com (non-commercial plan ~₹300-500/month)
# Env var needed: RAILWAY_API_KEY

def train_pnr_status(pnr: str) -> str:
    """TODO: Call railway API to get PNR status."""
    return (
        "🚆 <b>Train Service — Coming Soon!</b>\n\n"
        "Railway PNR check will be available shortly.\n"
        "ଟ୍ରେନ୍ service ଶୀଘ୍ର ଆସୁଛି! 🔜"
    )

def train_live_status(train_no: str) -> str:
    """TODO: Call railway API to get live running status."""
    return (
        "🚆 <b>Train Service — Coming Soon!</b>\n\n"
        "Live train status will be available shortly.\n"
        "ଟ୍ରେନ୍ status ଶୀଘ୍ର ଆସୁଛି! 🔜"
    )

def train_between_stations(from_stn: str, to_stn: str, date: str = None) -> str:
    """TODO: Call railway API to get trains between stations."""
    return (
        "🚆 <b>Train Service — Coming Soon!</b>\n\n"
        f"Trains from {from_stn} to {to_stn} — available shortly.\n"
        "ଟ୍ରେନ୍ service ଶୀଘ୍ର ଆସୁଛି! 🔜"
    )

def train_seat_availability(train_no: str, from_stn: str, to_stn: str,
                             date: str, travel_class: str) -> str:
    """TODO: Call railway API to check seat availability."""
    return (
        "🚆 <b>Train Service — Coming Soon!</b>\n\n"
        "Seat availability check will be available shortly.\n"
        "ଟ୍ରେନ୍ service ଶୀଘ୍ର ଆସୁଛି! 🔜"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BRAIN: SYSTEM PROMPT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM_PROMPT = """You are StayinPuri Bot — a smart, concise assistant for a family holiday rental in Puri, Odisha, India.

== PROPERTIES ==
1. 🏠 Asiyana Apartment — listed on Airbnb and Agoda
2. 🏡 Tulsi Vihar Apartment — listed on Airbnb, Agoda and Booking.com

== PEOPLE ==
- Pritish — owner
- Sas — his wife
- Gaura, Manoj, Radheshyam — trusted on-ground helpers. Never call them "caretaker" or "staff".

== LANGUAGE DETECTION — CRITICAL, NEVER GET THIS WRONG ==
You MUST detect the language TYPE from the user's message and reply in the EXACT same type.

TYPE 1 — ODIA SCRIPT: message contains Odia Unicode characters (ଅ ଆ ଇ ଉ ଏ ଓ etc.)
→ Reply 100% in Odia script. Never switch to English.

TYPE 2 — ROMANIZED ODIA: Odia words written in English letters. This is NOT English.
Detection signals: khali, achi, nahi, aaji, kebe, kete, din, hela, gala, thiba, aasibe,
bhai, puchha, re, ki, ku, ra, te, se, mo, purna, booking, guest
Common mistakes: "Asiyana/Asiana/Ajay Hasina" = Asiyana Apartment
→ Reply in simple Romanized Odia (Odia words written in English letters)

TYPE 3 — ENGLISH: proper English
→ Reply in English

TYPE 4 — MIXED: blend of above → match exact same blend

== GREETING RULE ==
First message or "hi/hello/namaskara" → warm greeting in detected language.
Follow-up messages in SAME conversation → skip greeting, answer directly.

== BOOKING DATA ==
{booking_context}

TODAY: {today}

== INTELLIGENCE RULES ==
1. ONE PROPERTY ASKED → answer that property ONLY. Never mention the other.

2. PROPERTY UNCLEAR → set needs_property=true. NEVER guess. This triggers apartment selection buttons.
   These words do NOT specify a property — always set needs_property=true:
   - "ଘର" (ghara = house, generic)
   - "apartment", "flat", "room", "property" (generic)
   - "khali achi", "kebe khali", "guest achi" — WITHOUT naming Asiyana or Tulsi
   - Any availability/booking question with no property name
   Only skip needs_property=true when message explicitly contains:
   "Asiyana" OR "Asiana" OR "Ajay Hasina" OR "Tulsi" OR "Tulasi"

3. INTENT UNCLEAR → do NOT guess. Set needs_clarification=true.
4. BLOCKED dates = owner manually blocked. No guests can book. Count as unavailable.
5. FREE period = no confirmed bookings AND no blocks.
6. Never repeat the user's question back.
7. Never say "Would you like me to..." — give the answer directly.
8. Max 3 lines in reply. Short. Clear. Mobile-friendly.
9. OFFLINE BOOKING mentioned → set offline_booking=true only.
10. TRAIN/RAILWAY mentioned → set train_query=true only.

== OUTPUT FORMAT — STRICT JSON ONLY ==
Respond with ONLY this JSON. No text before or after. No markdown fences.
{{
  "lang": "odia_script|romanized_odia|english",
  "reply": "your answer in detected language",
  "followups": ["short relevant question 1", "short relevant question 2"],
  "needs_property": false,
  "needs_clarification": false,
  "offline_booking": false,
  "train_query": false
}}

== FOLLOWUP QUESTIONS — OWNER/CARETAKER CONTEXT ==
This is a PRIVATE group for the property owner (Pritish), his wife, and on-ground helpers (Gaura, Manoj, Radheshyam).
They are NOT guests. They MANAGE the property. Followups must reflect this.

GOOD followup examples (management perspective):
- After availability answer: "Agle booking kebe?" / "ପରବର୍ତ୍ତୀ booking କେବେ?" / "Next booking when?"
- After booking info: "Guest kete jon aasibe?" / "ଗ୍ରୁପ size କେତେ?" / "How many guests?"
- After free dates: "Kichi block karibaku darkar?" / "ଦିନ block କରିବା?" / "Need to block any dates?"
- After check-in info: "Room ready achi ki?" / "ଘର ready ଅଛି କି?" / "Is room prepared?"
- After check-out info: "Cleaning hela ki?" / "ପରିଷ୍କାର ହେଲା କି?" / "Cleaning done?"
- After platform info: "Other platform re bi achi ki?" / "ଅନ୍ୟ platform ରେ?" / "Check other platform?"
- After monthly stats: "Best performing month?" / "ଏ ବର୍ଷ kete nights?" / "This year total?"

BAD followups (guest-facing — NEVER use these):
- "What dates are you interested in booking?" ❌
- "Would you like to make a reservation?" ❌
- "How many guests will be staying?" ❌
- "Kete guest aasibe?" ❌ (bot cannot take bookings)
- "Kete din thiba?" ❌ (bot cannot take bookings)
- "Which room type do you prefer?" ❌
- Anything that sounds like you are taking a new booking ❌

THIS BOT CANNOT TAKE BOOKINGS. Never suggest booking-related actions.
Only suggest management/operational follow-up questions.

STRICTLY BANNED followup patterns (never generate these):
- Anything with "kete jon" (how many guests) ❌
- Anything with "aasibe" in context of new guests arriving ❌
- Anything about check-in dates for new guests ❌
- Anything about room preferences ❌

GOOD followup patterns (always from management perspective):
- Next booking date: "Agle booking kebe?" / "ପରବର୍ତ୍ତୀ booking?" / "Next booking?"
- Cleaning status: "Cleaning hela ki?" / "ପରିଷ୍କାର ହେଲା?" / "Room cleaned?"
- Block dates: "Kichi block karibaku?" / "Block darkar?" / "Need to block?"
- Other property: Only if user asked about both
- Platform check: "Other platform re bi check?" / "Agoda re bi dekha?"

Rules:
- Always from MANAGEMENT/OWNER perspective
- Same language as reply (Odia script / Romanized / English)
- Short — max 5 words per button
- Practical — something Gaura or Pritish would actually want to know next
- NEVER mention the other property unless asked about both
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BRAIN: CONVERSATION HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_histories: dict = {}

def get_history(chat_id) -> list:
    return _histories.get(str(chat_id), [])

def add_history(chat_id, role: str, content: str):
    key = str(chat_id)
    _histories.setdefault(key, []).append({"role": role, "content": content})
    # Keep last 6 messages (3 turns)
    if len(_histories[key]) > 6:
        _histories[key] = _histories[key][-6:]

def clear_history(chat_id):
    _histories.pop(str(chat_id), None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BRAIN: LLM CLIENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _extract_json(raw: str) -> str:
    """
    Robustly extract JSON object from model output.
    Handles: markdown fences, leading text, trailing text,
    missing outer braces, extra whitespace.
    """
    raw = raw.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
        raw = "\n".join(lines).strip()

    # If it starts with { — try as-is first
    if raw.startswith("{"):
        return raw

    # Find first { and last } — extract JSON object
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]

    # Model returned fields without braces — wrap them
    if '"lang"' in raw or '"reply"' in raw:
        return "{" + raw.strip().strip(",") + "}"

    return raw

FALLBACK = {
    "lang": "english", "reply": "ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ 🙏",
    "followups": [], "needs_property": False,
    "needs_clarification": False, "offline_booking": False, "train_query": False,
}

def ask_ai(chat_id, user_message: str) -> dict:
    """Core AI call. Returns structured dict with reply + flags."""
    system = SYSTEM_PROMPT.format(
        booking_context=get_bookings_context(),
        today=datetime.now(TZ).strftime("%d %b %Y (%A)"),
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(get_history(chat_id))
    messages.append({"role": "user", "content": user_message})

    raw = ""
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://stayinpuri.com",
                "X-Title": "StayinPuri Bot",
            },
            json={
                "model":           MODEL,
                "messages":        messages,
                "max_tokens":      400,
                "temperature":     0.15,
                "response_format": {"type": "json_object"},
            },
            timeout=25,
        )
        resp.raise_for_status()
        raw    = resp.json()["choices"][0]["message"]["content"].strip()
        raw    = _extract_json(raw)
        parsed = json.loads(raw)

        reply = parsed.get("reply", "").strip()
        add_history(chat_id, "user", user_message)
        add_history(chat_id, "assistant", reply)
        return parsed

    except json.JSONDecodeError as e:
        log.error("JSON parse fail: %s | raw was: %s", e, raw[:300])
        fallback = dict(FALLBACK)
        fallback["reply"] = raw if len(raw) > 5 else "ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ 🙏"
        return fallback
    except Exception as e:
        log.error("OpenRouter error: %s | raw: %s", e, raw[:200] if raw else "empty")
        return dict(FALLBACK)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHANNEL: TELEGRAM — KEYBOARDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def kb_today_after():
    return {"inline_keyboard": [[
        {"text": "📅 This week",    "callback_data": "week"},
        {"text": "📊 This month",   "callback_data": "month"},
    ], [
        {"text": "🏠 Asiyana free?", "callback_data": "free_asiyana"},
        {"text": "🏡 Tulsi free?",   "callback_data": "free_tulsi"},
    ]]}

def kb_week_after():
    return {"inline_keyboard": [[
        {"text": "📅 Today",       "callback_data": "today"},
        {"text": "📊 Month",       "callback_data": "month"},
        {"text": "🔍 Free slots",  "callback_data": "free_both"},
    ]]}

def kb_month_after():
    return {"inline_keyboard": [[
        {"text": "📅 Today",       "callback_data": "today"},
        {"text": "📅 This week",   "callback_data": "week"},
    ]]}

def kb_for_lang(is_odia: bool, is_roman: bool) -> dict:
    """Quick action buttons in user's detected language."""
    if is_odia:
        return {"inline_keyboard": [[
            {"text": "📅 ଆଜି",      "callback_data": "today"},
            {"text": "📅 ଏ ସପ୍ତାହ", "callback_data": "week"},
            {"text": "📊 ଏ ମାସ",    "callback_data": "month"},
        ]]}
    if is_roman:
        return {"inline_keyboard": [[
            {"text": "📅 Aaji",     "callback_data": "today"},
            {"text": "📅 E saptah", "callback_data": "week"},
            {"text": "📊 E masa",   "callback_data": "month"},
        ]]}
    return {"inline_keyboard": [[
        {"text": "📅 Today",    "callback_data": "today"},
        {"text": "📅 This week","callback_data": "week"},
        {"text": "📊 Month",    "callback_data": "month"},
    ]]}

# ── Store pending questions in memory, keyed by short ID ─────────────────────
_pending_questions: dict = {}
_pending_counter = 0

def _store_pending(question: str) -> str:
    """Store question, return short numeric key safe for callback_data."""
    global _pending_counter
    _pending_counter += 1
    key = str(_pending_counter % 9999)  # keep short
    _pending_questions[key] = question
    return key

def _get_pending(key: str) -> str:
    return _pending_questions.get(key, "")


def kb_apt(is_odia: bool, is_roman: bool, orig_q: str) -> dict:
    """Apartment selection buttons. Uses short key to avoid Telegram 64-byte limit."""
    key = _store_pending(orig_q)
    if is_odia:
        return {"inline_keyboard": [[
            {"text": "🏠 ଆସିଆନା",      "callback_data": f"prop_asiyana_{key}"},
            {"text": "🏡 ତୁଲସୀ ବିହାର", "callback_data": f"prop_tulsi_{key}"},
        ]]}
    if is_roman:
        return {"inline_keyboard": [[
            {"text": "🏠 Asiyana",     "callback_data": f"prop_asiyana_{key}"},
            {"text": "🏡 Tulsi Vihar", "callback_data": f"prop_tulsi_{key}"},
        ]]}
    return {"inline_keyboard": [[
        {"text": "🏠 Asiyana",     "callback_data": f"prop_asiyana_{key}"},
        {"text": "🏡 Tulsi Vihar", "callback_data": f"prop_tulsi_{key}"},
    ]]}

# ── Banned followup patterns — guest-facing, not management ──────────────────
BANNED_FOLLOWUP_KW = [
    "kete jon", "how many guest", "kitne log", "guest aasibe",
    "book karibe", "booking karibe", "reserve", "reservation",
    "check in karibe", "checkin karibe", "room type", "room ready",
    "kete din thiba", "how long stay", "kete din",
]

def _is_valid_followup(fq: str) -> bool:
    """Filter out guest-facing followup suggestions."""
    fl = fq.lower()
    return not any(kw in fl for kw in BANNED_FOLLOWUP_KW)

def kb_from_followups(followups: list, is_odia: bool = False, is_roman: bool = False) -> dict | None:
    """Build inline buttons from AI followup questions. Filters bad suggestions."""
    if not followups:
        return None
    valid = [fq for fq in followups[:4] if _is_valid_followup(fq)][:2]
    if not valid:
        return None
    buttons = []
    for fq in valid:
        key = _store_pending(fq)
        buttons.append({"text": fq[:40], "callback_data": f"fq_{key}"})
    return {"inline_keyboard": [buttons]}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHANNEL: TELEGRAM — API CALLS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def send_msg(chat_id, text: str, markup=None, reply_to=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if markup:  payload["reply_markup"] = json.dumps(markup)
    if reply_to: payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error("send_msg failed: %s", e)

def answer_cb(cb_id: str):
    try:
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                      json={"callback_query_id": cb_id}, timeout=5)
    except Exception:
        pass

def get_updates(offset: int) -> list:
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates",
                         params={"offset": offset, "timeout": 30}, timeout=35)
        r.raise_for_status()
        return r.json().get("result", [])
    except Exception as e:
        log.error("getUpdates failed: %s", e)
        return []

def set_commands():
    cmds = [
        {"command": "start",  "description": "Welcome / restart"},
        {"command": "today",  "description": "Today's bookings"},
        {"command": "week",   "description": "This week's bookings"},
        {"command": "month",  "description": "This month summary"},
        {"command": "train",  "description": "Train info (coming soon)"},
        {"command": "help",   "description": "Show all commands"},
    ]
    try:
        requests.post(f"{TELEGRAM_API}/setMyCommands",
                      json={"commands": cmds}, timeout=10)
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHANNEL: TELEGRAM — MESSAGE HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def handle_message(msg: dict):
    # ── Guard: skip bots and empty messages ──────────────────────────────────
    if msg.get("from", {}).get("is_bot"):
        return
    text      = msg.get("text", "").strip()
    if not text:
        return

    chat_id   = msg["chat"]["id"]
    msg_id    = msg["message_id"]
    from_name = msg.get("from", {}).get("first_name", "")

    log.info("MSG [%s] %s: %s", chat_id, from_name, text[:80])

    # ── Guard: skip @mentions to other users ─────────────────────────────────
    for ent in msg.get("entities", []):
        if ent.get("type") == "mention":
            return

    # ── Slash commands ────────────────────────────────────────────────────────
    cmd = text.split()[0].lower() if text.startswith("/") else ""

    if cmd == "/start":
        clear_history(chat_id)
        send_msg(chat_id,
            f"👋 ନମସ୍କାର <b>{from_name}</b>! 🏖️\n\n"
            f"StayinPuri Bot — Ask me anything about your properties!\n"
            f"Odia, Romanized Odia, or English — I understand all.\n\n"
            f"<b>Commands:</b> /today · /week · /month · /train · /help",
            kb_for_lang(False, False), msg_id)
        return

    if cmd == "/today":
        send_msg(chat_id, get_today_summary(), kb_today_after(), msg_id)
        return

    if cmd == "/week":
        send_msg(chat_id, get_week_summary(), kb_week_after(), msg_id)
        return

    if cmd == "/month":
        send_msg(chat_id, get_month_summary(), kb_month_after(), msg_id)
        return

    if cmd == "/train":
        send_msg(chat_id,
            "🚆 <b>Train Service — Coming Soon!</b>\n\n"
            "PNR check, live status, seat availability, trains between stations.\n"
            "ଟ୍ରେନ୍ service ଶୀଘ୍ର ଆସୁଛି! 🔜",
            reply_to=msg_id)
        return

    if cmd == "/help":
        send_msg(chat_id,
            "🤖 <b>StayinPuri Bot</b>\n\n"
            "<b>Commands:</b>\n"
            "/today — ଆଜି status\n"
            "/week  — ଏ ସପ୍ତାହ bookings\n"
            "/month — ଏ ମାସ summary\n"
            "/train — Train info (coming soon)\n\n"
            "<b>Ask freely in Odia / Romanized / English:</b>\n"
            "• ଆଜି Asiyana ରେ guest ଅଛି?\n"
            "• Tulsi Vihar kebe khali achi?\n"
            "• When is Asiyana free next month?",
            reply_to=msg_id)
        return

    # ── Free-text → detect language → wait → AI ───────────────────────────────
    is_odia, is_roman = detect_lang(text)

    # ── Client-side offline booking check — BEFORE property pre-check ──────────
    OFFLINE_KW = {"offline", "direct booking", "direct", "walk-in", "walkin"}
    TRAIN_KW   = {"train", "pnr", "railway", "irctc", "ଟ୍ରେନ", "ରেল"}
    text_lower = text.lower()

    if any(k in text_lower for k in OFFLINE_KW):
        send_msg(chat_id, offline_msg(is_odia, is_roman), reply_to=msg_id)
        return

    if any(k in text_lower for k in TRAIN_KW):
        send_msg(chat_id,
            "🚆 <b>Train Service — Coming Soon!</b>\n\nPNR check, live status, seat availability — all coming shortly. 🔜",
            reply_to=msg_id)
        return

    # ── Client-side property pre-check (faster than waiting for AI) ──────────
    # If message is about availability/booking but doesn't name a property → ask immediately
    PROPERTY_NAMES   = {"asiyana", "asiana", "ajay hasina", "tulsi", "tulasi"}
    AVAILABILITY_KW  = {"khali", "free", "available", "booking", "guest", "achi",
                        "ଘର", "ଖାଲି", "ଅଛି", "ବୁକିଂ"}
    mentions_property    = any(p in text_lower for p in PROPERTY_NAMES)
    mentions_availability = any(k in text_lower for k in AVAILABILITY_KW)

    if mentions_availability and not mentions_property:
        send_msg(chat_id,
                 which_apt_msg(is_odia, is_roman),
                 kb_apt(is_odia, is_roman, text),
                 msg_id)
        return

    # Instant wait message in user's language
    send_msg(chat_id, wait_msg(is_odia, is_roman), reply_to=msg_id)

    # ── Detect property name in text ─────────────────────────────────────────
    prop_in_text = None
    tl = text.lower()
    if any(p in tl for p in ["asiyana", "asiana", "ajay hasina"]):
        prop_in_text = "Asiyana"
    elif any(p in tl for p in ["tulsi", "tulasi"]):
        prop_in_text = "Tulsi"

    # ── Availability question for known property → Python formatter ──────────
    # Triggers when: availability keyword found OR message is just property name + "re/?" 
    AVAIL_KW = {
        "khali", "free", "available", "booking", "achi", "status",
        "slot", "open", "ଖାଲି", "ଅଛି", "ବୁକିଂ", "kana", "kemiti",
        "kana achi", "ki achi", "re ?", "re?", "?",
    }
    is_avail_q = any(k in tl for k in AVAIL_KW)

    # Also trigger if message is just property name (with/without "re ?")
    # e.g. "Tulsi Vihar re ?" or just "Asiyana ?"
    stripped = tl.replace("asiyana","").replace("asiana","").replace("ajay hasina","")                  .replace("tulsi vihar","").replace("tulsi","").replace("tulasi","")                  .strip(" re?.")
    if prop_in_text and len(stripped) <= 5:
        is_avail_q = True  # short message after removing property name = availability question

    if is_avail_q and prop_in_text:
        reply  = get_property_status(prop_in_text, is_odia, is_roman)
        markup = kb_for_lang(is_odia, is_roman)
        send_msg(chat_id, reply, markup, msg_id)
        return

    # Call AI brain
    result       = ask_ai(chat_id, text)
    reply        = result.get("reply", "").strip()
    followups    = result.get("followups", [])
    needs_prop   = result.get("needs_property", False)
    needs_clari  = result.get("needs_clarification", False)
    is_offline   = result.get("offline_booking", False)
    is_train     = result.get("train_query", False)

    # ── Offline booking ───────────────────────────────────────────────────────
    if is_offline:
        send_msg(chat_id, offline_msg(is_odia, is_roman), reply_to=msg_id)
        return

    # ── Train query ───────────────────────────────────────────────────────────
    if is_train:
        send_msg(chat_id,
            "🚆 <b>Train Service — Coming Soon!</b>\n\n"
            "PNR check, live status, seat availability — all coming shortly.\n"
            "ଟ୍ରେନ୍ service ଶୀଘ୍ର ଆସୁଛି! 🔜",
            reply_to=msg_id)
        return

    # ── Ambiguous property → ask which one ───────────────────────────────────
    if needs_prop:
        send_msg(chat_id,
                 which_apt_msg(is_odia, is_roman),
                 kb_apt(is_odia, is_roman, text),
                 msg_id)
        return

    # ── Needs clarification → show AI's clarifying question with followup btns ─
    if needs_clari:
        markup = kb_from_followups(followups, is_odia, is_roman) or kb_for_lang(is_odia, is_roman)
        send_msg(chat_id, reply, markup, msg_id)
        return

    # ── Normal reply with followup buttons ───────────────────────────────────
    markup = kb_from_followups(followups, is_odia, is_roman) or kb_for_lang(is_odia, is_roman)
    send_msg(chat_id, reply, markup, msg_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHANNEL: TELEGRAM — CALLBACK HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _ai_reply_with_buttons(chat_id, question: str, label: str = ""):
    """Helper: show selected label → wait → call AI → send reply with buttons."""
    # Show what was selected so group knows which button was tapped
    if label:
        send_msg(chat_id, f"▶️ <b>{label}</b>")

    # ── Detect language from question ─────────────────────────────────────────
    is_odia, is_roman = detect_lang(question)

    # ── If question is about availability for a known property → use Python formatter
    # This gives clean formatted output — no AI date formatting issues
    q_lower = question.lower()
    is_avail_q = any(k in q_lower for k in [
        "khali", "free", "available", "availability", "booking", "achi",
        "status", "slot", "open", "ଖାଲି", "ଅଛି", "ବୁକିଂ", "status"
    ])
    prop_in_q = None
    if "asiyana" in q_lower or "asiana" in q_lower or "ajay hasina" in q_lower:
        prop_in_q = "Asiyana"
    elif "tulsi" in q_lower or "tulasi" in q_lower:
        prop_in_q = "Tulsi"

    if is_avail_q and prop_in_q:
        reply  = get_property_status(prop_in_q, is_odia, is_roman)
        markup = kb_for_lang(is_odia, is_roman)
        send_msg(chat_id, reply, markup)
        return

    # ── Otherwise → AI ────────────────────────────────────────────────────────
    send_msg(chat_id, wait_msg(is_odia, is_roman))
    result    = ask_ai(chat_id, question)
    reply     = result.get("reply", "")
    followups = result.get("followups", [])
    is_odia   = result.get("lang") == "odia_script"
    is_roman  = result.get("lang") == "romanized_odia"
    markup    = kb_from_followups(followups, is_odia, is_roman) or kb_for_lang(is_odia, is_roman)
    send_msg(chat_id, reply, markup)


def handle_callback(cb: dict):
    chat_id    = cb["message"]["chat"]["id"]
    data       = cb.get("data", "")
    cb_id      = cb["id"]
    from_name  = cb.get("from", {}).get("first_name", "")
    answer_cb(cb_id)

    # ── Static command callbacks — show label + result ────────────────────────
    if data == "today":
        send_msg(chat_id, f"▶️ <b>{from_name}: Today's status</b>")
        send_msg(chat_id, get_today_summary(), kb_today_after())
    elif data == "week":
        send_msg(chat_id, f"▶️ <b>{from_name}: This week</b>")
        send_msg(chat_id, get_week_summary(), kb_week_after())
    elif data == "month":
        send_msg(chat_id, f"▶️ <b>{from_name}: This month</b>")
        send_msg(chat_id, get_month_summary(), kb_month_after())
    elif data == "free_asiyana":
        send_msg(chat_id, f"▶️ <b>{from_name}: Asiyana free slots</b>")
        send_msg(chat_id, get_free_slots("Asiyana"), kb_for_lang(False, False))
    elif data == "free_tulsi":
        send_msg(chat_id, f"▶️ <b>{from_name}: Tulsi Vihar free slots</b>")
        send_msg(chat_id, get_free_slots("Tulsi"), kb_for_lang(False, False))
    elif data == "free_both":
        send_msg(chat_id, f"▶️ <b>{from_name}: Free slots — both</b>")
        send_msg(chat_id, get_free_slots(), kb_for_lang(False, False))

    # ── Property selection ────────────────────────────────────────────────────
    elif data.startswith("prop_"):
        parts     = data.split("_", 2)
        prop_key  = parts[1] if len(parts) > 1 else ""
        pend_key  = parts[2] if len(parts) > 2 else ""
        orig_q    = _get_pending(pend_key)
        prop_name = "Asiyana" if prop_key == "asiyana" else "Tulsi Vihar"
        question  = f"{prop_name} re {orig_q}" if orig_q else prop_name
        label     = f"{from_name}: {prop_name}"
        _ai_reply_with_buttons(chat_id, question, label)

    # ── AI followup button ────────────────────────────────────────────────────
    elif data.startswith("fq_"):
        parts    = data.split("_", 1)
        pend_key = parts[1] if len(parts) > 1 else ""
        question = _get_pending(pend_key)
        if question:
            label = f"{from_name}: {question[:40]}"
            _ai_reply_with_buttons(chat_id, question, label)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    log.info("StayinPuri Bot starting — final build")
    set_commands()
    now = datetime.now(TZ).strftime("%d %b %Y, %I:%M %p")
    send_msg(TELEGRAM_CHAT_ID,
        f"🤖 <b>StayinPuri Bot online!</b>\n"
        f"ମୁଁ ପ୍ରସ୍ତୁତ 🙏  Ask in Odia or English.\n"
        f"⏰ {now} IST")

    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                if "message" in update:
                    handle_message(update["message"])
                elif "callback_query" in update:
                    handle_callback(update["callback_query"])
            except Exception as e:
                log.error("Update error: %s", e, exc_info=True)
        if not updates:
            time.sleep(1)


if __name__ == "__main__":
    main()
