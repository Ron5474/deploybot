import requests
import json
from langchain_core.tools import tool

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch="

@tool
def retrieve_cve(app_name):
    """
    Look up known CVEs and security vulnerabilities for a self-hosted application. Input should be the application name. Use this when the user asks
    about security vulnerabilities, CVEs, or whether an app is safe to use.
    """
    app_url = f"{NVD_URL}{app_name}"

    response = requests.get(app_url)

    if response.status_code != 200:
        return "Error Fetching CVE Information"

    vulnerabilities = response.json().get("vulnerabilities", [])

    if not vulnerabilities:
        return f"No CVEs found for {app_name}"

    cves = []
    for vuln in vulnerabilities:
        cve = vuln["cve"]

        cve_id = cve["id"]
        description = cve["descriptions"][0]["value"]
        published = cve["published"]

        metrics = cve.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [])
        severity = cvss_v31[0]["cvssData"]["baseSeverity"] if cvss_v31 else "N/A"
        
        cves.append({
            "id": cve_id,
            "description": description,
            "severity": severity,
            "published": published
        })

    return json.dumps(cves, indent=2)

