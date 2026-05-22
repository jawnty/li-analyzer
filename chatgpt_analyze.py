import pandas as pd
from rapidfuzz import fuzz  # Use rapidfuzz.fuzz if you prefer a modern alternative
import re

# Function to parse market capitalization values.
# This function handles strings with "M" (millions) or "B" (billions) and returns a float in dollars.
def parse_market_cap(cap_str):
    if pd.isna(cap_str):
        return None
    # Clean the string: remove commas, dollar signs and extra spaces.
    cap_str = cap_str.replace(',', '').replace('$', '').strip()
    # Check for "M" or "B" indicators
    if 'M' in cap_str:
        try:
            return float(cap_str.replace('M', '')) * 1e6
        except ValueError:
            return None
    elif 'B' in cap_str:
        try:
            return float(cap_str.replace('B', '')) * 1e9
        except ValueError:
            return None
    else:
        try:
            return float(cap_str)
        except ValueError:
            return None

# Define a function to compute a seniority score for a given job title.
# The function assigns higher numerical values for roles that typically have decision-making authority.
def seniority_score(title):
    if pd.isna(title):
        return 0
    title = title.lower()
    score = 0
    if 'ceo' in title or 'chief executive' in title:
        score = max(score, 100)
    if 'coo' in title or 'chief operating' in title:
        score = max(score, 90)
    if 'cfo' in title or 'chief financial' in title:
        score = max(score, 90)
    if 'cto' in title or 'chief technology' in title:
        score = max(score, 90)
    if 'president' in title:
        score = max(score, 80)
    if 'vice president' in title or 'vp' in title:
        score = max(score, 70)
    if 'director' in title:
        score = max(score, 60)
    if 'manager' in title:
        score = max(score, 50)
    return score

# Function to perform fuzzy matching between a given company name from LinkedIn and the list of companies.
def get_matching_company(linkedin_company, companies_df, threshold=80):
    best_score = 0
    best_match = None
    # Loop through each company in the filtered Companies dataframe.
    for idx, row in companies_df.iterrows():
        # Use partial_ratio for fuzzy matching between the two names.
#        score = fuzz.partial_ratio(linkedin_company.lower(), row['Company Name'].lower())
        score = fuzz.partial_ratio(str(linkedin_company).lower(), str(row['Company Name']).lower())

        if score > best_score:
            best_score = score
            best_match = row['Company Name']
    # Only accept the match if it exceeds the chosen threshold.
    if best_score >= threshold:
        return best_match, best_score
    else:
        return None, best_score

def main():
    # Load LinkedIn connections and companies data.
    linkedin_df = pd.read_csv("LinkedIn.csv")
    companies_df = pd.read_csv("Companies.csv")
    
    # Parse market cap and filter for companies with market cap between $50M and $100M.
    companies_df['Market Cap Numeric'] = companies_df['Market Capitalization'].apply(parse_market_cap)
    companies_df_filtered = companies_df[
        (companies_df['Market Cap Numeric'] >= 50e6) & (companies_df['Market Cap Numeric'] <= 100e6)
    ]
    
    # Create new columns to store the matched company and the fuzzy match score.
    linkedin_df['Matched Company'] = None
    linkedin_df['Match Score'] = None

    # For each LinkedIn record, perform fuzzy matching against the filtered companies.
    for idx, row in linkedin_df.iterrows():
        company_name = row['Company']
        matched_company, score = get_matching_company(company_name, companies_df_filtered)
        if matched_company is not None:
            linkedin_df.at[idx, 'Matched Company'] = matched_company
            linkedin_df.at[idx, 'Match Score'] = score

    # Filter out rows with no matched company.
    filtered_linkedin_df = linkedin_df.dropna(subset=['Matched Company']).copy()
    
    # Compute seniority score for each connection based on their job title.
    filtered_linkedin_df['Seniority Score'] = filtered_linkedin_df['Position'].apply(seniority_score)
    
    # For companies with multiple connections in your network, keep only the highest-ranking (by seniority score).
    highest_ranking = (
        filtered_linkedin_df.loc[filtered_linkedin_df.groupby('Matched Company')['Seniority Score'].idxmax()]
        .reset_index(drop=True)
    )
    
    # Save the final list of connections to a CSV file.
    highest_ranking.to_csv("selected_connections.csv", index=False)
    print("Selected connections saved to selected_connections.csv")
    
if __name__ == '__main__':
    main()
