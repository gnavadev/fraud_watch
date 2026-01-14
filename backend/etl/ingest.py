import requests
import csv
import time

def get_minneapolis_child_care(query="child care", city_filter="minneapolis", limit=20):
    """
    Fetches nonprofits in MN matching the query, then filters by city locally.
    """
    base_url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
    output_file = f"{city_filter}_{query.replace(' ', '_')}.csv"
    
    # ProPublica API requires state[id] for state filtering.
    # We filter for 'MN' at the API level.
    params = {
        "q": query,
        "state[id]": "MN",
        "page": 0
    }
    headers = {"User-Agent": "Mozilla/5.0 (Educational Project)"}

    results = []
    
    print(f"Searching for '{query}' in {city_filter.title()}, MN...")

    while len(results) < limit:
        try:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            orgs = data.get("organizations", [])
            
            if not orgs:
                print("No more pages available from API.")
                break
            
            for org in orgs:
                # API returns cities in various cases (often UPPERCASE)
                org_city = org.get("city", "").lower()
                
                if org_city == city_filter.lower():
                    row = {
                        "Name": org.get("name"),
                        "EIN": org.get("ein"),
                        "Address": org.get("address"),
                        "City": org.get("city"),
                        "State": org.get("state"),
                        "Revenue": org.get("revenue", 0),
                        "Assets": org.get("asset_amount", 0),
                        "PDF URL": org.get("pdf_url")
                    }
                    results.append(row)
                    
                    if len(results) >= limit:
                        break
            
            print(f"Checked page {params['page']}. Found {len(results)} matches so far.")
            params["page"] += 1
            
            # Be polite to the API
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break

    # Save to CSV
    if results:
        keys = results[0].keys()
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(results)
            print(f"\nSuccess! Saved {len(results)} organizations to '{output_file}'.")
        except IOError as e:
            print(f"Error saving file: {e}")
    else:
        print("No matching organizations found in Minneapolis.")

if __name__ == "__main__":
    get_minneapolis_child_care()