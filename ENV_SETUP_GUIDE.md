# Environment Setup Guide

Complete step-by-step instructions for setting up your `.env` file with all required API keys.

## Quick Summary

You need:
1. **ANTHROPIC_API_KEY** (Required) - For Claude LLM
2. **NOTION_API_KEY** (Optional) - For Notion sync
3. **NOTION_DATABASE_ID** (Optional) - Your Notion database ID

## Part 1: Anthropic API Key (Required)

### Step 1: Create Anthropic Account

1. Go to https://console.anthropic.com/
2. Click "Sign Up" if you don't have an account
3. Complete email verification
4. Set up your account

### Step 2: Create API Key

1. After logging in, you'll see the console dashboard
2. In the left sidebar, click **"API Keys"**
3. You should see a button that says **"Create Key"**
4. Click it
5. Give it a name (e.g., "Wiki RAG System")
6. Click "Create"

### Step 3: Copy Your Key

1. You'll see your new key displayed (it starts with `sk-ant-`)
2. **Copy the entire key** (click the copy button or select all)
3. Keep it safe - don't share it!

### Step 4: Add to .env

1. Open the `.env` file in your editor:
   ```bash
   nano .env
   # or use your favorite editor
   ```

2. Find this line:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
   ```

3. Replace `sk-ant-your-actual-api-key-here` with your actual key:
   ```
   ANTHROPIC_API_KEY=sk-ant-abc123xyz789...
   ```

4. Save the file (Ctrl+O, Enter, Ctrl+X if using nano)

### Step 5: Test It

```bash
docker compose up -d
docker logs rag-backend | grep -i "anthropic\|success"
```

You should see no errors about the API key.

## Part 2: Notion Integration (Optional)

Only do this if you have a Notion technology watch database and want to sync it.

### Step 1: Create Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **"Create new integration"**
3. In the dialog:
   - **Name**: "Wiki RAG System" (or whatever you prefer)
   - **Logo**: Leave blank or choose one
   - **Associated workspace**: Select your workspace
4. Accept the terms
5. Click **"Create integration"**

### Step 2: Get Your Integration Token

1. After creating, you'll see a page with your integration details
2. Look for **"Internal Integration Token"**
3. Click the **copy** button next to it
4. The token starts with `ntn_`
5. Keep it secret!

### Step 3: Share Your Database with the Integration

1. Open your technology watch database in Notion
2. Click the **three dots (...)** in the top-right corner
3. Click **"Connections"**
4. You should see your integration listed
5. Click it to connect (it might show as a dropdown)
6. Confirm the connection

### Step 4: Find Your Database ID

1. Keep your Notion database open
2. Look at the **URL in your browser's address bar**:
   ```
   https://notion.so/user/abc123def456ghi789/...
                      ^^^^^^^^^^^^^^^^^^^^
                   This is your Database ID
   ```

3. Copy the database ID (the long alphanumeric string)
4. It should be between `/user/` and the next `/` or `?`

**Example:**
- If URL is: `https://notion.so/user/12ab34cd56ef78gh90ij?v=...`
- Your Database ID is: `12ab34cd56ef78gh90ij`

### Step 5: Add to .env

1. Open your `.env` file
2. Find these lines:
   ```
   NOTION_API_KEY=ntn_your-actual-notion-token-here
   NOTION_DATABASE_ID=your-database-id-here
   ```

3. Replace with your actual values:
   ```
   NOTION_API_KEY=ntn_abc123xyz789...
   NOTION_DATABASE_ID=12ab34cd56ef78gh90ij
   ```

4. Save the file

### Step 6: Test It

```bash
docker exec wiki-cli python scripts/notion-sync.py --status
```

You should see sync status information.

## Notion Database Setup

For the integration to work, your Notion database should have these columns:

| Column Name | Type | Purpose |
|------------|------|---------|
| Name | Title | Item name |
| Description | Rich Text | What it is |
| Category | Select | Framework, Tool, Library, etc. |
| URL | URL | Link to the resource |
| Date Discovered | Date | When you found it |
| Status | Select | New, Evaluating, Adopted, Rejected |

