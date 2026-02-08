# Technical Architecture & Design Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Agentic Design Pattern](#agentic-design-pattern)
4. [Code Flow & Execution](#code-flow--execution)
5. [Data Architecture](#data-architecture)
6. [LLM Integration](#llm-integration)
7. [Tool System](#tool-system)
8. [Logging & Observability](#logging--observability)
9. [Deployment Diagram](#deployment-diagram)

---

## System Overview

### Purpose
AI-Powered Procurement Assistant that translates natural language questions into MongoDB queries and provides intelligent responses about California state procurement data (919,734 records, 2012-2015).

### Key Characteristics
- **Agentic AI**: Uses ReAct (Reasoning + Acting) loop for autonomous decision-making
- **Multi-LLM Support**: Works with both Google Gemini and OpenAI GPT models
- **Hybrid Search**: Combines database queries with web search
- **Observable**: Comprehensive logging with token tracking and user feedback
- **Iterative**: Agent can retry queries if results appear incorrect

### Technology Stack
```
Frontend:     Streamlit (Multi-page web UI)
Backend:      Python 3.12
AI Framework: LangChain (Tool calling, message handling)
LLM Providers: Google Gemini API, OpenAI API
Database:     MongoDB (Document store)
Logging:      BigQuery / Local CSV
Search:       DuckDuckGo (via ddgs library)
```

---

## Architecture Components

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│                        (Streamlit Pages)                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   1_Config.py   │ 2_Data_Setup.py │   3_Chat_Assistant.py       │
│  - LLM Setup    │  - MongoDB      │   - Chat Interface          │
│  - Logging      │  - Data Load    │   - Feedback UI             │
└────────┬────────┴────────┬────────┴──────────┬──────────────────┘
         │                 │                   │
         └─────────────────┴───────────────────┘
                           │
         ┌─────────────────┴──────────────────┐
         │      Session State Manager         │
         │  - llm_manager                     │
         │  - mongo_client                    │
         │  - agent                           │
         │  - chat_logger                     │
         │  - messages                        │
         └─────────────────┬──────────────────┘
                           │
         ┌─────────────────┴──────────────────┐
         │     AGENTIC AI CORE                │
         │  (AgenticProcurementAgent)         │
         │                                    │
         │  ┌──────────────────────────┐     │
         │  │  ReAct Loop Engine       │     │
         │  │  - Reasoning             │     │
         │  │  - Tool Selection        │     │
         │  │  - Observation           │     │
         │  │  - Retry Logic           │     │
         │  └──────────┬───────────────┘     │
         │             │                      │
         │  ┌──────────┴───────────────┐     │
         │  │   Tool Registry          │     │
         │  ├──────────────────────────┤     │
         │  │ 1. get_collection_schema │     │
         │  │ 2. translate_query       │     │
         │  │ 3. execute_mongodb_query │     │
         │  │ 4. search_web            │     │
         │  └──────────┬───────────────┘     │
         └─────────────┼──────────────────────┘
                       │
         ┌─────────────┴──────────────────┐
         │                                │
    ┌────▼────┐  ┌──────────┐  ┌────────▼────┐
    │   LLM   │  │ MongoDB  │  │  Web Search │
    │ Manager │  │  Client  │  │   (DDGS)    │
    └─────┬───┘  └────┬─────┘  └──────┬──────┘
          │           │                │
    ┌─────▼─────┐ ┌──▼──────────┐ ┌───▼───────┐
    │  Gemini   │ │  MongoDB    │ │ DuckDuck  │
    │    API    │ │   Server    │ │  Go API   │
    └───────────┘ └─────────────┘ └───────────┘
```

### Component Breakdown

#### 1. **User Interface Layer** (`pages/`)
- **1_Config.py**: LLM configuration, logging setup
- **2_Data_Setup.py**: MongoDB connection, data loading
- **3_Chat_Assistant.py**: Main chat interface with feedback

#### 2. **Agent Layer** (`src/ai_agent_agentic.py`)
- **AgenticProcurementAgent**: Core agentic AI
- **ReAct Loop**: Iterative reasoning and acting
- **Tool Management**: Dynamic tool calling

#### 3. **LLM Layer** (`src/llm_manager.py`)
- **LLMManagerV2**: Abstraction over Gemini/OpenAI
- **Unified Interface**: Single API for both providers
- **Token Tracking**: Automatic usage monitoring

#### 4. **Database Layer** (`src/mongo_client.py`)
- **MongoDBClient**: Connection management
- **Query Execution**: Find and aggregate operations
- **Schema Inspection**: Dynamic field discovery

#### 5. **Translation Layer** (`src/query_translator_langchain.py`)
- **QueryTranslator**: Natural language to MongoDB
- **Few-Shot Learning**: Example-based translation
- **Schema-Aware**: Uses database structure

#### 6. **Logging Layer** (`src/chat_logger.py`)
- **ChatLogger**: Multi-destination logging
- **BigQuery Integration**: Structured logging
- **CSV Fallback**: Local file backup

---

## Agentic Design Pattern

### What Makes It "Agentic"?

Traditional chatbots follow a **fixed pipeline**:
```
User Query → Query Translation → Database Execution → Response
```

Our agentic system uses a **dynamic ReAct loop**:
```
User Query → [REASON → ACT → OBSERVE → DECIDE] → Response
              └──────────── Loop ────────────┘
```

### ReAct Loop Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       ReAct Loop                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. REASON (Think)                                   │   │
│  │    LLM analyzes situation and decides next action   │   │
│  │    Output: Thought + Tool Selection                 │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │ 2. ACT (Execute)                                    │   │
│  │    Call selected tool with arguments                │   │
│  │    Options:                                         │   │
│  │    - get_collection_schema()                        │   │
│  │    - translate_query(question)                      │   │
│  │    - execute_mongodb_query(query_json)              │   │
│  │    - search_web(query)                              │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │ 3. OBSERVE (Analyze)                                │   │
│  │    Examine tool output                              │   │
│  │    Check for errors or unexpected results           │   │
│  │    Add observation to conversation history          │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │ 4. DECIDE (Next Step)                               │   │
│  │    ┌──────────────────────────────────┐             │   │
│  │    │ Have enough info?                │             │   │
│  │    └────┬──────────────────────┬───────┘             │   │
│  │         │ YES                  │ NO                  │   │
│  │    ┌────▼────┐          ┌──────▼──────┐             │   │
│  │    │ Respond │          │ Loop Again  │             │   │
│  │    │  to User│          │ (Iteration++)            │   │
│  │    └─────────┘          └──────┬──────┘             │   │
│  │                                │                     │   │
│  └────────────────────────────────┼─────────────────────┘   │
│                                   │                         │
│                          ┌────────▼────────┐                │
│                          │  Max Iterations │                │
│                          │   Reached (8)?  │                │
│                          └────┬───────┬────┘                │
│                               │ YES   │ NO                  │
│                          ┌────▼────┐  │                     │
│                          │  Exit   │  │                     │
│                          │ w/Error │  │                     │
│                          └─────────┘  │                     │
│                                       │                     │
│                          ┌────────────▼───────────┐         │
│                          │   Continue Loop        │         │
│                          │   (Back to REASON)     │         │
│                          └────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Key Agentic Capabilities

#### 1. **Autonomous Tool Selection**
The agent decides which tools to use based on the question:

```python
# Example decision process:
Question: "Which department spent the most?"

Iteration 1: REASON → "Need schema to know field names"
            ACT → get_collection_schema()
            OBSERVE → "Field is 'department_name'"

Iteration 2: REASON → "Now translate to aggregation query"
            ACT → translate_query("Which department spent most?")
            OBSERVE → "Got aggregation pipeline"

Iteration 3: REASON → "Execute the query"
            ACT → execute_mongodb_query(pipeline)
            OBSERVE → "Results: [{'_id': 'Transportation', 'total': 99B}]"

Iteration 4: REASON → "Have answer, format response"
            ACT → [No tool] → Final Answer
            RESPOND → "Transportation spent $99 billion"
```

#### 2. **Observation & Retry**
Agent can detect issues and retry:

```python
# Example retry scenario:
Iteration 1: execute_mongodb_query({"find": {"field": "wrong_name"}})
            OBSERVE → {"error": "Field 'wrong_name' doesn't exist"}

Iteration 2: REASON → "Field name was wrong, check schema"
            ACT → get_collection_schema()
            OBSERVE → "Correct field is 'department_name'"

Iteration 3: REASON → "Retry with correct field"
            ACT → execute_mongodb_query({"find": {"field": "department_name"}})
            OBSERVE → "Success! Got results"
```

#### 3. **Hybrid Information Retrieval**
Combines database and web search:

```python
# Example hybrid query:
Question: "Which CA dept manages healthcare and what's the US budget?"

Iteration 1: translate_query("CA healthcare department")
            execute_mongodb_query() → "Dept of Health Care Services"

Iteration 2: search_web("US healthcare budget 2024")
            OBSERVE → "US spends $4.5 trillion on healthcare"

Iteration 3: Combine both results in natural language response
```

### Comparison: Traditional vs Agentic

| Aspect | Traditional Pipeline | Agentic ReAct |
|--------|---------------------|---------------|
| **Flow** | Fixed sequence | Dynamic loop |
| **Error Handling** | Fail immediately | Retry with corrections |
| **Tool Use** | Predetermined | Autonomous selection |
| **Schema Knowledge** | Hardcoded | Inspects on-demand |
| **Iterations** | Single pass | Multiple passes (up to 8) |
| **Observability** | Limited | Full reasoning trace |
| **Adaptability** | None | Self-correcting |

---

## Code Flow & Execution

### Startup Sequence

```
1. User runs: streamlit run app.py
   │
   ├─> app.py
   │   ├─> init_session_state()
   │   │   ├─> Initialize: llm_config = None
   │   │   ├─> Initialize: mongo_client = None
   │   │   ├─> Initialize: agent = None
   │   │   ├─> Initialize: chat_logger = None
   │   │   └─> Initialize: session_id = UUID
   │   │
   │   └─> Display welcome page with navigation
   │
   └─> User navigates to pages/1_Config.py
```

### Configuration Flow

```
pages/1_Config.py
   │
   ├─> User selects provider: Gemini or OpenAI
   │
   ├─> render_gemini_config() OR render_openai_config()
   │   ├─> Detect API key from env
   │   ├─> Show model selection
   │   └─> Return config_data dict
   │
   ├─> User enables logging (optional)
   │   ├─> Select: BigQuery or Local CSV
   │   ├─> Configure destination
   │   └─> Store logging_config
   │
   ├─> User clicks "Test Connection"
   │   │
   │   └─> test_llm_connection(provider, config_data)
   │       │
   │       ├─> create_llm_manager(provider, api_key, model)
   │       │   │
   │       │   └─> src/llm_manager.py → LLMManagerV2.__init__()
   │       │       ├─> _init_chat_model()
   │       │       │   ├─> IF Gemini: _init_gemini_chat()
   │       │       │   │   ├─> Detect API key type (AQ. vs AIza)
   │       │       │   │   └─> Create ChatGoogleGenerativeAI
   │       │       │   │
   │       │       │   └─> IF OpenAI: _init_openai_chat()
   │       │       │       ├─> Check for gpt-5 model
   │       │       │       └─> Create ChatOpenAI
   │       │       │
   │       │       └─> test_connection()
   │       │           └─> generate("Respond with OK")
   │       │
   │       └─> IF success:
   │           ├─> st.session_state.llm_manager = llm_manager
   │           ├─> st.session_state.llm_config = {...}
   │           └─> st.session_state.chat_logger = create_chat_logger(...)
   │
   └─> User clicks "Next: Data Setup"
```

### Data Setup Flow

```
pages/2_Data_Setup.py
   │
   ├─> User enters MongoDB URI
   │
   ├─> User clicks "Connect to MongoDB"
   │   │
   │   └─> src/mongo_client.py → MongoDBClient(uri, db_name)
   │       ├─> connect()
   │       └─> st.session_state.mongo_client = client
   │
   ├─> User clicks "Load Data to MongoDB"
   │   │
   │   └─> src/data_loader.py → load_procurement_data()
   │       │
   │       ├─> Read CSV in chunks (1000 rows)
   │       ├─> Parse dates, clean data
   │       ├─> Insert to MongoDB in batches
   │       ├─> Create indexes
   │       │   ├─> creation_date
   │       │   ├─> fiscal_year
   │       │   ├─> department_name
   │       │   ├─> supplier_name
   │       │   └─> (creation_date, fiscal_year)
   │       │
   │       └─> Return stats (total_documents, date_range, etc.)
   │
   └─> st.session_state.data_loaded = True
```

### Chat Query Flow (The Agentic Loop)

```
pages/3_Chat_Assistant.py
   │
   ├─> User enters: "Which department spent the most money?"
   │
   └─> process_query(user_query)
       │
       ├─> Append to messages: {"role": "user", "content": query}
       │
       └─> st.session_state.agent.process_query(user_query)
           │
           └─> src/ai_agent_agentic.py → AgenticProcurementAgent.process_query()
               │
               ├─> START: Initialize counters
               │   ├─> iterations = 0
               │   ├─> tool_calls_made = []
               │   ├─> total_input_tokens = 0
               │   └─> total_output_tokens = 0
               │
               ├─> Build conversation messages
               │   ├─> SystemMessage(system_prompt)
               │   └─> HumanMessage(user_question)
               │
               ├─> ┌─────────────────────────────────────┐
               │   │   REACT LOOP (max 8 iterations)     │
               │   └─────────────────────────────────────┘
               │   │
               │   ├─> ITERATION 1
               │   │   │
               │   │   ├─> THINK: llm_with_tools.invoke(messages)
               │   │   │   ├─> LLM analyzes question
               │   │   │   ├─> Track tokens from response_metadata
               │   │   │   └─> Returns: AIMessage with tool_calls
               │   │   │
               │   │   ├─> CHECK: Does AIMessage have tool_calls?
               │   │   │   ├─> NO → Final answer ready → BREAK
               │   │   │   └─> YES → Continue to ACT
               │   │   │
               │   │   ├─> ACT: Execute tool_calls
               │   │   │   │
               │   │   │   ├─> Tool: "get_collection_schema"
               │   │   │   │   └─> _tool_get_schema()
               │   │   │   │       └─> mongo.get_collection_schema()
               │   │   │   │           └─> Sample 100 docs, extract fields
               │   │   │   │
               │   │   │   ├─> Tool: "translate_query"
               │   │   │   │   └─> _tool_translate_query(user_question)
               │   │   │   │       └─> translator.translate(question)
               │   │   │   │           └─> LangChain query translator
               │   │   │   │               ├─> Load few-shot examples
               │   │   │   │               ├─> Build prompt with schema
               │   │   │   │               └─> LLM generates MongoDB query
               │   │   │   │
               │   │   │   ├─> Tool: "execute_mongodb_query"
               │   │   │   │   └─> _tool_execute_query(query_json)
               │   │   │   │       ├─> Parse JSON to extract query_type & query
               │   │   │   │       ├─> IF query_type == "aggregate":
               │   │   │   │       │   └─> mongo.aggregate(pipeline)
               │   │   │   │       └─> IF query_type == "find":
               │   │   │   │           └─> mongo.find(filter, limit)
               │   │   │   │
               │   │   │   └─> Tool: "search_web"
               │   │   │       └─> _tool_search_web(query, max_results)
               │   │   │           └─> DuckDuckGoSearchResults(num_results)
               │   │   │               └─> Returns search snippets
               │   │   │
               │   │   ├─> OBSERVE: Create ToolMessage with results
               │   │   │   └─> messages.append(ToolMessage(content=tool_output))
               │   │   │
               │   │   └─> TRACK: tool_calls_made.append(tool_name)
               │   │
               │   ├─> ITERATION 2 (if needed)
               │   │   └─> [Same THINK → ACT → OBSERVE cycle]
               │   │
               │   ├─> ITERATION 3 (if needed)
               │   │   └─> [Same cycle...]
               │   │
               │   └─> ... up to ITERATION 8
               │
               ├─> EXTRACT: final_response from AIMessage.content
               │
               ├─> CALCULATE: execution_time
               │
               └─> RETURN: {
                   "success": True,
                   "response": clean_response,
                   "iterations": 3,
                   "tools_used": ["get_collection_schema", "translate_query", "execute_mongodb_query"],
                   "execution_time": 2.45,
                   "token_count": {
                       "input_token_count": 2341,
                       "output_token_count": 156,
                       "total_token_count": 2497
                   }
               }
```

### Post-Query Flow

```
pages/3_Chat_Assistant.py (continued)
   │
   ├─> Receive result from agent
   │
   ├─> Add assistant message to session:
   │   └─> messages.append({
   │       "role": "assistant",
   │       "content": result["response"],
   │       "query_data": result
   │   })
   │
   ├─> LOG INTERACTION (if enabled):
   │   │
   │   └─> log_chat_interaction(message_idx, feedback="NA")
   │       │
   │       └─> chat_logger.log_interaction(
   │           session_id,
   │           model,
   │           user_query,
   │           tools_used,
   │           response,
   │           user_feedback="NA",
   │           token_count
   │       )
   │       │
   │       └─> src/chat_logger.py → ChatLogger.log_interaction()
   │           │
   │           ├─> Prepare log_entry dict
   │           │
   │           ├─> TRY BigQuery (if enabled):
   │           │   │
   │           │   └─> _log_to_bigquery(log_entry)
   │           │       ├─> Insert to BigQuery table
   │           │       └─> IF SUCCESS: Done
   │           │
   │           └─> FALLBACK to CSV:
   │               └─> _log_to_csv(log_entry)
   │                   └─> Append to chat_logs.csv
   │
   ├─> DISPLAY RESPONSE in chat UI:
   │   │
   │   └─> render_chat_message(role, content, query_data)
   │       ├─> Show metrics: Iterations, Tools, Time, Web Status
   │       ├─> Show token usage (if available)
   │       └─> Show feedback buttons (if logging enabled)
   │
   └─> User clicks feedback (👍 or 👎):
       │
       └─> log_chat_interaction(message_idx, feedback="upvote")
           └─> Updates log with new feedback
```

### Tool Execution Details

#### Tool 1: get_collection_schema

```python
Flow:
  _tool_get_schema()
    │
    └─> mongo_client.get_collection_schema(collection_name)
        │
        ├─> Sample 100 documents from collection
        │
        ├─> Extract unique field names
        │   └─> For each doc:
        │       └─> Recursively find all keys (nested included)
        │
        ├─> Determine field types
        │   └─> Sample values to infer: string, int, date, etc.
        │
        └─> Return: {
            "collection": "procurement_orders",
            "total_documents": 919734,
            "fields": {
                "purchase_order_number": "string",
                "creation_date": "date",
                "total_price": "number",
                "department_name": "string",
                ...
            }
        }
```

#### Tool 2: translate_query

```python
Flow:
  _tool_translate_query(user_question)
    │
    └─> translator.translate(user_question)
        │
        ├─> Build context:
        │   ├─> Collection schema (fields and types)
        │   └─> Few-shot examples (5 examples)
        │
        ├─> Construct prompt:
        │   """
        │   You are a MongoDB query translator.
        │
        │   Schema: {schema}
        │
        │   Examples:
        │   Q: "How many orders in Q1 2013?"
        │   A: {"query_type": "find", "query": {...}}
        │
        │   Q: "Top 5 departments by spending?"
        │   A: {"query_type": "aggregate", "query": [{$group...}]}
        │
        │   Translate: "{user_question}"
        │   """
        │
        ├─> LLM call: llm_manager.generate_json(prompt)
        │
        └─> Return: {
            "query_type": "aggregate",
            "query": [
                {"$group": {"_id": "$department_name", "total": {"$sum": "$total_price"}}},
                {"$sort": {"total": -1}},
                {"$limit": 1}
            ],
            "explanation": "Groups by department, sums spending, sorts descending"
        }
```

#### Tool 3: execute_mongodb_query

```python
Flow:
  _tool_execute_query(query_json)
    │
    ├─> Parse JSON: query_data = json.loads(query_json)
    │
    ├─> Extract: query_type, query
    │
    ├─> IF query_type == "aggregate":
    │   │
    │   └─> mongo_client.aggregate(collection, pipeline)
    │       ├─> Validate pipeline is a list
    │       ├─> Execute: collection.aggregate(pipeline)
    │       ├─> Convert results to list
    │       └─> Serialize (handle ObjectId, datetime)
    │
    └─> IF query_type == "find":
        │
        └─> mongo_client.find(collection, filter, limit=100)
            ├─> Execute: collection.find(filter).limit(100)
            ├─> Convert cursor to list
            └─> Serialize results

    Return: {
        "success": true,
        "results": [
            {"_id": "Transportation", "total": 99000000000},
            ...
        ],
        "count": 1
    }
```

#### Tool 4: search_web

```python
Flow:
  _tool_search_web(query, max_results=5)
    │
    └─> DuckDuckGoSearchResults(num_results=max_results)
        │
        ├─> DDGS().text(query, max_results)
        │   └─> Calls DuckDuckGo search API
        │
        ├─> Format results:
        │   └─> [
        │       {"title": "...", "snippet": "...", "url": "..."},
        │       ...
        │   ]
        │
        └─> Return: {
            "success": true,
            "query": "current inflation rate",
            "results": "snippet: ..., title: ..., link: ...",
            "count": 5
        }
```

---

## Data Architecture

### MongoDB Schema

```javascript
// Collection: procurement_orders
{
  "_id": ObjectId("..."),

  // Order Identifiers
  "purchase_order_number": "P3000123456",
  "requisition_number": "R2013-001234",
  "lpa_number": "LPA-12-0045",

  // Dates
  "creation_date": ISODate("2013-07-15T00:00:00Z"),
  "purchase_date": ISODate("2013-07-20T00:00:00Z"),
  "fiscal_year": "2013-2014",

  // Department
  "department_name": "Department of Transportation",

  // Supplier
  "supplier_code": "SUP123",
  "supplier_name": "ACME Supplies Inc.",
  "supplier_zip_code": "94105",

  // Item Details
  "item_name": "Office Chairs",
  "item_description": "Ergonomic office chairs with lumbar support",
  "quantity": 50,
  "unit_price": 299.99,
  "total_price": 14999.50,

  // Classification
  "acquisition_type": "Goods",
  "commodity_title": "Furniture and Furnishings",
  "normalized_unspsc": "56101501",

  // Location
  "location": "Sacramento, CA"
}
```

### Indexes

```javascript
// Single field indexes
db.procurement_orders.createIndex({ "creation_date": 1 })
db.procurement_orders.createIndex({ "fiscal_year": 1 })
db.procurement_orders.createIndex({ "department_name": 1 })
db.procurement_orders.createIndex({ "supplier_name": 1 })
db.procurement_orders.createIndex({ "total_price": 1 })

// Compound indexes
db.procurement_orders.createIndex({ "creation_date": 1, "fiscal_year": 1 })
db.procurement_orders.createIndex({ "supplier_name": 1, "total_price": 1 })

// Text index for search
db.procurement_orders.createIndex({ "item_name": "text", "item_description": "text" })
```

### Data Loading Pipeline

```
CSV File (919,734 rows)
    │
    ├─> Read in chunks (1000 rows/batch)
    │
    ├─> For each chunk:
    │   ├─> Parse dates (MM/DD/YYYY → ISODate)
    │   ├─> Convert prices (string → float)
    │   ├─> Handle nulls
    │   ├─> Calculate fiscal_year
    │   │   └─> July-June fiscal year
    │   └─> Clean field names
    │
    ├─> Insert batch to MongoDB
    │   └─> db.procurement_orders.insert_many(chunk)
    │
    ├─> Progress bar update
    │
    └─> After all batches:
        ├─> Create indexes
        └─> Return statistics
```

### Query Patterns

#### Aggregation Example: Top Departments by Spending

```javascript
db.procurement_orders.aggregate([
  {
    $group: {
      _id: "$department_name",
      total_spending: { $sum: "$total_price" },
      order_count: { $sum: 1 }
    }
  },
  {
    $sort: { total_spending: -1 }
  },
  {
    $limit: 10
  }
])
```

#### Find Example: Orders in Q1 2013

```javascript
db.procurement_orders.find({
  creation_date: {
    $gte: ISODate("2013-01-01"),
    $lt: ISODate("2013-04-01")
  }
}).limit(100)
```

---

## LLM Integration

### Multi-Provider Architecture

```
┌────────────────────────────────────────────────────┐
│             LLMManagerV2 (Abstraction)             │
├────────────────────────────────────────────────────┤
│  Methods:                                          │
│  - generate(prompt) → str                          │
│  - generate_json(prompt) → dict                    │
│  - test_connection() → dict                        │
├────────────────────────────────────────────────────┤
│  Provider-Specific Initialization:                 │
│  - _init_gemini_chat()                            │
│  - _init_openai_chat()                            │
└────────────────┬───────────────┬───────────────────┘
                 │               │
      ┌──────────▼──────┐   ┌───▼──────────┐
      │ Gemini Branch   │   │ OpenAI Branch│
      └─────────────────┘   └──────────────┘
```

### Gemini Integration

```python
# Authentication Modes:
Mode 1: API Key (Developer)
  - Key starts with "AIza"
  - Direct Google AI API
  - Free tier available

Mode 2: API Key (Vertex AI Express)
  - Key starts with "AQ."
  - Vertex AI with API key
  - No service account needed

Mode 3: Service Account
  - GOOGLE_APPLICATION_CREDENTIALS env var
  - Full Vertex AI access
  - For production deployments

# Code Flow:
if api_key.startswith("AQ."):
    # Vertex AI Express Mode
    chat_model = ChatGoogleGenerativeAI(
        model="gemini-3-pro-preview",
        google_api_key=api_key,
        vertexai=True,
        max_output_tokens=8192,
        convert_system_message_to_human=True
    )
elif api_key.startswith("AIza"):
    # Developer API
    chat_model = ChatGoogleGenerativeAI(
        model="gemini-3-pro-preview",
        google_api_key=api_key,
        max_output_tokens=8192,
        convert_system_message_to_human=True
    )
else:
    # Service Account
    credentials = service_account.Credentials.from_service_account_file(
        sa_key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    chat_model = ChatGoogleGenerativeAI(
        model="gemini-3-pro-preview",
        credentials=credentials,
        project=project_id,
        vertexai=True,
        max_output_tokens=8192,
        convert_system_message_to_human=True
    )
```

### OpenAI Integration

```python
# Authentication:
- OPENAI_API_KEY environment variable
- API key starts with "sk-"

# Special Handling for GPT-5:
if model == "gpt-5":
    # GPT-5 only supports temperature=1 (default)
    chat_model = ChatOpenAI(
        model="gpt-5",
        # temperature not set (uses default 1)
        max_tokens=8192,
        api_key=api_key
    )
else:
    chat_model = ChatOpenAI(
        model=model,
        temperature=0.1,
        max_tokens=8192,
        api_key=api_key
    )
```

### Token Tracking

```python
# After each LLM call:
if hasattr(ai_msg, 'response_metadata'):
    metadata = ai_msg.response_metadata

    # OpenAI format:
    if 'token_usage' in metadata:
        usage = metadata['token_usage']
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

    # Gemini format:
    elif 'usage_metadata' in metadata:
        usage = metadata['usage_metadata']
        input_tokens = usage.get('prompt_token_count', 0)
        output_tokens = usage.get('candidates_token_count', 0)

    # Accumulate across iterations:
    total_input_tokens += input_tokens
    total_output_tokens += output_tokens
```

---

## Tool System

### Tool Registry

```python
# LangChain @tool decorator:
@tool
def get_collection_schema() -> str:
    """
    Get the MongoDB collection schema.
    Use this when you need to know available fields.
    """
    return self._tool_get_schema()

@tool
def translate_query(user_question: str) -> str:
    """
    Translate natural language to MongoDB query.

    Args:
        user_question: Natural language question

    Returns:
        JSON with query_type, query, and explanation
    """
    return self._tool_translate_query(user_question)

@tool
def execute_mongodb_query(query_json: str) -> str:
    """
    Execute a MongoDB query.

    Args:
        query_json: JSON string with query_type and query

    Returns:
        JSON with success, results, and count
    """
    return self._tool_execute_query(query_json)

@tool
def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo.

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        JSON with search results
    """
    return self._tool_search_web(query, max_results)
```

### Tool Binding

```python
# Bind tools to LLM:
tools = [get_collection_schema, translate_query, execute_mongodb_query]

if enable_web_search:
    tools.append(search_web)

llm_with_tools = llm.bind_tools(tools)
```

### Tool Invocation

```python
# LLM returns tool calls in AIMessage:
ai_msg = llm_with_tools.invoke(messages)

# Extract tool calls:
for tool_call in ai_msg.tool_calls:
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    tool_id = tool_call["id"]

    # Execute corresponding tool:
    if tool_name == "get_collection_schema":
        output = self.tools[0].invoke({})

    elif tool_name == "translate_query":
        q = tool_args.get("user_question")
        output = self._tool_translate_query(q)

    # ... etc

    # Add result to conversation:
    messages.append(ToolMessage(
        content=output,
        tool_call_id=tool_id
    ))
```

---

## Logging & Observability

### Logging Architecture

```
┌──────────────────────────────────────────────┐
│          Chat Interaction Event              │
│  (user query + agent response + feedback)    │
└─────────────────┬────────────────────────────┘
                  │
    ┌─────────────▼──────────────┐
    │    ChatLogger.log_interaction()
    │                            │
    ├─> Prepare log_entry dict  │
    │   - session_id             │
    │   - timestamp              │
    │   - model                  │
    │   - user_query             │
    │   - tools_used (JSON)      │
    │   - response               │
    │   - user_feedback          │
    │   - token_count (JSON)     │
    └────────────┬───────────────┘
                 │
    ┌────────────▼───────────────┐
    │  IF log_to_bigquery        │
    │  AND bq_available:         │
    └────┬───────────────────┬───┘
         │ YES               │ NO
         │                   │
    ┌────▼────────┐    ┌─────▼──────┐
    │  BigQuery   │    │  Local CSV │
    │  Insert     │    │  Append    │
    └─────────────┘    └────────────┘
         │
    ┌────▼────────────────────────┐
    │ IF error (network, auth):   │
    │ Fallback → CSV              │
    └─────────────────────────────┘
```

### BigQuery Schema

```sql
CREATE TABLE `hudhud-demo.penny_demo.chat_logs` (
  session_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  model STRING,
  user_query STRING NOT NULL,
  tools_used STRING,  -- JSON array
  response STRING,
  user_feedback STRING,
  token_count STRING  -- JSON object
)
```

### CSV Format

```csv
session_id,timestamp,model,user_query,tools_used,response,user_feedback,token_count
uuid,2026-02-07T20:00:00Z,gpt-4o,"Which dept?","[""translate_query""]","Transportation",upvote,"{""input_token_count"":1234,...}"
```

### Metrics Collection

```python
# Per Query:
- iterations: Number of ReAct loop cycles
- tools_used: List of tools called
- execution_time: Total time in seconds
- token_count: {input, output, total}

# Aggregated (in BigQuery):
- Average tokens per query
- Most used tools
- User satisfaction (upvote %)
- Cost per model
- Query complexity (iterations)
```

---

## Deployment Diagram

### Local Development

```
┌─────────────────────────────────────────────────┐
│          Developer's Laptop                      │
│                                                  │
│  ┌───────────────────────────────────────┐      │
│  │  Streamlit App (localhost:8501)       │      │
│  │  - Python 3.12                        │      │
│  │  - Virtual Env (.venv/)               │      │
│  └───────┬───────────────────────────────┘      │
│          │                                       │
│  ┌───────▼───────────────────────────────┐      │
│  │  MongoDB (localhost:27017)            │      │
│  │  - procurement_orders collection      │      │
│  │  - 919,734 documents                  │      │
│  └───────────────────────────────────────┘      │
│                                                  │
│  ┌───────────────────────────────────────┐      │
│  │  Environment Variables (.env)         │      │
│  │  - OPENAI_API_KEY                     │      │
│  │  - GOOGLE_API_KEY                     │      │
│  │  - GOOGLE_APPLICATION_CREDENTIALS     │      │
│  └───────────────────────────────────────┘      │
└─────────────┬───────────────────┬───────────────┘
              │                   │
      ┌───────▼────────┐  ┌───────▼───────┐
      │  OpenAI API    │  │  Google Cloud │
      │  (external)    │  │  - Gemini API │
      └────────────────┘  │  - BigQuery   │
                          └───────────────┘
```

### Production Deployment (Example)

```
┌─────────────────────────────────────────────────┐
│            Cloud Run / App Engine               │
│                                                  │
│  ┌───────────────────────────────────────┐      │
│  │  Streamlit Container                  │      │
│  │  - Auto-scaling (1-10 instances)      │      │
│  │  - Environment variables from Secret  │      │
│  │    Manager                            │      │
│  └───────┬───────────────────────────────┘      │
│          │                                       │
│  ┌───────▼───────────────────────────────┐      │
│  │  MongoDB Atlas (Managed)              │      │
│  │  - M10 cluster (production)           │      │
│  │  - Auto-backup enabled                │      │
│  │  - VPC peering                        │      │
│  └───────────────────────────────────────┘      │
└─────────────┬───────────────────┬───────────────┘
              │                   │
      ┌───────▼────────┐  ┌───────▼───────┐
      │  OpenAI API    │  │  Google Cloud │
      │  (external)    │  │  - Vertex AI  │
      │                │  │  - BigQuery   │
      └────────────────┘  │  - IAM Auth   │
                          └───────────────┘
```

---

## Performance Considerations

### Optimization Strategies

1. **Index Coverage**
   - All common query fields indexed
   - Compound indexes for multi-field queries
   - Query planning with `.explain()`

2. **Result Limiting**
   - Default limit: 100 documents
   - Prevents memory issues
   - Pagination for large result sets

3. **Connection Pooling**
   - MongoDB connection reused across requests
   - Streamlit session state for agent instance
   - Warm connections reduce latency

4. **Token Management**
   - Track usage per query
   - Set max_tokens limits
   - Monitor costs by model

5. **Caching** (Future)
   - Cache schema inspections
   - Cache common query translations
   - Redis for distributed cache

### Scalability

```
Current: Single instance, local MongoDB
  ├─> Handles: ~10 concurrent users
  └─> Response time: 1-5 seconds

Production: Cloud-hosted, managed MongoDB
  ├─> Handles: 100+ concurrent users
  ├─> Auto-scaling: 1-10 app instances
  ├─> Response time: 2-10 seconds (with web search)
  └─> Cost: ~$200/month (M10 MongoDB + LLM API costs)
```

---

## Security Considerations

1. **API Key Management**
   - Stored in environment variables
   - Never committed to git
   - Rotation policy recommended

2. **MongoDB Security**
   - Authentication enabled
   - IP whitelist
   - SSL/TLS for connections

3. **Input Validation**
   - Query sanitization
   - Tool parameter validation
   - SQL injection prevention (N/A for MongoDB, but watch for NoSQL injection)

4. **Logging Privacy**
   - User queries logged (be aware of PII)
   - BigQuery access controlled by IAM
   - Data retention policy

---

## Future Enhancements

1. **Advanced RAG**
   - Vector embeddings for semantic search
   - Pinecone/Weaviate integration

2. **Multi-Modal**
   - Chart generation from queries
   - PDF report exports

3. **Collaboration**
   - Multi-user sessions
   - Shared conversation history

4. **Advanced Analytics**
   - Query performance dashboard
   - Cost tracking by user
   - A/B testing different prompts

---

## Conclusion

This system demonstrates a production-ready agentic AI architecture with:

✅ **Autonomous reasoning** via ReAct loop
✅ **Multi-provider LLM support** (Gemini & OpenAI)
✅ **Hybrid information retrieval** (Database + Web)
✅ **Comprehensive observability** (Logging + Metrics)
✅ **Self-correcting behavior** (Retry logic)
✅ **Clean separation of concerns** (Modular architecture)

The agentic design pattern enables the system to handle complex, multi-step queries with minimal human intervention while maintaining full transparency into its reasoning process.
