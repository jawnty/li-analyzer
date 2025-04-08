# LinkedIn Lead Generation Script

## Overview

This Python script helps identify potential leads for AI consulting services from your 1st-degree LinkedIn network. It filters connections based on the market capitalization of the companies they work for and their estimated seniority level within those companies.

The script processes two CSV files: one with your LinkedIn connections and another with public company data. It uses fuzzy matching to link connections to companies and a keyword-based scoring system to estimate seniority.

## Requirements

* **Python:** Version 3.7+ recommended.
* **Libraries:** Install the necessary Python libraries using pip:
    ```bash
    pip install pandas python-Levenshtein thefuzz
    ```
    *(Note: `python-Levenshtein` improves the speed of `thefuzz`)*
* **Input Files:**
    1.  `LinkedIn.csv`: Contains your 1st-degree LinkedIn connections. Must include columns: `First Name`, `Last Name`, `URL`, `Email Address`, `Company`, `Position`, `Connected On`.
    2.  `Companies.csv`: Contains data on US public companies. Must include columns: `Company Name`, `Market Capitalization`, `Sector`, `Industry`, `Sub-Industry`, `Company Headquarters Location`, `Revenue (TTM)`, `Employees (Full Time)`.

## Configuration

You can adjust the script's behavior by modifying the configuration variables near the top of the Python file (e.g., `find_leads.py`):

* `LINKEDIN_FILE`: Path to your LinkedIn connections CSV.
* `COMPANIES_FILE`: Path to the public companies CSV.
* `OUTPUT_FILE`: Name of the resulting CSV file containing potential leads.
* `MIN_MARKET_CAP_USD`, `MAX_MARKET_CAP_USD`: The target market capitalization range for companies (in USD).
* `SENIORITY_KEYWORDS`, `NEGATIVE_KEYWORDS`: Dictionaries defining keywords and scores used to estimate job title seniority. Feel free to tune these based on your observations.
* `FUZZY_MATCH_THRESHOLD`: The minimum confidence score (0-100) required for a fuzzy match between company names.
* `MIN_SENIORITY_SCORE`: The minimum seniority score a contact must have to be included in the output list.

## Usage

1.  **Prepare Data:** Ensure your `LinkedIn.csv` and `Companies.csv` files are correctly formatted and placed in the same directory as the script, or update the file paths in the configuration section.
2.  **Configure (Optional):** Modify the configuration variables within the script if needed (e.g., change market cap range, seniority threshold).
3.  **Run Script:** Open a terminal or command prompt, navigate to the directory containing the script and CSV files, and run:
    ```bash
    python your_script_name.py
    ```
    (Replace `your_script_name.py` with the actual filename you saved the script as, e.g., `find_leads.py`).
4.  **Check Output:** The script will print progress messages and save the results to the specified `OUTPUT_FILE` (default: `potential_leads_multiple.csv`).

## Output

The script generates a CSV file (e.g., `potential_leads_multiple.csv`) containing the filtered list of potential contacts. The columns include:

* First Name, Last Name
* Position (Job Title)
* Seniority Score (Estimated)
* Company (Name from LinkedIn profile)
* Matched Company Name (Official name from Companies list)
* Matched Market Cap (USD)
* URL (LinkedIn Profile)
* Email Address
* Connected On

The list is sorted by the matched company name and then by seniority score (highest first).

## Notes & Limitations

* **Seniority Scoring:** The seniority score is based on keywords in job titles and is a heuristic estimate. It may not perfectly reflect actual decision-making power. Tuning the `SENIORITY_KEYWORDS` dictionary might be necessary.
* **Company Matching:** Fuzzy matching helps link variations in company names but isn't foolproof. Review the `Match Score` (if added to output) or the `Matched Company Name` column for accuracy.
* **Data Quality:** The accuracy of the results depends heavily on the quality and completeness of the input CSV files.
# li-analyzer
LinkedIn analyzer