Optional columns (useful but not required):
- Tags (Multi-select) - Topic tags
- Priority (Select) - High, Medium, Low
- Notes (Rich Text) - Your observations

The system will work with different column names, but you may need to adjust the field mapping in `config/wiki_schema.yaml` if they're very different.

## Verification Checklist

After setting up .env:

- [ ] ANTHROPIC_API_KEY is set and starts with `sk-ant-`
- [ ] .env file is saved
- [ ] For Notion (optional):
  - [ ] NOTION_API_KEY is set and starts with `ntn_`
  - [ ] NOTION_DATABASE_ID is set
  - [ ] Integration is connected to your database

## Troubleshooting

### "Invalid API key" Error

- **Problem**: Key doesn't work
- **Solution**:
  1. Copy the key again from https://console.anthropic.com/
  2. Make sure you copied the entire key (no spaces before/after)
  3. Check you're using the right API key (not the user ID)

### "Notion API error" or "Database not found"

- **Problem**: Notion sync not working
- **Solution**:
  1. Verify the integration token starts with `ntn_`
  2. Go to https://www.notion.so/my-integrations and check the token
  3. Verify your database ID has no spaces or extra characters
  4. Make sure the integration is shared with the database (check "Connections")

### "Cannot read file" when starting

- **Problem**: .env file not found or not in right place
- **Solution**:
  1. Make sure you're in the project directory: `cd obsidian-wiki-llm`
  2. Verify .env exists: `ls -la .env`
  3. The file should be in the root of the project, same level as docker compose.yml

### "docker: command not found"

- **Problem**: Docker not installed
- **Solution**:
  1. Install Docker: https://docs.docker.com/install/
  2. Install Docker Compose: https://docs.docker.com/compose/install/
  3. Verify: `docker --version && docker compose --version`

## Cost Estimation

### Anthropic (Claude)

- **Input tokens**: $0.003 per 1K tokens
- **Output tokens**: $0.015 per 1K tokens

**Typical usage:**
- 1 document ingestion (2000 words): ~0.01-0.02
- 1 query: ~0.01-0.03
- Monthly (50 ingestings + 100 queries): ~$2-5

**Notion:**
- Free (no API charges)

## Security Best Practices

1. **Never commit .env to git**
   - It's already in .gitignore
   - But double-check with `git status` before committing

2. **Keep keys secret**
   - Don't share them in emails or chat
   - Don't paste them in screenshots
   - If exposed, create a new key immediately

3. **Rotate keys periodically**
   - Every 3-6 months is good practice
   - Go to https://console.anthropic.com/ to create new keys
   - Delete old keys after testing new ones

4. **Use environment variables**
   - The system uses .env for this
   - This keeps secrets out of code

## Next Steps

After setting up .env:

1. **Start the system**:
   ```bash
   make setup && make start
   ```

2. **Check if everything works**:
   ```bash
   make test
   ```

3. **Browse Obsidian**:
   ```bash
   open http://localhost:8080
   ```

4. **Add your first document**:
   ```bash
   make ingest FILE=raw_sources/example.md
   ```

5. **Query the wiki**:
   ```bash
   make query Q="Your question here"
   ```

## Getting Help

If you get stuck:

1. Check the log output: `docker logs rag-backend`
2. Verify .env syntax (no spaces around `=`)
3. Make sure API keys are copied correctly (no extra spaces)
4. Check API limits:
   - Anthropic: https://console.anthropic.com/
   - Notion: https://www.notion.so/my-integrations

## Additional Resources

- **Anthropic Documentation**: https://docs.anthropic.com/
- **Notion API Documentation**: https://developers.notion.com/
- **Project README**: README.md
- **System Architecture**: ARCHITECTURE.md

---

You're all set! Your system should be ready to use after completing these steps.
