import pandas as pd
import re
from thefuzz import process, fuzz

# --- Configuration ---
LINKEDIN_FILE = 'LinkedIn.csv'
COMPANIES_FILE = 'Companies.csv'
OUTPUT_FILE = 'potential_leads.csv'

MIN_MARKET_CAP_USD = 50_000_000  # $50 Million
MAX_MARKET_CAP_USD = 100_000_000 # $100 Million

# Define keywords for seniority ranking (higher score = more senior)
# This is a heuristic approach and might need tuning based on observed titles
SENIORITY_KEYWORDS = {
    'ceo': 100, 'chief executive officer': 100,
    'cto': 95, 'chief technology officer': 95,
    'cfo': 95, 'chief financial officer': 95,
    'coo': 95, 'chief operating officer': 95,
    'cio': 95, 'chief information officer': 95,
    'cmo': 95, 'chief marketing officer': 95,
    'chief': 90, # General 'Chief X Officer'
    'president': 85,
    'founder': 85,
    'partner': 80,
    'vp': 75, 'vice president': 75,
    'evp': 78, 'executive vice president': 78,
    'svp': 76, 'senior vice president': 76,
    'principal': 70,
    'head': 65,
    'director': 60,
    'manager': 40,
    'lead': 30,
    'board member': 100,
    'investor': 100
    # Add more keywords and adjust scores as needed
}
# Lower score for potentially less senior roles containing senior keywords
NEGATIVE_KEYWORDS = {
    'assistant to': -20,
    'intern': -50,
    'former': -100, # Exclude former employees
    'ex-': -100,
}


FUZZY_MATCH_THRESHOLD = 100 # Minimum score (out of 100) for company name match
MIN_SENIORITY_SCORE = 60   # Minimum score required to include contact (e.g., 60 = Director level and above)

# --- Helper Functions ---

def clean_market_cap(value):
    """Converts market cap strings (e.g., '$55.3M', '98B') to numeric USD."""
    if pd.isna(value):
        return None
    value = str(value).strip().upper().replace('$', '').replace(',', '')
    if 'B' in value:
        num = value.replace('B', '')
        try:
            return float(num) * 1_000_000_000
        except ValueError:
            return None
    elif 'M' in value:
        num = value.replace('M', '')
        try:
            return float(num) * 1_000_000
        except ValueError:
            return None
    try:
        # Assume it's already in dollars if no M or B
        return float(value)
    except ValueError:
        return None

def preprocess_company_name(name):
    """Cleans company names for better fuzzy matching."""
    if pd.isna(name):
        return ""
    name = str(name).lower()
    # Remove common suffixes
    name = re.sub(r'\b(inc|llc|ltd|corp|corporation|plc|gmbh|ag|co)\b\.?$', '', name).strip()
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def assign_seniority_score(title):
    """Assigns a score based on keywords in the job title."""
    if pd.isna(title):
        return 0
    
    title_lower = title.lower()
    score = 0
    
    # Check for negative keywords first
    for keyword, penalty in NEGATIVE_KEYWORDS.items():
        if keyword in title_lower:
            score += penalty # Apply penalty

    # Find the highest score from positive keywords
    highest_positive_score = 0
    for keyword, value in SENIORITY_KEYWORDS.items():
        # Use word boundaries to avoid partial matches (e.g., 'manager' in 'account manager')
        if re.search(r'\b' + re.escape(keyword) + r'\b', title_lower):
            highest_positive_score = max(highest_positive_score, value)

    # Only add positive score if not strongly negated (e.g., 'former ceo')
    if score > -50: # Allow minor penalties like 'assistant to'
         score += highest_positive_score
    
    # Ensure score is not negative unless strongly negated
    return max(score, 0) if score >= -50 else score


# --- Main Script ---

print("Starting lead generation process...")

# 1. Load Data
try:
    print(f"Loading LinkedIn connections from {LINKEDIN_FILE}...")
    df_linkedin = pd.read_csv(LINKEDIN_FILE)
    print(f"Loaded {len(df_linkedin)} connections.")
except FileNotFoundError:
    print(f"Error: LinkedIn file not found at {LINKEDIN_FILE}")
    exit()
except Exception as e:
    print(f"Error loading LinkedIn file: {e}")
    exit()

try:
    print(f"Loading company data from {COMPANIES_FILE}...")
    df_companies = pd.read_csv(COMPANIES_FILE)
    print(f"Loaded {len(df_companies)} companies.")
except FileNotFoundError:
    print(f"Error: Companies file not found at {COMPANIES_FILE}")
    exit()
except Exception as e:
    print(f"Error loading Companies file: {e}")
    exit()

# 2. Clean and Filter Companies by Market Cap
print("Cleaning and filtering company data by market cap...")
# Ensure required columns exist
required_company_cols = ['Company Name', 'Market Capitalization']
if not all(col in df_companies.columns for col in required_company_cols):
    print(f"Error: Companies file must contain columns: {required_company_cols}")
    exit()

df_companies['Market Cap (USD)'] = df_companies['Market Capitalization'].apply(clean_market_cap)
df_companies_filtered = df_companies[
    (df_companies['Market Cap (USD)'] >= MIN_MARKET_CAP_USD) &
    (df_companies['Market Cap (USD)'] <= MAX_MARKET_CAP_USD)
].copy() # Use .copy() to avoid SettingWithCopyWarning

