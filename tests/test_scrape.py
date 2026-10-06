import json
import sys
import types
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

FIX = json.loads((Path(__file__).parent / "google-jobs.json").read_text())


class FakeResp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def env(monkeypatch):
    calls = {"apify": [], "jobspy": []}

    def fake_post(url, params=None, json=None, headers=None, timeout=None):
        calls["apify"].append(json)
        if headers["Authorization"] != "Bearer good":
            return FakeResp(401, {})
        return FakeResp(201, FIX)

    def fake_jobspy(**kw):
        calls["jobspy"].append(kw)
        return pd.DataFrame([{"id": "in-1", "site": "indeed", "job_url": "https://indeed.com/1", "title": "Engineer", "company": "Acme",
                              "location": "Austin, TX, US", "date_posted": date(2026, 10, 4), "is_remote": False, "description": "x"}])

    import jobspy_google._scrape as mod
    monkeypatch.setattr(mod.requests, "post", fake_post)
    monkeypatch.setitem(sys.modules, "jobspy", types.SimpleNamespace(scrape_jobs=fake_jobspy))
    monkeypatch.setenv("APIFY_TOKEN", "good")
    return calls


def test_google_only_matches_jobspy_columns(env):
    from jobspy_google import DESIRED_ORDER, scrape_jobs
    df = scrape_jobs(site_name="google", search_term="software engineer", location="New York", results_wanted=5, hours_old=72, country_indeed="USA", is_remote=True, job_type="fulltime")
    assert list(df.columns) == DESIRED_ORDER
    assert len(df) == len(FIX) and set(df["site"]) == {"google"}
    first = df.iloc[0]
    assert first["id"].startswith("go-") and first["title"] and first["company"]
    assert isinstance(first["date_posted"], date)
    assert env["jobspy"] == [], "JobSpy isn't called for google"
    inp = env["apify"][0]
    assert inp["queries"] == ["software engineer"] and inp["location"] == "New York"
    assert inp["datePosted"] == "3days" and inp["country"] == "us" and inp["remoteOnly"] is True and inp["employmentType"] == "fulltime"


def test_salary_and_job_type_mapping(env):
    from jobspy_google import scrape_jobs
    df = scrape_jobs(site_name=["google"], search_term="software engineer")
    paid = df[df["min_amount"].notna()]
    assert len(paid) >= 1
    row = paid.iloc[0]
    assert row["salary_source"] == "direct_data" and row["interval"] in {"yearly", "monthly", "weekly", "daily", "hourly"}
    assert row["currency"] == "USD"
    assert set(df["job_type"].dropna()) <= {"fulltime", "parttime", "contract", "internship", "temporary", "fulltime, parttime"}


def test_other_sites_go_to_jobspy_and_results_merge(env):
    from jobspy_google import scrape_jobs
    df = scrape_jobs(site_name=["indeed", "google"], search_term="engineer", google_search_term="engineer jobs near Austin, TX since yesterday", location="Austin, TX", results_wanted=3, offset=1)
    assert env["jobspy"][0]["site_name"] == ["indeed"]
    assert env["apify"][0]["queries"] == ["engineer jobs near Austin, TX since yesterday"] and "location" not in env["apify"][0]
    assert env["apify"][0]["maxJobsPerQuery"] == 4
    assert list(df["site"].unique()) == ["google", "indeed"], "sorted by site like JobSpy"
    assert (df["site"] == "google").sum() == 3, "offset and results_wanted applied"


def test_all_sites_by_default_and_site_enums(env):
    from jobspy_google import scrape_jobs
    Site = types.SimpleNamespace(GOOGLE=types.SimpleNamespace(value="google"))
    scrape_jobs(search_term="nurse")
    assert "google" not in env["jobspy"][0]["site_name"] and "linkedin" in env["jobspy"][0]["site_name"]
    env["jobspy"].clear()
    scrape_jobs(site_name=[Site.GOOGLE], search_term="nurse")
    assert env["jobspy"] == []


def test_errors(env, monkeypatch):
    from jobspy_google import scrape_jobs
    with pytest.raises(ValueError, match="search_term or google_search_term"):
        scrape_jobs(site_name="google")
    with pytest.raises(RuntimeError, match="rejected the API token"):
        scrape_jobs(site_name="google", search_term="x", apify_token="bad")
    monkeypatch.delenv("APIFY_TOKEN")
    with pytest.raises(RuntimeError, match="No Apify API token"):
        scrape_jobs(site_name="google", search_term="x")
