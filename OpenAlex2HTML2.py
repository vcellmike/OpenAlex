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

url = (
    "https://api.openalex.org/works?"
    "page=1&"
    "filter=authorships.author.id:a5107139754|a5108684139|a5025520854|a5036760070|a5001720782|"
    "a5066544731|a5037784628|a5017428281|a5058589735|a5027644564|a5041327556|a1995438260|a5107139754,"
    "authorships.institutions.lineage:i75929689|i140172145"
    # optional year range to exclude older items like 2013:
    ",publication_year:2015-2025"
    "&sort=publication_year:desc&per_page=150"
)

data = requests.get(url).json()

specific_work_ids = ["w4406278796", "w4414299727"]  
results = data.get("results", [])
existing_ids = {w["id"] for w in results}
specific_works = []
for wid in specific_work_ids:
    work_url = f"https://api.openalex.org/works/{wid}"
    work = requests.get(work_url).json()
    
    if work.get("id") not in existing_ids:
        specific_works.append(work)
        existing_ids.add(work["id"])   # avoid duplicates if multiple lists used later

# Insert all of them at the top in order


#data["results"].insert(0, specific_work)
data["results"] = specific_works + results

data = fix_dict_strings(data)

# List of last names to underline
underline_last_names = {"blinov", "agmon", "roy", "moraru", "mendes","guertin","kshitiz","loew","mayer",
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