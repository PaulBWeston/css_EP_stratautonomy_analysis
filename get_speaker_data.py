import pandas as pd
import requests
import time
import json

API_BASE = "https://data.europarl.europa.eu/api/v2"


def extract_items(payload):
    data = payload.get("data", payload)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "@graph" in data:
        return data["@graph"]
    if isinstance(data, dict):
        return [data]

    return []


def fetch_mep_raw(speaker_id):
    """
    Fetch raw MEP/person metadata for one speaker_id.
    """
    speaker_id = str(speaker_id).replace(".0", "").strip()

    url = f"{API_BASE}/meps/{speaker_id}"

    params = {
        "format": "application/ld+json",
        "json-layout": "framed",
    }

    r = requests.get(url, params=params, timeout=30)

    if r.status_code == 204 or not r.text.strip():
        return None

    if r.status_code == 404:
        print(f"No MEP found for speaker_id={speaker_id}")
        return None

    r.raise_for_status()

    payload = r.json()
    items = extract_items(payload)

    raw = items[0] if items else payload

    returned_id = str(raw.get("id") or raw.get("@id") or "")
    print(f"  requested speaker_id={speaker_id}, returned_id={returned_id}")

    return raw




def find_values_by_key(obj, key_names):
    """
    Recursively collect values whose key matches one of key_names.
    Useful because Europarl JSON-LD is nested.
    """
    results = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in key_names:
                results.append(v)

            results.extend(find_values_by_key(v, key_names))

    elif isinstance(obj, list):
        for x in obj:
            results.extend(find_values_by_key(x, key_names))

    return results


def clean_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ["label", "prefLabel", "name", "identifier", "id", "@id", "@value"]:
            if key in value:
                return clean_value(value[key])
        return str(value)
    if isinstance(value, list):
        return " | ".join(clean_value(x) for x in value)
    return str(value)

def get_eu_political_group_memberships(raw):
    memberships = raw.get("hasMembership", []) or raw.get("membership", [])

    groups = []

    for m in memberships:
        if not isinstance(m, dict):
            continue

        if m.get("membershipClassification") != "def/ep-entities/EU_POLITICAL_GROUP":
            continue

        period = m.get("memberDuring", {})

        groups.append({
            "eu_political_group_id": m.get("organization"),
            "eu_political_group_role": m.get("role"),
            "eu_political_group_valid_from": period.get("startDate"),
            "eu_political_group_valid_to": period.get("endDate"),
        })

    return groups


def flatten_mep(speaker_id, raw):
    """
    First-pass flattening. We will inspect output and refine field names.
    """
    eu_groups = get_eu_political_group_memberships(raw)
    eu_groups = sorted(
    eu_groups,
    key=lambda g: g.get("eu_political_group_valid_from") or "",
    reverse=True
    ) # need sorting to pull the current group
    current_or_latest_group = eu_groups[0] if eu_groups else {}
    
    
    if raw is None:
        return {
            "speaker_id": speaker_id,
            "speaker_name": None,
            "country": None,
            "political_group_raw": None,
            "national_party_raw": None,
        }

    name_candidates = find_values_by_key(
        raw,
        ["label", "prefLabel", "fullName", "name"]
    )

    country_candidates = find_values_by_key(
        raw,
        ["country", "citizenship", "nationality", "represents_country"]
    )

    political_group_candidates = find_values_by_key(
        raw,
        ["political_group", "politicalGroup", "has_membership", "membership"]
    )

    national_party_candidates = find_values_by_key(
        raw,
        ["nationalPoliticalGroup", "national_party", "nationalParty", "party"]
    )

    return {
        "speaker_id": speaker_id,
        "speaker_name": clean_value(name_candidates[0]) if name_candidates else None,
        "country": clean_value(country_candidates[0]) if country_candidates else None,

        "eu_political_group_id": current_or_latest_group.get("eu_political_group_id"),
        "eu_political_group_role": current_or_latest_group.get("eu_political_group_role"),
        "eu_political_group_valid_from": current_or_latest_group.get("eu_political_group_valid_from"),
        "eu_political_group_valid_to": current_or_latest_group.get("eu_political_group_valid_to"),

        "national_party_raw": clean_value(national_party_candidates[0]) if national_party_candidates else None,
    }

