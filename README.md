# jobspy-google: JobSpy with Google Jobs working again

[JobSpy](https://github.com/speedyapply/JobSpy)'s README says it plainly: "**Q: No results when using "google"? A: Google Jobs is currently unavailable.**" Google now serves job data only to browsers that run JavaScript, so `site_name="google"` returns an empty DataFrame (see [issue #284](https://github.com/speedyapply/JobSpy/issues/284)).

**jobspy-google keeps JobSpy's `scrape_jobs` arguments and DataFrame columns, so your code doesn't change.** `"google"` runs on a hosted Google Jobs API that renders Google Jobs for you, and every other site (`indeed`, `linkedin`, `glassdoor`, `zip_recruiter`, `bayt`, `naukri`, `bdjobs`) is passed to JobSpy unchanged.

```diff
- from jobspy import scrape_jobs
+ from jobspy_google import scrape_jobs
```

## Install

```bash
pip install git+https://github.com/retracn/jobspy-google
```

You need an Apify API token for the Google part: create a [free Apify account](https://console.apify.com/sign-up), copy the token from [Settings → API & Integrations](https://console.apify.com/settings/integrations) and set `APIFY_TOKEN`, or pass `apify_token="..."`.

## Use it exactly like JobSpy

```python
from jobspy_google import scrape_jobs

jobs = scrape_jobs(
    site_name=["indeed", "linkedin", "google"],
    search_term="software engineer",
    google_search_term="software engineer jobs near San Francisco, CA since yesterday",
    location="San Francisco, CA",
    results_wanted=20,
    hours_old=72,
    country_indeed="USA",
)
print(jobs[["site", "title", "company", "location", "date_posted", "min_amount", "max_amount", "job_url"]])
```

- The same 34 columns in the same order, sorted by site and newest first, as JobSpy returns.
- Google rows fill `id`, `job_url` (the apply link), `job_url_direct`, `title`, `company`, `location`, `date_posted`, `job_type`, `salary_source`, `interval`, `min_amount`, `max_amount`, `currency`, `is_remote` and `description`.
- For Google, `google_search_term` is used as the search when given; otherwise `search_term` and `location`. `hours_old`, `is_remote`, `job_type`, `results_wanted`, `offset` and `country_indeed` apply (26 countries, including USA, UK, Canada, India, Germany, Spain and Mexico).
- `site_name=None` (all sites) runs JobSpy's other sites plus Google.

## Cost and speed

Google Jobs results cost $0.03 per search plus $2 per 1,000 jobs on your Apify account, so a 20-job search costs about 7 cents and the free plan's $5 monthly credit covers about 70 of them. A Google search takes about 20–60 seconds, since Google Jobs needs a real browser. The other sites cost nothing extra and run in JobSpy as before.

## How it works

The Google part calls [Google Jobs Scraper](https://apify.com/automationnation/google-jobs-scraper) through Apify's `run-sync-get-dataset-items` endpoint and maps its output to JobSpy's columns. That Actor also returns fields JobSpy doesn't have, such as the job board it came from ("via LinkedIn"), qualifications, benefits and all apply links, if you call it directly.

Disclosure: I maintain the Actor this package calls. MIT licensed. Not affiliated with Google or with JobSpy.
