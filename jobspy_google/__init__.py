"""JobSpy's scrape_jobs with a working Google Jobs source.

JobSpy's README says "Google Jobs is currently unavailable": Google now serves job data only to browsers
that run JavaScript, so site_name="google" returns nothing. This scrape_jobs has the same signature and
returns the same DataFrame columns. "google" runs AutomationNation's Google Jobs Scraper on Apify, and
every other site (indeed, linkedin, glassdoor, zip_recruiter, ...) is passed to JobSpy unchanged.
Set APIFY_TOKEN (free account: https://console.apify.com/sign-up) or pass apify_token=.
"""

from ._scrape import DESIRED_ORDER, scrape_jobs

__all__ = ["scrape_jobs", "DESIRED_ORDER"]
__version__ = "1.0.0"