def print_membership_classifications(raw):
    memberships = raw.get("hasMembership", []) or raw.get("membership", [])

    classifications = sorted(set(
        m.get("membershipClassification")
        for m in memberships
        if isinstance(m, dict) and m.get("membershipClassification")
    ))

    print("Membership classifications found:")
    for c in classifications:
        print(" ", c)

def fetch_org_raw(org_id):
    org_id = str(org_id).strip()

    # org/5153 -> 5153
    org_num = org_id.split("/")[-1]

    url = f"{API_BASE}/organizations/{org_num}"

    params = {
        "format": "application/ld+json",
        "json-layout": "framed",
    }

    r = requests.get(url, params=params, timeout=30)

    if r.status_code == 204 or not r.text.strip():
        return None

    if r.status_code == 404:
        print(f"No organization found for {org_id}")
        return None

    r.raise_for_status()

    payload = r.json()
    items = extract_items(payload)
    return items[0] if items else payload

def fetch_org_raw(org_id):
    org_id = str(org_id).strip()

    # org/5153 -> 5153
    org_num = org_id.split("/")[-1]

    url = f"{API_BASE}/organizations/{org_num}"

    params = {
        "format": "application/ld+json",
        "json-layout": "framed",
    }

    r = requests.get(url, params=params, timeout=30)

    if r.status_code == 204 or not r.text.strip():
        return None

    if r.status_code == 404:
        print(f"No organization found for {org_id}")
        return None

    r.raise_for_status()

    payload = r.json()
    items = extract_items(payload)
    return items[0] if items else payload

def build_speakers_dataframe(speeches_csv, out_csv="europarl_speakers.csv", save_every=10):
    speeches = pd.read_excel(speeches_csv)

    speaker_ids = (
        speeches["speaker_id"]
        .dropna()
        .astype(str)
        .str.replace(".0", "", regex=False)
        .unique()
    )

    # Resume if output file already exists
    try:
        existing = pd.read_csv(out_csv)
        done_ids = set(existing["speaker_id"].astype(str))
        rows = existing.to_dict("records")
        print(f"Resuming: found {len(done_ids)} existing speaker rows in {out_csv}")
    except FileNotFoundError:
        done_ids = set()
        rows = []

    for i, speaker_id in enumerate(speaker_ids, start=1):
        if speaker_id in done_ids:
            print(f"[{i}/{len(speaker_ids)}] Skipping {speaker_id} already done")
            continue

        print(f"[{i}/{len(speaker_ids)}] Fetching speaker {speaker_id}")

        try:
            raw = fetch_mep_raw(speaker_id)
            # print_membership_classifications(raw)
            # raise SystemExit
            row = flatten_mep(speaker_id, raw)

            print("  row to append:")
            print(row)

            rows.append(row)
            done_ids.add(speaker_id)

        except Exception as e:
            print(f"Error fetching {speaker_id}: {e}")
            print("Saving progress before continuing...")
            pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8")
            continue

        # Save every N newly fetched rows
        if len(rows) % save_every == 0:
            pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8")
            print(f"Saved progress: {len(rows)} rows")

        time.sleep(0.2)

    speakers = pd.DataFrame(rows)
    speakers.to_csv(out_csv, index=False, encoding="utf-8")

    print(f"Finished. Saved {len(speakers)} rows to {out_csv}")
    return speakers


if __name__ == "__main__":
    speakers = build_speakers_dataframe(
        speeches_csv="css_scored_samples_with_llm_vpartial_cleaned.xlsx",
        out_csv="europarl_speakers_small_v3.csv"
    )

    print(speakers.head())

    #get_speaker_data.py