# scrapers/wikipedia_s.py

import pandas as pd
import wikipediaapi

def get_company_profile(company_name, user_agent):
    """
    Fetches the company profile from Wikipedia, including the summary and infobox.
    """
    if not user_agent:
        print("Wikipedia User-Agent not set. Skipping Wikipedia scraping.")
        return pd.DataFrame()

    # Corrected the line below to include the user_agent
    wiki_wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language='en')
    
    page_py = wiki_wiki.page(company_name)

    if not page_py.exists():
        print(f"Wikipedia page for '{company_name}' not found.")
        return pd.DataFrame()

    # Extract Infobox data
    infobox_data = {}
    if hasattr(page_py, 'section_by_title') and page_py.section_by_title('Infobox'):
        # This is a simplification; real infobox parsing is more complex
        # and may require a different approach if this fails.
        pass # Placeholder for more robust infobox parsing if needed

    profile_data = {
        'Name': company_name,
        'Summary': page_py.summary,
        'URL': page_py.fullurl
    }
    profile_data.update(infobox_data)
    
    df = pd.DataFrame([profile_data])
    print(f"Successfully scraped Wikipedia profile for {company_name}.")
    return df