if df_companies_filtered.empty:
    print("No companies found within the specified market cap range.")
    exit()

print(f"Found {len(df_companies_filtered)} companies in the target market cap range.")

# Prepare target company names for matching
df_companies_filtered['Clean Company Name'] = df_companies_filtered['Company Name'].apply(preprocess_company_name)
target_company_names = df_companies_filtered['Clean Company Name'].tolist()
target_company_map = df_companies_filtered.set_index('Clean Company Name')['Company Name'].to_dict() # Map clean name back to original
market_cap_map = df_companies_filtered.set_index('Clean Company Name')['Market Cap (USD)'].to_dict()


# 3. Match LinkedIn Connections to Target Companies
print("Matching LinkedIn connections to target companies (this may take a moment)...")
# Ensure required LinkedIn columns exist
required_linkedin_cols = ['Company', 'Position', 'First Name', 'Last Name']
if not all(col in df_linkedin.columns for col in required_linkedin_cols):
    print(f"Error: LinkedIn file must contain columns: {required_linkedin_cols}")
    exit()

matched_connections = []
df_linkedin['Clean Company'] = df_linkedin['Company'].apply(preprocess_company_name)

# Create a cache for fuzzy matching results to speed up
fuzzy_match_cache = {}

for index, row in df_linkedin.iterrows():
    if not row['Clean Company']:
        continue

    # Check cache first
    if row['Clean Company'] in fuzzy_match_cache:
         best_match, score = fuzzy_match_cache[row['Clean Company']]
    else:
        # Find the best fuzzy match among target companies
        match_result = process.extractOne(
            row['Clean Company'],
            target_company_names,
            scorer=fuzz.token_sort_ratio # Good for matching names with different word order
        )
        if match_result:
            best_match, score = match_result
            fuzzy_match_cache[row['Clean Company']] = (best_match, score) # Store in cache
        else:
            best_match, score = None, 0
            fuzzy_match_cache[row['Clean Company']] = (None, 0) # Cache miss


    if best_match and score >= FUZZY_MATCH_THRESHOLD:
        connection_data = row.to_dict()
        connection_data['Matched Company Name'] = target_company_map[best_match] # Get original name
        connection_data['Matched Market Cap (USD)'] = market_cap_map[best_match]
        connection_data['Match Score'] = score
        matched_connections.append(connection_data)

if not matched_connections:
    print("No connections found working at companies in the target market cap range after matching.")
    exit()

df_matched = pd.DataFrame(matched_connections)
print(f"Found {len(df_matched)} potential connections after company matching.")

# 4. Rank Seniority
print("Ranking connections by seniority based on job titles...")
df_matched['Seniority Score'] = df_matched['Position'].apply(assign_seniority_score)

# Filter out potentially former employees or very low ranks if score is negative
df_matched = df_matched[df_matched['Seniority Score'] >= 0]

if df_matched.empty:
    print("No suitable connections found after seniority scoring.")
    exit()

# 5. Filter Connections by Minimum Seniority Threshold
print(f"Filtering connections to include only those with seniority score >= {MIN_SENIORITY_SCORE}...")
# Sort by company and then descending seniority score for organized output
df_matched_sorted = df_matched.sort_values(by=['Matched Company Name', 'Seniority Score'], ascending=[True, False])

# *** MODIFIED LOGIC HERE ***
# Filter connections based on the minimum seniority score threshold
df_potential_contacts = df_matched_sorted[df_matched_sorted['Seniority Score'] >= MIN_SENIORITY_SCORE].copy()

if df_potential_contacts.empty:
    print(f"No connections found meeting the minimum seniority score of {MIN_SENIORITY_SCORE}.")
    exit()

print(f"Identified {len(df_potential_contacts)} contacts meeting the seniority threshold.")

# 6. Prepare and Save Output
print(f"Preparing final list and saving to {OUTPUT_FILE}...")
# Select and order columns for the final output
output_columns = [
    'First Name',
    'Last Name',
    'Position',
    'Seniority Score',
    'Company', # Original company name from LinkedIn
    'Matched Company Name', # Official matched company name
    'Matched Market Cap (USD)',
    'URL', # LinkedIn Profile URL
    'Email Address',
    'Connected On'
]
# Ensure all desired output columns exist in the dataframe, add missing ones with None
for col in output_columns:
    if col not in df_potential_contacts.columns:
        df_potential_contacts[col] = None

df_final_output = df_potential_contacts[output_columns] # Already sorted by company and score


# Format Market Cap for readability
df_final_output['Matched Market Cap (USD)'] = df_final_output['Matched Market Cap (USD)'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else 'N/A')


try:
    df_final_output.to_csv(OUTPUT_FILE, index=False)
    print(f"Successfully saved potential leads to {OUTPUT_FILE}")
    # Display the first few results
    print("\n--- Top Potential Leads ---")
    print(df_final_output.head().to_string())
    print("---------------------------\n")

except Exception as e:
    print(f"Error saving output file: {e}")

print("Script finished.")
