import argparse
import csv
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
import json
import datetime as dt

import requests

API_BASE = "https://data.europarl.europa.eu/api/v2"
DATA_BASE = "https://data.europarl.europa.eu"

LANG_MAP = {
    "ENG": "en",
    "FRA": "fr",
    "DEU": "de",
    "SPA": "es",
    "ITA": "it",
    "NLD": "nl",
    "POR": "pt",
    "POL": "pl",
    "ELL": "el",
    "DAN": "da",
    "SWE": "sv",
    "FIN": "fi",
}


def find_doc_id(obj):
    """
    Recursively find a CRE speech document ID like:
    eli/dl/doc/CRE-9-2024-01-15-OTH-10120000
    """
    if isinstance(obj, str):
        m = re.search(r"(?:https://data\.europarl\.europa\.eu/)?eli/dl/doc/(CRE-[^/\s'\"]+)", obj)
        if m:
            return m.group(1)

    elif isinstance(obj, dict):
        for value in obj.values():
            found = find_doc_id(value)
            if found:
                return found

    elif isinstance(obj, list):
        for value in obj:
            found = find_doc_id(value)
            if found:
                return found

    return None


def find_original_language(obj):
    """
    Recursively find original language code like ENG, FRA, DEU.
    """
    text = str(obj)
    m = re.search(r"/language/([A-Z]{3})", text)
    if m:
        return LANG_MAP.get(m.group(1), m.group(1).lower())
    return None




def get_label(item):
    label = item.get("activity_label")
    if isinstance(label, dict):
        return label.get("en") or next(iter(label.values()), "")
    return label or ""


def extract_items(payload):
    data = payload.get("data", payload)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "@graph" in data:
        return data["@graph"]
    if isinstance(data, dict):
        return [data]
    return []


def fetch_speech_metadata(date, limit):
    all_items = []
    offset = 0

    while True:
        params = {
            "format": "application/ld+json",
            "json-layout": "framed",
            "activity-type": "PLENARY_DEBATE_SPEECH",
            "sitting-date": date,
            "sitting-date-end": date,
            "limit": limit,
            "offset": offset,
            "sort-by": "sitting-date:asc",
            "include-output": "xml_fragment",
            "language": "en",
        }

        r = requests.get(f"{API_BASE}/speeches", params=params, timeout=30)

        if r.status_code == 204 or not r.text.strip():
            break

        r.raise_for_status()

        try:
            items = extract_items(r.json())
        except requests.exceptions.JSONDecodeError:
            if offset == 0:
                raise
            break

        if not items:
            break

        all_items.extend(items)

        print(f"  fetched {len(items)} rows at offset {offset}")

        # If fewer than limit returned, this was the last page.
        if len(items) < limit:
            break

        offset += limit
        time.sleep(0.2)

    return all_items

def find_embedded_text(obj):
    """
    Recursively search the API response for embedded transcript XML/text.
    """
    if isinstance(obj, str):
        if "<" in obj and ">" in obj:
            return strip_markup(obj)
        return None

    if isinstance(obj, dict):
        # likely places where included transcript output may appear
        for key in ["output", "text", "value", "@value"]:
            if key in obj:
                found = find_embedded_text(obj[key])
                if found:
                    return found

        for value in obj.values():
            found = find_embedded_text(value)
            if found:
                return found

    if isinstance(obj, list):
        for value in obj:
            found = find_embedded_text(value)
            if found:
                return found

    return None

def strip_markup(raw):
    """
    Convert XML/XHTML-ish document to readable text.
    """
    raw = raw.strip()

    # Try XML parsing first.
    try:
        root = ET.fromstring(raw)
        text = " ".join(t.strip() for t in root.itertext() if t.strip())
        return re.sub(r"\s+", " ", unescape(text)).strip()
    except ET.ParseError:
        pass

    # Fallback: crude tag stripping.
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", unescape(text))
    return text.strip()

def fetch_speech_text(doc_id, lang):
    urls = [
        f"{DATA_BASE}/eli/dl/doc/{doc_id}/{lang}/xml",
        f"{DATA_BASE}/eli/dl/doc/{doc_id}/{lang}/xhtml",
    ]

    for url in urls:
        r = requests.get(url, timeout=30, headers={
            "User-Agent": "europarl-speech-research/0.1"
        })

        if r.status_code == 404:
            continue

        r.raise_for_status()
        text = strip_markup(r.text)

        if text:
            return text, url

    return "", ""


def get_speaker_id(item):
    participation = item.get("had_participation")

    if isinstance(participation, dict):
        people = participation.get("had_participant_person", [])
        if people:
            return people[0].split("/")[-1]  # person/118859 -> 118859

    return None


def date_range(start_date, end_date):
    current = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)

    while current <= end:
        yield current.isoformat()
        current += dt.timedelta(days=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default="2026-01-01")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", default="europarl_speeches_with_text.csv")
    args = parser.parse_args()

    # If --date is provided, just run one day.
    if args.date:
        dates = [args.date]
    else:
        dates = list(date_range(args.start_date, args.end_date))

    all_rows = []

    for date in dates:
        print(f"\nFetching speeches for {date}...")

        try:
            items = fetch_speech_metadata(date, args.limit)
        except requests.exceptions.JSONDecodeError:
            print(f"{date}: non-JSON response, skipping")
            continue
        except requests.exceptions.HTTPError as e:
            print(f"{date}: HTTP error {e}, skipping")
            continue
        except requests.exceptions.RequestException as e:
            print(f"{date}: request error {e}, skipping")
            continue

        if not items:
            print(f"{date}: no speeches")
            continue

        print(f"{date}: found {len(items)} speeches")

        for i, item in enumerate(items, start=1):
            recorded_docs = item.get("recorded_in_a_realization_of", [])

            doc_id = None
            original_lang = "en"

            if recorded_docs:
                recorded_doc = recorded_docs[0]

                doc_id = recorded_doc.get("identifier") or recorded_doc.get("id", "").split("/")[-1]

                original_languages = recorded_doc.get("originalLanguage", [])
                if original_languages:
                    lang_code = original_languages[0].split("/")[-1]
                    original_lang = LANG_MAP.get(lang_code, lang_code.lower())

            speaker_id = get_speaker_id(item)
            text = find_embedded_text(item) or ""
            source_url = ""

            all_rows.append({
                "speech_event_id": item.get("id") or item.get("@id"),
                "doc_id": doc_id,
                "speaker_id": speaker_id,
                "original_language": original_lang,
                "date": item.get("activity_date"),
                "start_time": item.get("activity_start_date"),
                "end_time": item.get("activity_end_date"),
                "debate_title": get_label(item),
                "text": text,
                "source_url": source_url,
            })

        time.sleep(0.2)

    if not all_rows:
        print("No rows found.")
        return

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} rows to {args.out}")

if __name__ == "__main__":
    main()

    ##################### INSTRUCTIONS TO RUN ##############################
    #### In the command below
            # Replace <this_scripts_file_path> with the file path!
            # copy into terminal/command prompt

    # python <this_scripts_file_path> --date 2024-01-15 --limit 50

    # e.g. 
    # python europarl_speeches.py --date 2024-01-15 --limit 50


    # Arguments:
    #       -- date: date to retrieve speeches
    #       -- limit: maximum number of speeches to retrieve
