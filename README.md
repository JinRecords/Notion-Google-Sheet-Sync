# Notion \<\> Google Sheets Sync

A powerful Python script to sync data between Notion databases and Google Sheets. This tool supports one-way and two-way synchronization, preserves formulas in Google Sheets, and can be scheduled to run automatically.

-----

## ✨ Features

  * **Bi-directional Sync**: Set Notion or Google Sheets as the "source of truth".
  * **Multi-Sync Support**: Sync multiple sheets to multiple databases in a single run.
  * **Dynamic Column Mapping**: Automatically matches columns based on the header row in Google Sheets.
  * **Formula Preservation**: Never overwrites your formulas in Google Sheets.
  * **Scheduled Execution**: Configure the script to run once or repeat at a set interval.
  * **Easy Configuration**: All settings are managed in a simple `config.json` file.

-----

## 🚀 Setup Instructions

Follow these steps to get the script up and running.

### Step 1: Install Requirements

First, clone this repository and navigate into the project directory. It's highly recommended to use a Python virtual environment.

```bash
# Clone the repository (replace with your URL)
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# Create and activate a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install the required Python packages
pip install -r requirements.txt
```

-----

### Step 2: Set up Notion Integration

To allow the script to access your Notion workspace, you need to create an integration.

1.  **Create an Integration**:

      * Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and click **"+ New integration"**.
      * Give it a name (e.g., "Google Sheets Sync") and submit.
      * On the next screen, copy the **"Internal Integration Secret"**. This is your Notion API token.

2.  **Get your Database ID**:

      * Open the Notion database you want to sync in your browser.
      * The URL will look like: `https://www.notion.so/your-workspace/`**`a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3`**`?v=...`
      * The **Database ID** is the 32-character string between the `/` and the `?`.

3.  **Share the Database with the Integration**:

      * Go to your Notion database page.
      * Click the **`•••`** menu in the top-right corner.
      * Click **"Add connections"** and select the integration you just created.

-----

### Step 3: Set up Google Cloud & Sheets API

To allow the script to access your Google Sheets, you need to enable the API and get credentials.

1.  **Enable the Google Sheets API**:

      * Go to the [Google Cloud Console](https://console.cloud.google.com/).
      * Create a new project or select an existing one.
      * In the search bar, find and enable the **"Google Sheets API"**.

2.  **Create Credentials**:

      * Go to the [Credentials page](https://console.cloud.google.com/apis/credentials) in the Google Cloud Console.
      * Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
      * If prompted, configure the "OAuth consent screen". For **User Type**, select **External** and fill in the required app name, user support email, and developer contact information.
      * For the **Application type**, select **Desktop app** and give it a name.
      * Click **Create**. A window will pop up. Click **DOWNLOAD JSON**.
      * **Rename the downloaded file to `credentials.json`** and place it in the same folder as the script.

3.  **Add Test Users (Crucial Step)**:

      * While your app is in "Testing" mode, only authorized users can log in. You must add your own Google account to this list.
      * Go back to the [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) in the Google Cloud Console.
      * Under the "Test users" section, click **+ ADD USERS**.
      * Enter the Google email address you'll use to authorize the script and click **Save**.

4.  **Get your Google Sheet ID**:

      * Open the Google Sheet you want to sync.
      * The URL will look like: `https://docs.google.com/spreadsheets/d/`**`1Txj0M39oI5VTNVtxQi3SN45BLe6yWY56JMC5pqoalAc`**`/edit...`
      * The **Sheet ID** is the long string of characters between `/d/` and `/edit`.

-----

## ⚙️ Configuration (`config.json`)

All script settings are controlled by the `config.json` file. Edit this file to match your setup.

```json
{
  "RUN_REPEATEDLY": false,
  "REPEAT_INTERVAL_MINUTES": 30,
  "SAMPLE_SPREADSHEET_ID": "your-google-sheet-id-here",
  "NOTION_INTEGRATION_TOKEN": "your-internal-integration-secret-here",
  "SYNC_PAIRS": [
    {
      "RANGE": "Sheet1!A:E",
      "DATABASE_ID": "your-first-notion-database-id-here",
      "PRIORITY": "sheet"
    },
    {
      "RANGE": "Sheet2!A:C",
      "DATABASE_ID": "your-second-notion-database-id-here",
      "PRIORITY": "notion"
    }
  ]
}
```

| Key | Description |
| :--- | :--- |
| `RUN_REPEATEDLY` | Set to `true` to run the script on a loop, or `false` to run it only once. |
| `REPEAT_INTERVAL_MINUTES` | If `RUN_REPEATEDLY` is `true`, this is the wait time in minutes between syncs. \<br\> **⚠️ Warning**: Setting a very short interval (e.g., less than 10-15 minutes) can result in a high volume of API requests to both Notion and Google. While both services have generous free tiers, excessive use may lead to rate limiting or potential charges. Please use a reasonable interval for your needs. |
| `SAMPLE_SPREADSHEET_ID` | The ID of your Google Sheet. |
| `NOTION_INTEGRATION_TOKEN` | Your Internal Integration Secret from Notion. |
| `SYNC_PAIRS` | A list of sync jobs to perform. You can add as many as you need. |
| `RANGE` | The sheet name and columns to sync (e.g., `Sheet1!A:E`). |
| `DATABASE_ID` | The ID of the corresponding Notion database. |
| `PRIORITY` | The sync direction. Can be `'sheet'` or `'notion'`. \<br\> • **`'sheet'`**: One-way sync from Google Sheets to Notion. \<br\> • **`'notion'`**: Two-way sync. Data flows from Notion to Sheets, waits 1 second for formulas to calculate, then flows back from Sheets to Notion. |

-----

## ▶️ Running the Script

Once your `config.json` is set up, run the script from your terminal:

```bash
python3 sync.py
```

  * **First Run**: The first time you run the script, a browser window will open asking you to authorize access to your Google account. After you approve, a `token.pickle` file will be created so you don't have to log in every time.
  * **Stopping the Script**: If the script is running in a loop (`RUN_REPEATEDLY` is `true`), you can stop it by pressing **`Ctrl+C`** in the terminal.

-----

## 🔧 Troubleshooting

| Error / Problem | Solution |
| :--- | :--- |
| **`FileNotFoundError: credentials.json`** | Make sure you have downloaded the credentials file from Google Cloud, renamed it to `credentials.json`, and placed it in the same folder as the script. |
| **`API token is invalid`** or **401 Error** | Your `NOTION_INTEGRATION_TOKEN` in `config.json` is incorrect. Go back to your Notion integration page, re-copy the secret, and paste it into the config file. |
| **Login fails or `access_denied` error** | This usually means the Google account you are trying to log in with is not listed as a "Test user" in your Google Cloud project's OAuth consent screen. See **Step 3.3**. |
| **Permission / 403 Errors** | 1.  **Google**: Ensure you have enabled the "Google Sheets API" in your Google Cloud project. \<br\> 2.  **Notion**: Ensure you have shared your Notion database with your integration (Step 2.3). |
| **Columns are scrambled or missing** | This usually means the header names in your Google Sheet do **not exactly match** the property names in your Notion database. They are case-sensitive\! |
| **Script doesn't ask for Google login or fails with permission errors after working before** | A `token.pickle` file already exists with old permissions. **Delete the `token.pickle` file** and run the script again to re-authorize it. |
