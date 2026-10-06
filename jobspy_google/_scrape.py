import hashlib
import os
from datetime import datetime

import pandas as pd
import requests

ACTOR = "automationnation~google-jobs-scraper"
API = "https://api.apify.com/v2"
ALL_SITES = ["linkedin", "indeed", "zip_recruiter", "glassdoor", "google", "bayt", "naukri", "bdjobs"]
# JobSpy's column order (jobspy/util.py desired_order).
DESIRED_ORDER = [
    "id", "site", "job_url", "job_url_direct", "title", "company", "location", "date_posted", "job_type",
    "salary_source", "interval", "min_amount", "max_amount", "currency", "is_remote", "job_level",
    "job_function", "listing_type", "emails", "description", "company_industry", "company_url",
    "company_logo", "company_url_direct", "company_addresses", "company_num_employees", "company_revenue",
    "company_description", "skills", "experience_range", "company_rating", "company_reviews_count",
    "vacancy_count", "work_from_home_type",
]
COUNTRIES = {
    "usa": "us", "us": "us", "united states": "us", "uk": "uk", "united kingdom": "uk", "gb": "uk", "canada": "ca",
    "india": "in", "singapore": "sg", "south africa": "za", "uae": "ae", "united arab emirates": "ae",
    "philippines": "ph", "malaysia": "my", "nigeria": "ng", "pakistan": "pk", "hong kong": "hk", "ghana": "gh",
    "qatar": "qa", "saudi arabia": "sa", "egypt": "eg", "germany": "de", "switzerland": "ch", "spain": "es",
    "mexico": "mx",
}
JOB_TYPES = {"FULL_TIME": "fulltime", "PART_TIME": "parttime", "CONTRACTOR": "contract", "INTERN": "internship", "TEMPORARY": "temporary"}
EMPLOYMENT = {"fulltime": "fulltime", "parttime": "parttime", "contract": "contractor", "internship": "internship"}
INTERVALS = {"YEAR": "yearly", "MONTH": "monthly", "WEEK": "weekly", "DAY": "daily", "HOUR": "hourly"}


def _sites(site_name):
    if site_name is None:
        return list(ALL_SITES)
    items = site_name if isinstance(site_name, (list, tuple, set)) else [site_name]
    return [str(getattr(s, "value", s)).lower() for s in items]


def _date_posted(hours_old):
    if not hours_old:
        return "any"
    h = int(hours_old)
    return "today" if h <= 24 else "3days" if h <= 72 else "week" if h <= 168 else "month" if h <= 720 else "any"


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _row(j):
    posted = j.get("postedAt")
    types = [JOB_TYPES.get(t, str(t).lower()) for t in (j.get("employmentTypes") or [])]
    lo, hi = _num(j.get("salaryMin")), _num(j.get("salaryMax"))
    return {
        "id": "go-" + (j.get("googleJobId") or hashlib.md5(f"{j.get('title')}|{j.get('companyName')}|{j.get('location')}".encode()).hexdigest()[:16]),
        "site": "google",
        "job_url": j.get("applyUrl") or j.get("jobUrl"),
        "job_url_direct": j.get("applyUrl"),
        "title": j.get("title"),
        "company": j.get("companyName"),
        "location": j.get("location"),
        "date_posted": datetime.fromisoformat(posted.replace("Z", "+00:00")).date() if posted else None,
        "job_type": ", ".join(types) if types else None,
        "salary_source": "direct_data" if lo or hi else None,
        "interval": INTERVALS.get(j.get("salaryPeriod")) if lo or hi else None,
        "min_amount": lo,
        "max_amount": hi,
        "currency": j.get("salaryCurrency") if lo or hi else None,
        "is_remote": bool(j.get("isRemote")),
        "description": j.get("description"),
    }


def _google_query(search_term, google_search_term, location):
    if google_search_term:
        return google_search_term, None
    if not search_term:
        raise ValueError("Google Jobs needs search_term or google_search_term.")
    return search_term, location


def _fetch_google(query, location, country, results_wanted, hours_old, is_remote, job_type, token, wait_secs):
    if not token:
        raise RuntimeError("No Apify API token: set APIFY_TOKEN or pass apify_token=. Free account: https://console.apify.com/sign-up, token: https://console.apify.com/settings/integrations")
    inp = {"queries": [query], "country": country, "maxJobsPerQuery": int(results_wanted), "datePosted": _date_posted(hours_old),
           "employmentType": EMPLOYMENT.get(str(job_type or "").lower().replace("_", ""), "any"), "remoteOnly": bool(is_remote)}
    if location:
        inp["location"] = location
    res = requests.post(f"{API}/acts/{ACTOR}/run-sync-get-dataset-items", params={"timeout": wait_secs, "clean": "true"}, json=inp,
                        headers={"Authorization": f"Bearer {token}", "User-Agent": "jobspy-google"}, timeout=wait_secs + 30)
    if res.status_code == 401:
        raise RuntimeError("Apify rejected the API token (check APIFY_TOKEN).")
    if res.status_code == 402:
        raise RuntimeError("Your Apify account has no credit left: https://console.apify.com/billing")
    res.raise_for_status()
    data = res.json()
    return data if isinstance(data, list) else []


def scrape_jobs(site_name=None, search_term=None, google_search_term=None, location=None, distance=50, is_remote=False,
                job_type=None, easy_apply=None, results_wanted=15, country_indeed="usa", proxies=None, ca_cert=None,
                description_format="markdown", linkedin_fetch_description=False, linkedin_company_ids=None, offset=0,
                hours_old=None, enforce_annual_salary=False, verbose=0, user_agent=None, fetch_description=False,
                apify_token=None, wait_secs=300, **kwargs) -> pd.DataFrame:
    """Same arguments and DataFrame as jobspy.scrape_jobs; "google" works again (via Apify)."""
    sites = _sites(site_name)
    frames = []
    others = [s for s in sites if s != "google"]
    if others:
        import jobspy  # python-jobspy

        frames.append(jobspy.scrape_jobs(
            site_name=others, search_term=search_term, google_search_term=google_search_term, location=location,
            distance=distance, is_remote=is_remote, job_type=job_type, easy_apply=easy_apply, results_wanted=results_wanted,
            country_indeed=country_indeed, proxies=proxies, ca_cert=ca_cert, description_format=description_format,
            linkedin_fetch_description=linkedin_fetch_description, linkedin_company_ids=linkedin_company_ids, offset=offset,
            hours_old=hours_old, enforce_annual_salary=enforce_annual_salary, verbose=verbose, user_agent=user_agent,
            fetch_description=fetch_description, **kwargs))
    if "google" in sites:
        query, loc = _google_query(search_term, google_search_term, location)
        country = COUNTRIES.get(str(country_indeed or "usa").strip().lower(), "us")
        token = apify_token or os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN")
        jobs = _fetch_google(query, loc, country, int(results_wanted) + int(offset or 0), hours_old, is_remote, job_type, token, min(int(wait_secs), 300))
        rows = [_row(j) for j in jobs[int(offset or 0):int(offset or 0) + int(results_wanted)]]
        if rows:
            frames.append(pd.DataFrame(rows))
    frames = [f.dropna(axis=1, how="all") for f in frames if f is not None and len(f)]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    for column in DESIRED_ORDER:
        if column not in df.columns:
            df[column] = None
    df = df[DESIRED_ORDER]
    return df.sort_values(by=["site", "date_posted"], ascending=[True, False]).reset_index(drop=True)
