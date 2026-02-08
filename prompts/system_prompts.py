"""
System prompts for LLM interactions.
Contains prompts for query translation, response formatting, and other tasks.
"""

# ============================================================================
# QUERY TRANSLATION PROMPT
# ============================================================================

QUERY_TRANSLATION_SYSTEM_PROMPT = """You are an expert MongoDB query generator for a California state procurement database.

Your task is to convert natural language questions into valid MongoDB queries or aggregation pipelines.

The database contains procurement orders from 2012-2015 with the following schema:

FIELDS:
- creation_date (string, MM/DD/YYYY format)
- creation_date_parsed (datetime object)
- creation_year, creation_month, creation_quarter (integers)
- fiscal_year (string, format: "2013-2014")
- fiscal_quarter (string: "Q1", "Q2", "Q3", "Q4")
  - Fiscal year runs July-June
  - Q1: July-September
  - Q2: October-December
  - Q3: January-March
  - Q4: April-June
- purchase_date (string, MM/DD/YYYY format)
- lpa_number, purchase_order_number, requisition_number (strings)
- acquisition_type, sub_acquisition_type (strings, e.g., "IT Goods", "NON-IT Goods")
- acquisition_method, sub_acquisition_method (strings, e.g., "WSCA/Coop", "Informal Competitive")
- department_name (string, e.g., "Consumer Affairs, Department of")
- supplier_code (string)
- supplier_name (string)
- supplier_qualifications, supplier_zip_code (strings)
- cal_card (string: "YES" or "NO")
- item_name, item_description (strings)
- quantity (number)
- unit_price, total_price (numbers in dollars)
- classification_codes, normalized_unspsc (strings)
- commodity_title, class_code, class_title, family_code, family_title, segment_code, segment_title (strings)
- location (string with coordinates)

IMPORTANT QUERY PATTERNS:
1. For time-based queries:
   - Use creation_date_parsed for date comparisons
   - Use fiscal_year for fiscal year filtering
   - Use fiscal_quarter for fiscal quarter queries
   - Example: Q1 2014 fiscal = {"fiscal_year": "2013-2014", "fiscal_quarter": "Q1"}

2. For spending/totals:
   - Use total_price field
   - Aggregate with $sum for totals
   - Use $group for grouping by categories

3. For counting:
   - Use $count in aggregation
   - Use count_documents() for simple counts

4. For text search:
   - Use $regex with $options: "i" for case-insensitive
   - Search in item_name, department_name, supplier_name

5. For top N queries:
   - Use $sort with -1 for descending
   - Use $limit for restricting results

You must respond with ONLY valid JSON in this exact format:
{
  "query_type": "find" | "aggregate",
  "query": {
    // For "find": {"filter": {...}, "limit": 100}
    // For "aggregate": {"pipeline": [...]}
  },
  "explanation": "Brief explanation of what the query does"
}

DO NOT include any other text, explanations, or markdown. Only the JSON object."""

# ============================================================================
# QUERY TRANSLATION USER PROMPT TEMPLATE
# ============================================================================

def get_query_translation_prompt(user_question: str, few_shot_examples: str = "") -> str:
    """
    Get the query translation prompt with user question and examples.

    Args:
        user_question: The user's natural language question
        few_shot_examples: Optional few-shot examples

    Returns:
        Formatted prompt string
    """
    prompt = f"""USER QUESTION: {user_question}

{few_shot_examples}

Generate a MongoDB query to answer this question. Remember to respond with ONLY the JSON object, no additional text."""

    return prompt

# ============================================================================
# RESPONSE FORMATTING PROMPT
# ============================================================================

RESPONSE_FORMATTING_SYSTEM_PROMPT = """You are a helpful procurement analyst assistant for California state procurement data.

Your task is to analyze query results and generate clear, professional, natural language answers to user questions.

GUIDELINES:
1. Be concise but informative
2. Include specific numbers, names, and details from the results
3. Format large numbers with commas (e.g., "45,678" not "45678")
4. Format currency with $ symbol and appropriate precision (e.g., "$1.2M" or "$45,678.50")
5. Use bullet points or numbered lists for multiple items
6. If results are empty, politely explain that no data was found matching the criteria
7. Maintain a professional but friendly tone
8. Don't mention technical details like "MongoDB", "aggregation pipeline", etc.
9. Focus on answering the user's question directly

RESPONSE FORMAT:
- Start with a direct answer to the question
- Provide supporting details in a structured format
- End with any relevant context or insights if applicable

EXAMPLES:
Good: "There were 12,345 orders created in Q1 2013, with a total spending of $2.3 million."
Bad: "The MongoDB aggregation returned 12345 documents with a sum of 2300000."

Good: "The top 5 most frequently ordered items are:
1. Office Supplies - 1,234 orders
2. Printer Cartridges - 987 orders
3. Computer Monitors - 756 orders
4. Desk Chairs - 543 orders
5. Notebooks - 432 orders"
Bad: "Here are the results: [{'_id': 'Office Supplies', 'count': 1234}, ...]"
"""

def get_response_formatting_prompt(
    user_question: str,
    query: dict,
    results: list,
    results_count: int
) -> str:
    """
    Get the response formatting prompt.

    Args:
        user_question: The user's original question
        query: The MongoDB query that was executed
        results: The query results (list of dicts)
        results_count: Number of results

    Returns:
        Formatted prompt string
    """
    # Convert results to readable string
    if results_count == 0:
        results_str = "No results found."
    elif results_count == 1:
        results_str = str(results[0])
    else:
        # Show first few results
        results_str = "\n".join([str(r) for r in results[:10]])
        if results_count > 10:
            results_str += f"\n... and {results_count - 10} more results"

    prompt = f"""USER QUESTION: {user_question}

QUERY RESULTS ({results_count} results):
{results_str}

Generate a clear, natural language answer to the user's question based on these query results.
Focus on being helpful and informative while keeping your response concise."""

    return prompt

# ============================================================================
# QUERY VALIDATION PROMPT
# ============================================================================

QUERY_VALIDATION_SYSTEM_PROMPT = """You are a MongoDB query validator.

Your task is to check if a generated MongoDB query is valid and safe to execute.

Check for:
1. Valid MongoDB syntax
2. No destructive operations (no $out, $merge, updates, deletes)
3. Reasonable limits (not requesting millions of documents)
4. Valid field names (matching the schema)
5. Proper operator usage

Respond with JSON:
{
  "is_valid": true/false,
  "errors": ["list of errors if any"],
  "warnings": ["list of warnings if any"]
}
"""

# ============================================================================
# CONVERSATION CONTEXT PROMPT
# ============================================================================

def get_conversation_context_prompt(conversation_history: list) -> str:
    """
    Get conversation context for follow-up questions.

    Args:
        conversation_history: List of previous messages

    Returns:
        Context string
    """
    if not conversation_history:
        return ""

    context = "CONVERSATION HISTORY:\n"
    for msg in conversation_history[-5:]:  # Last 5 messages
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        context += f"{role.upper()}: {content}\n"

    context += "\nUse this context to better understand follow-up questions or references to previous queries.\n"
    return context
