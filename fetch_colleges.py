import os
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the same directory as the script
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

def get_top_500_colleges():
    api_key = os.getenv("data_gov_key")
    if not api_key:
        raise ValueError("API key not found. Please ensure 'data_key' is set in your .env file.")
    url = "https://api.data.gov/ed/collegescorecard/v1/schools.json"
    
    # Parameters for the API:
    # 1. 'school.degrees_awarded.highest=3' (4-year institutions)
    # 2. 'latest.student.size__range=1..' (Must have students)
    # 3. 'fields' (Specific data points we want)
    params = {
        "api_key": api_key,
        "school.degrees_awarded.highest": 3,
        "latest.student.size__range": "1..",
        "fields": "id,school.name,latest.student.size,school.city,school.state",
        "sort": "latest.student.size:desc",
        "per_page": 100, # API max per page
    }

    all_schools = []
    
    # Loop through first 5 pages to get 500 schools
    for page in range(5):
        params["page"] = page
        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")

        data = response.json()
        all_schools.extend(data['results'])

    # Convert to DataFrame
    df = pd.DataFrame(all_schools)

    # Rename columns safely using a mapping
    df = df.rename(columns={
        "id": "ID",
        "school.name": "School Name",
        "latest.student.size": "Enrollment",
        "school.city": "City",
        "school.state": "State"
    })
    return df

if __name__ == "__main__":
    df_top_500 = get_top_500_colleges()
    df_top_500.to_csv("top_500_colleges.csv", index=False)