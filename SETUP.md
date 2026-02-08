# Setup Guide - AI Procurement Assistant

Complete setup guide to get the AI Procurement Assistant running on your local machine or in production.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Data Loading](#data-loading)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Application runtime |
| MongoDB | 4.4+ | Database |
| pip | Latest | Package management |
| Git | Any | Version control |

### Required API Keys

You need **at least one** of the following:

**Option 1: OpenAI (Recommended for beginners)**
- OpenAI API Key
- Get from: https://platform.openai.com/api-keys

**Option 2: Google Gemini**
- Gemini API Key (Developer)

**Option 3: Google Vertex AI (Advanced)**
- Google Cloud Project with Vertex AI enabled
- Service Account with necessary permissions

### Optional (for logging)
- Google Cloud Project for BigQuery logging
- Service Account with BigQuery permissions

---

## Quick Start

**For the impatient** - Get running in 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/msiddique1436/penny_assignment.git
cd penny_assignment

# 2. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your API key

# 5. Start MongoDB (if not running)
# macOS/Linux: mongod --dbpath ~/data/db
# Windows: "C:\Program Files\MongoDB\Server\X.X\bin\mongod.exe"

# 6. Run the app
streamlit run app.py

# 7. Open browser to http://localhost:8501
```

Now follow the UI to configure, load data, and start chatting!

---

## Detailed Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/msiddique1436/penny_assignment.git
cd penny_assignment
```

### Step 2: Set Up Python Environment

**Create virtual environment:**
```bash
python3.12 -m venv .venv
```

**Activate virtual environment:**

On macOS/Linux:
```bash
source .venv/bin/activate
```

On Windows:
```cmd
.venv\Scripts\activate
```

Your prompt should now show `(.venv)` prefix.

**Verify Python version:**
```bash
python --version
# Should show: Python 3.12.x
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Verify installation:**
```bash
pip list | grep streamlit
pip list | grep langchain
pip list | grep pymongo
```

### Step 4: Install MongoDB

**macOS (using Homebrew):**
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Ubuntu/Debian:**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

**Windows:**
1. Download: https://www.mongodb.com/try/download/community
2. Run installer
3. Choose "Complete" installation
4. Install MongoDB as a Service
5. Start MongoDB service from Services panel

**Docker (Alternative):**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:7.0
```

**Verify MongoDB is running:**
```bash
mongosh --eval "db.version()"
# Should show MongoDB version
```

### Step 5: Set Up Environment Variables

**Copy example file:**
```bash
cp .env.example .env
```

**Edit `.env` file:**
```bash
# Use your favorite editor
nano .env
# or
vim .env
# or
code .env  # VS Code
```

**Minimum required (choose ONE LLM provider):**

**Option A: OpenAI**
```bash
# .env file
OPENAI_API_KEY=sk-proj-...  # Your OpenAI API key
OPENAI_MODEL=gpt-4o-mini     # or gpt-4o, gpt-5

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=procurement_db
```

**Option B: Gemini**
```bash
# .env file
GOOGLE_API_KEY=AIza...       # Your Gemini API key
GEMINI_MODEL=gemini-2.0-flash-exp

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=procurement_db
```

**Option C: Vertex AI (Advanced)**
```bash
# .env file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
VERTEX_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
GEMINI_MODEL=gemini-3-pro-preview

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=procurement_db
```

**Optional - BigQuery Logging:**
```bash
# Add to .env if you want BigQuery logging
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

**Save and close the file.**

**Verify environment variables:**
```bash
# Check if variables are set
cat .env | grep API_KEY
```

---

## Configuration

### Step 1: Obtain Procurement Data

The application requires California procurement data (2012-2015).

**Option A: Use your own data**
- Place CSV file in `data/` folder
- Name it: `PURCHASE ORDER DATA EXTRACT 2012-2015_0.csv`

**Option B: Request sample data**
- Contact the project maintainer
- Or use publicly available California procurement data

**Expected CSV format:**
```csv
Purchase Order Number,Creation Date,Purchase Date,Fiscal Year,LPA Number,Purchase Type,...
P3000123456,07/15/2013,07/20/2013,2013-2014,LPA-12-0045,Goods,...
```

**Required columns:**
- Purchase Order Number
- Creation Date
- Purchase Date
- Fiscal Year
- Department Name
- Supplier Name
- Item Name
- Unit Price
- Total Price
- Quantity

### Step 2: Prepare Data Directory

```bash
mkdir -p data
# Place your CSV file in data/ folder
```

**Verify file:**
```bash
ls -lh data/*.csv
# Should show your CSV file
```

---

## Running the Application

### Start the Application

```bash
streamlit run app.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

**Open your browser to:** http://localhost:8501

### First-Time Setup Wizard

#### Page 1: Configuration

1. **Select LLM Provider**
   - Choose: "Gemini" or "OpenAI"

2. **Configure API Key**
   - If using OpenAI: Should auto-detect from `.env`
   - If using Gemini: Should auto-detect from `.env`
   - Or enter manually

3. **Select Model**
   - OpenAI: `gpt-4o-mini` (recommended for cost), `gpt-4o`, or `gpt-5`
   - Gemini: `gemini-2.0-flash-exp` or `gemini-3-pro-preview`

4. **Enable Logging (Optional)**
   - Check "Enable Chat Logging"
   - Choose destination:
     - **Local CSV**: Logs to `chat_logs.csv` (no setup needed)
     - **BigQuery**: Logs to GCP BigQuery (requires service account)
   - For BigQuery:
     - Check "Use Default Table" for `hudhud-demo.penny_demo.chat_logs`
     - Or specify custom project/dataset/table

5. **Test Connection**
   - Click "🧪 Test Connection"
   - Wait for success message
   - If successful, configuration is saved!

6. **Next**
   - Click "Next: Data Setup →"

#### Page 2: Data Setup

1. **MongoDB Connection**
   - Default URI should be pre-filled: `mongodb://localhost:27017/`
   - Click "Connect to MongoDB"
   - Wait for "✅ Connected successfully"

2. **Load Data**
   - Verify CSV path is shown: `data/PURCHASE ORDER DATA EXTRACT 2012-2015_0.csv`
   - Click "📥 Load Data to MongoDB"
   - **Wait patiently** - Loading 919,734 rows takes ~2-5 minutes
   - Progress bar will show status

3. **Verify Data**
   - Check statistics:
     - Total Documents: 919,734
     - Date Range: 2012-2015
     - Total Spending: ~$273B
     - Unique Suppliers: ~37K
     - Unique Departments: ~100

4. **Next**
   - Click "Next: Chat Assistant →"

#### Page 3: Chat Assistant

1. **Try Sample Queries**
   - Click any sample query button
   - Examples:
     - "How many total orders are in the database?"
     - "Which department spent the most money?"
     - "What does UNSPSC stand for?" (web search)

2. **Ask Your Own Questions**
   - Type in chat input box
   - Examples:
     - "What are the top 5 most expensive items?"
     - "How many orders in Q2 2013?"
     - "Which suppliers have the most contracts?"

3. **Observe Agentic Behavior**
   - Watch metrics: Iterations, Tools Used, Time
   - Expand "View Agent's Reasoning Process"
   - See which tools the agent chose

4. **Provide Feedback (if logging enabled)**
   - Click 👍 for good answers
   - Click 👎 for poor answers
   - Feedback is logged for analysis

---

## Data Loading

### Manual Data Load (Alternative)

If you prefer loading data manually via Python:

```python
from src.data_loader import load_procurement_data
from src.mongo_client import MongoDBClient

# Connect to MongoDB
mongo_client = MongoDBClient(
    uri="mongodb://localhost:27017/",
    db_name="procurement_db"
)
mongo_client.connect()

# Load data
csv_path = "data/PURCHASE ORDER DATA EXTRACT 2012-2015_0.csv"
stats = load_procurement_data(
    csv_file_path=csv_path,
    mongo_client=mongo_client,
    collection_name="procurement_orders",
    batch_size=1000
)

print(f"Loaded {stats['total_documents']} documents")
```

### Verify Data in MongoDB

```bash
# Open MongoDB shell
mongosh

# Switch to database
use procurement_db

# Check document count
db.procurement_orders.countDocuments()
# Should return: 919734

# Sample document
db.procurement_orders.findOne()

# Check indexes
db.procurement_orders.getIndexes()

# Exit
exit
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Kill process using port 8501
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run app.py --server.port 8502
```

#### 2. MongoDB Connection Failed

**Error:**
```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 61] Connection refused
```

**Solution:**
```bash
# Check if MongoDB is running
mongosh --eval "db.version()"

# If not running, start it:
# macOS/Linux:
brew services start mongodb-community
# or
sudo systemctl start mongod

# Windows:
# Start MongoDB service from Services panel
```

#### 3. API Key Not Found

**Error:**
```
OpenAI API key required
```

**Solution:**
```bash
# Verify .env file exists
ls -la .env

# Verify API key is set
cat .env | grep API_KEY

# Make sure .env is in project root (same folder as app.py)
pwd
ls -la

# Restart Streamlit after editing .env
```

#### 4. Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'langchain'
```

**Solution:**
```bash
# Verify virtual environment is activated
which python
# Should show: /path/to/.venv/bin/python

# If not activated:
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Data File Not Found

**Error:**
```
FileNotFoundError: data/PURCHASE ORDER DATA EXTRACT 2012-2015_0.csv
```

**Solution:**
```bash
# Verify file exists
ls -lh data/*.csv

# Verify filename matches exactly (case-sensitive)
# Check for spaces in filename

# If file is missing, obtain procurement data and place in data/ folder
```

#### 6. BigQuery Permission Denied

**Error:**
```
google.api_core.exceptions.PermissionDenied: 403 Permission denied on resource project
```

**Solution:**
```bash
# Verify service account has permissions:
# - BigQuery Data Editor
# - BigQuery Job User

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Or use gcloud auth
gcloud auth application-default login

# Fallback: Use local CSV logging instead
```

#### 7. Web Search Not Working

**Error:**
```
Web search error: No module named 'ddgs'
```

**Solution:**
```bash
# Install web search package
pip install ddgs>=9.10.0

# Verify installation
pip show ddgs
```

#### 8. Token Limit Exceeded

**Error:**
```
Error code: 400 - This model's maximum context length is 8192 tokens
```

**Solution:**
```
# This happens with very long conversations
# Solution: Clear chat history
# Click "🗑️ Clear Chat" button in the UI

# Or reduce max_tokens in config.py:
DEFAULT_MAX_TOKENS = 4096  # Instead of 8192
```

#### 9. Gemini API Key Type Issues

**Error:**
```
Invalid API key format
```

**Solution:**
```bash
# Gemini has multiple API key types:

# Developer API key (starts with "AIza"):
GOOGLE_API_KEY=AIzaSy...

# Vertex AI Express Mode key (starts with "AQ."):
GOOGLE_API_KEY=AQ.xxx...

# Service Account (JSON file):
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Pick ONE method and ensure it's set correctly
```

---

## Production Deployment

### Docker Deployment

**Create Dockerfile:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install MongoDB client (for data loading)
RUN apt-get update && apt-get install -y mongodb-clients && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Build and run:**

```bash
# Build image
docker build -t procurement-assistant .

# Run container
docker run -d \
  -p 8501:8501 \
  -e OPENAI_API_KEY=sk-xxx \
  -e MONGO_URI=mongodb://host.docker.internal:27017/ \
  --name procurement-app \
  procurement-assistant
```

### Cloud Run Deployment (GCP)

```bash
# 1. Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/procurement-assistant

# 2. Deploy to Cloud Run
gcloud run deploy procurement-assistant \
  --image gcr.io/PROJECT_ID/procurement-assistant \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars MONGO_URI=mongodb+srv://...,OPENAI_API_KEY=sk-xxx

# 3. Access at provided URL
```

### Environment Variables for Production

```bash
# Production .env
OPENAI_API_KEY=sk-proj-xxx
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DB_NAME=procurement_db

# BigQuery logging
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/sa-key.json

# Security
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
```

---

## Verification Checklist

After setup, verify everything works:

- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip list`)
- [ ] MongoDB running and accessible
- [ ] `.env` file configured with API key
- [ ] Streamlit app starts without errors
- [ ] Config page: LLM connection test passes
- [ ] Data Setup: CSV file found and loadable
- [ ] Data Setup: MongoDB receives all 919,734 rows
- [ ] Chat page: Sample queries work
- [ ] Chat page: Agent shows reasoning process
- [ ] Chat page: Web search queries work
- [ ] Logging: Logs appear in CSV or BigQuery (if enabled)
- [ ] Feedback: Thumbs up/down buttons work (if logging enabled)

---

## Getting Help

### Resources

- **Documentation**: See `TECHNICAL_ARCHITECTURE.md` for system details
- **Logging**: See `LOGGING_FEATURE.md` for logging setup
- **Issues**: https://github.com/msiddique1436/penny_assignment/issues

### Support

If you encounter issues:

1. Check [Troubleshooting](#troubleshooting) section above
2. Search existing GitHub issues
3. Create new issue with:
   - Error message (full traceback)
   - Steps to reproduce
   - Environment (OS, Python version, package versions)
   - Configuration (redact API keys!)

---

## Next Steps

Once setup is complete:

1. **Explore Sample Queries**: Try all sample queries to understand capabilities
2. **Read Documentation**: Review `TECHNICAL_ARCHITECTURE.md`
3. **Customize**: Modify prompts, add tools, adjust models
4. **Monitor Usage**: Check logs and token usage
5. **Optimize**: Tune parameters for your use case

---

## Quick Reference

### Common Commands

```bash
# Start app
streamlit run app.py

# Start app on different port
streamlit run app.py --server.port 8502

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate      # Windows

# Install/update dependencies
pip install -r requirements.txt

# Check MongoDB status
mongosh --eval "db.version()"

# View logs
tail -f chat_logs.csv
```

### Project Structure

```
AI_Assignment/
├── app.py                  # Main entry point
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Template
├── data/                   # Data files (not in git)
├── src/                    # Source code
│   ├── ai_agent_agentic.py      # Agentic AI
│   ├── llm_manager.py           # LLM abstraction
│   ├── mongo_client.py          # MongoDB client
│   ├── query_translator_langchain.py  # Query translation
│   ├── chat_logger.py           # Logging system
│   └── data_loader.py           # Data loading
├── pages/                  # Streamlit pages
│   ├── 1_Config.py
│   ├── 2_Data_Setup.py
│   └── 3_Chat_Assistant.py
├── prompts/                # System prompts
└── tests/                  # Test files
```

### Default Ports

- Streamlit: `8501`
- MongoDB: `27017`

---

**You're all set! 🎉**

Start the app with `streamlit run app.py` and begin exploring California procurement data with AI! 🚀
