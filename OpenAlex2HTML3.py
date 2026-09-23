import json
import requests
from collections import defaultdict

def fix_mojibake(s):
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin1").decode("utf8")
    except Exception:
        return s

def fix_dict_strings(obj):
    if isinstance(obj, dict):
        return {k: fix_dict_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [fix_dict_strings(v) for v in obj]
    elif isinstance(obj, str):
        return fix_mojibake(obj)
    else:
        return obj

base_url = "https://api.openalex.org/works"

filters = (
    "authorships.author.id:"
    "a5107139754|a5108684139|a5025520854|a5036760070|"
    "a5001720782|a5058635802|a5066544731|a5037784628|"
    "a5017428281|a5058589735|a5027644564|a5041327556|"
    "a1995438260|a5028359320,"
    "authorships.institutions.lineage:i75929689|i140172145,"
    "publication_year:2016-2026"
)

params = {
    "filter": filters,
    "sort": "publication_year:desc",
    "per_page": 100,
    "cursor": "*"
}

results = []
page_number = 0
total_expected = None

while True:
    page_number += 1

    response = requests.get(
        base_url,
        params=params,
        timeout=60
    )
    response.raise_for_status()

    page_data = response.json()

    if total_expected is None:
        total_expected = page_data.get("meta", {}).get("count")
        print(f"OpenAlex reports {total_expected} matching works")

    batch = page_data.get("results", [])

    if not batch:
        break

    results.extend(batch)

    print(
        f"Page {page_number}: "
        f"{len(batch)} works; "
        f"{len(results)} retrieved total"
    )

    next_cursor = page_data.get("meta", {}).get("next_cursor")

    if not next_cursor:
        break

    params["cursor"] = next_cursor


print(f"Finished: retrieved {len(results)} OpenAlex works")

# Re-create data in the form expected by the rest of the script
data = {
    "results": results
}

specific_work_ids = ["W4406278796", "W4414299727", "W4414003956", "W4413410768", "W4406080021",
                     "W4404789954", "W4402922983", "W4408637455", "W4414848838"]  

results = data.get("results", [])

# Add specifically requested works
specific_works = []

for wid in specific_work_ids:
    work_url = f"https://api.openalex.org/works/{wid}"

    response = requests.get(work_url, timeout=30)

    if response.status_code != 200:
        print(f"Could not retrieve {wid}: HTTP {response.status_code}")
        continue

    try:
        work = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Could not decode JSON for {wid}")
        continue

    specific_works.append(work)


# Combine all works

# Combine all works
all_results = specific_works + results

# Sort newest first, so when multiple Zenodo versions are found,
# the newest version is retained.
all_results.sort(
    key=lambda w: w.get("publication_date") or "",
    reverse=True
)


def normalize_doi(doi):
    """Return DOI without https://doi.org/ prefix."""
    if not doi:
        return ""

    doi = doi.strip().lower()

    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    elif doi.startswith("http://doi.org/"):
        doi = doi[len("http://doi.org/"):]

    return doi


# Cache Zenodo lookups so the same record is never requested twice
zenodo_concept_cache = {}


def get_dedup_key(work):
    doi = (
        work.get("doi")
        or (work.get("ids") or {}).get("doi")
        or ""
    )

    doi = normalize_doi(doi)

    # Special handling for Zenodo versioned records
    if doi.startswith("10.5281/zenodo."):

        record_id = doi.rsplit(".", 1)[-1]

        if record_id not in zenodo_concept_cache:
            try:
                r = requests.get(
                    f"https://zenodo.org/api/records/{record_id}",
                    timeout=30
                )
                r.raise_for_status()

                zdata = r.json()

                concept_doi = normalize_doi(
                    zdata.get("conceptdoi", "")
                )

                if concept_doi:
                    zenodo_concept_cache[record_id] = concept_doi
                else:
                    zenodo_concept_cache[record_id] = doi

            except (
                requests.RequestException,
                requests.exceptions.JSONDecodeError
            ) as e:
                print(
                    f"Could not obtain Zenodo concept DOI "
                    f"for {doi}: {e}"
                )
                zenodo_concept_cache[record_id] = doi

        return (
            "zenodo-concept",
            zenodo_concept_cache[record_id]
        )

    # Normal publication: DOI is the preferred identifier
    if doi:
        return ("doi", doi)

    # Fall back to OpenAlex ID when there is no DOI
    return ("openalex", work.get("id", ""))


# Deduplicate
deduplicated_results = []
seen = set()

for work in all_results:

    key = get_dedup_key(work)

    if key in seen:
        print(
            f"Removing duplicate/version: "
            f"{work.get('title')} "
            f"{work.get('doi', '')}"
        )
        continue

    seen.add(key)
    deduplicated_results.append(work)


data["results"] = deduplicated_results

data = fix_dict_strings(data)

# List of last names to underline
underline_last_names = {"blinov", "schaff","agmon", "roy", "moraru", "mendes","guertin","kshitiz", "gupta","loew","mayer",
                        "slepchenko","cowan","acker","sarabipour","vera-licona","rodionov","ji yu","yi wu","Abhijit"}


# Dictionary to store publications grouped by year
publications_by_year = defaultdict(list)

# Iterate through each research article
for result in data["results"]:
    # Get the publication year
    publication_year = result["publication_year"]
    
    # Get the journal title
    journal_title = (
        (((result.get("primary_location") or {}).get("source") or {}).get("display_name"))
        or "N/A"
    )
    
    # Get the publication title
    publication_title = result["title"]
    
    # Get the DOI
    doi = result["ids"].get("doi", "N/A")  # Use "N/A" if DOI is not available
    
     # Get volume, issue, and pages
    biblio = result.get("biblio", {})
    volume = biblio.get("volume")
    issue = biblio.get("issue")
    first_page = biblio.get("first_page")
    last_page = biblio.get("last_page")
    
    # Format volume, issue, and pages
    details = []
    if volume:
        details.append(f"<b>{volume}</b>")
    if issue:
        details.append(f"({issue})")
    if first_page and last_page:
        details.append(f": {first_page}-{last_page}")
    elif first_page:
        details.append(f": {first_page}")

    details_str = "".join(details)  # Join only existing details

    # Get list of authors with underlining for matching names
    formatted_authors = []
    for authorship in result["authorships"]:
        author_name = authorship["author"]["display_name"]
        last_name = author_name.split()[-1].lower()  # Extract last name (case insensitive)
        full_name = author_name.lower()  # Full name (case insensitive)

        if last_name in underline_last_names or full_name in underline_last_names:
            formatted_authors.append(f"<b>{author_name}</b>")  # Underline matching names
        else:
            formatted_authors.append(author_name)
    if formatted_authors == ['Dan Vasilescu', 'James C. Schaff', '<b>Ion I. Moraru</b>', '<b>Michael L Blinov</b>', 'Dan Vasilescu', 'James C. Schaff', '<b>Ion I. Moraru</b>', '<b>Michael L Blinov</b>']:
        formatted_authors = ['Dan Vasilescu', 'James C. Schaff', '<b>Ion I. Moraru</b>', '<b>Michael L Blinov</b>']
    # Store formatted publication details
    publication_entry = f"<p>{', '.join(formatted_authors)}. ({publication_year}) {publication_title}. <i>{journal_title}</i>"
    if details_str:
        publication_entry += f", {details_str}"
    publication_entry += f" <a href='{doi}'>{doi}</a></p><br>"
    
    publications_by_year[publication_year].append(publication_entry)

# Create HTML content
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Publications</title>
</head>
<body>
    <title>Publications</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h2 { color: #2c3e50; }
        p { margin: 5px 0; }
        a { color: #2980b9; text-decoration: none; }
        a:hover { text-decoration: underline; }
        u { font-weight: bold; color: #c0392b; }  /* Red underline for emphasis */
    </style>
</head>
<body>
    <h1>Publications</h1>
"""

# Sort and append publications by year in HTML format
for year in sorted(publications_by_year.keys(), reverse=True):
    html_content += f"<h2>{year}</h2>\n"
    html_content += "\n".join(publications_by_year[year])
    html_content += "<hr>\n"

html_content += """
</body>
</html>
"""

# Write to an HTML file
file_path = "publications.html"
with open(file_path, "w", encoding="utf-8") as file:
    file.write(html_content)

print(f"HTML file saved as {file_path}")