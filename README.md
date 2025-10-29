# Notion \<\> Google Sheets Sync

A powerful Python script to sync data between Notion databases and Google Sheets. This tool supports one-way and two-way synchronization, preserves formulas in Google Sheets, and can be scheduled to run automatically.

-----

## ✨ Features

  * **Bi-directional Sync**: Set Notion or Google Sheets as the "source of truth".
  * **Calculator Mode**: Use Google Sheets as a powerful calculation engine for your Notion data.
  * **Multi-Sync Support**: Sync multiple sheets to multiple databases in a single run.
  * **Advanced Column Mapping**: Use a dedicated `ID` column for reliable updates and use a `[replace]` suffix to have one sheet column update a different Notion column.
  * **Rich Data Support**: Syncs a wide range of Notion property types, including `text`, `number`, `select`, `checkbox`, `formula`, `rollup`, and `relation` (fetches related page titles).
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
git clone https://github.com/JinRecords/Notion-Google-Sheet-Sync.git
cd Notion-Google-Sheet-Sync

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
  "SAMPLE_SPREADSHEET_ID": "your-google-sheet-id-here",
  "NOTION_INTEGRATION_TOKEN": "your-internal-integration-secret-here",
  "SYNC_PAIRS": [
    {
      "RANGE": "Sheet1!A:E",
      "DATABASE_ID": "your-first-notion-database-id-here",
      "PRIORITY": "sheet",
      "NAME": "Example One-Way Sync"
    },
    {
      "RANGE": "Sheet2!A:C",
      "DATABASE_ID": "your-second-notion-database-id-here",
      "PRIORITY": "calculator",
      "NAME": "Daily Calculator Job",
      "REPEAT": true,
      "INTERVAL": "day",
      "REPEAT_DAY": "09:00"
    }
  ]
}
```

| Key | Description |
| :--- | :--- |
| `SAMPLE_SPREADSHEET_ID` | The ID of your Google Sheet. |
| `NOTION_INTEGRATION_TOKEN` | Your Internal Integration Secret from Notion. |
| `SYNC_PAIRS` | A list of sync jobs to perform. You can add as many as you need. Each job is an object with its own properties. |

### Sync Pair Properties

| Key | Description |
| :--- | :--- |
| `NAME` | (Optional) A human-readable name for the sync job, which will be used in console logs. |
| `RANGE` | The sheet name and columns to sync (e.g., `Sheet1!A:E`). |
| `DATABASE_ID` | The ID of the corresponding Notion database. |
| `PRIORITY` | The sync direction. Can be `'sheet'`, `'notion'`, or `'calculator'`.<br>  • **`'sheet'`**: One-way sync from Google Sheets to Notion.<br>  • **`'notion'`**: Two-way sync. Data flows from Notion to Sheets, waits 1 second, then flows back from Sheets to Notion.<br>  • **`'calculator'`**: An advanced two-way sync that uses the sheet for calculations. See Advanced Usage section for details. |

### Scheduling Properties (Optional, per Sync Pair)

Add these keys inside a `SYNC_PAIRS` object to enable automatic scheduling for that specific sync job.

| Key | Description & Format |
| :--- | :--- |
| `REPEAT` | A boolean (`true` or `false`). Set to `true` to enable scheduling for this sync pair. |
| `INTERVAL` | The frequency of the sync. Can be `"hour"`, `"day"`, `"week"`, `"month"`, or `"year"`. |
| `REPEAT_HOUR` | Required if `INTERVAL` is `"hour"`. The minute of the hour to run the sync. <br> • **Format**: `"MM"` (e.g., `"30"` to run at `xx:30`). |
| `REPEAT_DAY` | Required if `INTERVAL` is `"day"`. The time of day to run the sync (in 24-hour format). <br> • **Format**: `"HH:MM"` (e.g., `"18:01"`). |
| `REPEAT_WEEK` | Required if `INTERVAL` is `"week"`. The time and day of the week to run. <br> • **Format**: `"HH:MM-DayName"` (e.g., `"00:01-Monday"`). |
| `REPEAT_MONTH` | Required if `INTERVAL` is `"month"`. The time and day of the month to run. If the specified day is greater than the number of days in the current month (e.g., `31` in February), the job will run on the last day of that month. <br> • **Format**: `"HH:MM-DD"` (e.g., `"00:01-1"` for the 1st of the month). |
| `REPEAT_YEAR` | Required if `INTERVAL` is `"year"`. The time, day, and month to run. <br> • **Format**: `"HH:MM-DD-MM"` (e.g., `"00:01-31-12"` for Dec 31st). |


-----

## 🔧 Advanced Usage

Beyond the basic setup, this script offers powerful features for more complex workflows.

### Calculator Mode (`"PRIORITY": "calculator"`)

The `calculator` mode is designed for workflows where you want to use Google Sheets to perform calculations on your Notion data. It works as follows:

1.  **Notion to Sheet**: Data is first synced from Notion to your Google Sheet. Any formulas in your sheet are preserved. Any columns in your sheet with a header ending in ` [replace]` will be ignored during this step, preserving their current values or formulas.
2.  **Calculation Pause**: The script waits for 1 second to allow all Google Sheet formulas to recalculate based on the new data from Notion.
3.  **Sheet to Notion**: The updated data (including the results of your calculations) is synced back to the corresponding writable columns in your Notion database.

This allows you to, for example, have a Notion property that is calculated in a Google Sheet formula and then synced back to a different, writable Notion property.

### ID-Based Updates

By default, the script matches rows between Google Sheets and Notion using the **Title** property. This can be unreliable if titles change.

For a more robust sync, you can add a column named exactly **`ID`** to your Google Sheet (usually as the first column).

*   When data is synced from Notion to the sheet, this column will be automatically populated with the unique Notion Page ID.
*   When data is synced back to Notion, the script will use this `ID` to update the correct page, even if the title has changed. The script will only perform updates and will not create new pages when an `ID` column is present.

### Replacing Column Values (`[replace]` suffix)

You can have a column in your Google Sheet update a *different* column in Notion by adding ` [replace]` to the end of the header in your Google Sheet.

For example, if you have a header named `Calculated Value [replace]` in your sheet, the data from this column will be used to update the property named `Calculated Value` in Notion.

This is very useful in `calculator` mode. You can have a Notion property (e.g., `Source Number`), use it in a sheet formula, and have the result written to a different column in the sheet (e.g., `Calculated Number [replace]`). The script will then sync this result back to the `Calculated Number` property in Notion.

-----

## ▶️ Running the Script

Once your `config.json` is set up, run the script from your terminal:

```bash
python3 main.py
```

  * **First Run**: The first time you run the script, a browser window will open asking you to authorize access to your Google account. After you approve, a `token.pickle` file will be created so you don't have to log in every time.
  * **How it Runs**: The script will first run any sync pairs that are not configured to repeat. If there are any scheduled jobs (with `"REPEAT": "True"`), it will then enter a loop to check for and run those jobs at their configured times. 
  * **Stopping the Script**: You can stop the scheduler by pressing **`Ctrl+C`** in the terminal.

-----

## 🔧 Troubleshooting

| Error / Problem | Solution |
| :--- | :--- |
| **`FileNotFoundError: credentials.json`** | Make sure you have downloaded the credentials file from Google Cloud, renamed it to `credentials.json`, and placed it in the same folder as the script. |
| **`API token is invalid`** or **401 Error** | Your `NOTION_INTEGRATION_TOKEN` in `config.json` is incorrect. Go back to your Notion integration page, re-copy the secret, and paste it into the config file. |
| **Login fails or `access_denied` error** | This usually means the Google account you are trying to log in with is not listed as a "Test user" in your Google Cloud project's OAuth consent screen. See **Step 3.3**. |
| **Permission / 403 Errors** | 1.  **Google**: Ensure you have enabled the "Google Sheets API" in your Google Cloud project.  2.  **Notion**: Ensure you have shared your Notion database with your integration (Step 2.3). |
| **Columns are scrambled or missing** | This usually means the header names in your Google Sheet do **not exactly match** the property names in your Notion database. They are case-sensitive\! |
| **Script doesn't ask for Google login or fails with permission errors after working before** | A `token.pickle` file already exists with old permissions. **Delete the `token.pickle` file** and run the script again to re-authorize it. |
