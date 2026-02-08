"""
Few-shot examples for query translation.
These examples teach the LLM how to generate correct MongoDB queries for different query patterns.
"""

FEW_SHOT_EXAMPLES = [
    # ========================================================================
    # BASIC COUNT QUERIES
    # ========================================================================
    {
        "user_query": "How many total orders are in the database?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {"$count": "total_orders"}
            ]
        },
        "explanation": "Count all documents in the collection"
    },

    # ========================================================================
    # TIME-BASED QUERIES
    # ========================================================================
    {
        "user_query": "How many orders were created in Q1 2013?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "fiscal_year": "2012-2013",
                        "fiscal_quarter": "Q1"
                    }
                },
                {"$count": "total_orders"}
            ]
        },
        "explanation": "Count documents in fiscal Q1 2013 (fiscal year 2012-2013, Q1 = Jul-Sep 2012)"
    },
    {
        "user_query": "How many orders were created in January 2014?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "creation_year": 2014,
                        "creation_month": 1
                    }
                },
                {"$count": "total_orders"}
            ]
        },
        "explanation": "Count documents where creation year is 2014 and month is 1 (January)"
    },
    {
        "user_query": "What was the total spending in fiscal year 2013-2014?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "fiscal_year": "2013-2014"
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_spending": {"$sum": "$total_price"}
                    }
                }
            ]
        },
        "explanation": "Sum total_price for all documents in fiscal year 2013-2014"
    },

    # ========================================================================
    # TOP N / RANKING QUERIES
    # ========================================================================
    {
        "user_query": "What are the top 5 most frequently ordered items?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$group": {
                        "_id": "$item_name",
                        "order_count": {"$sum": 1},
                        "total_quantity": {"$sum": "$quantity"}
                    }
                },
                {
                    "$sort": {"order_count": -1}
                },
                {
                    "$limit": 5
                }
            ]
        },
        "explanation": "Group by item_name, count orders, sum quantities, sort by count descending, limit to 5"
    },
    {
        "user_query": "Which department spent the most money?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$group": {
                        "_id": "$department_name",
                        "total_spending": {"$sum": "$total_price"}
                    }
                },
                {
                    "$sort": {"total_spending": -1}
                },
                {
                    "$limit": 1
                }
            ]
        },
        "explanation": "Group by department, sum spending, sort descending, get top 1"
    },
    {
        "user_query": "Who are the top 5 suppliers by revenue?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$group": {
                        "_id": "$supplier_name",
                        "total_revenue": {"$sum": "$total_price"},
                        "order_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"total_revenue": -1}
                },
                {
                    "$limit": 5
                }
            ]
        },
        "explanation": "Group by supplier, sum revenue, count orders, sort by revenue descending, limit to 5"
    },

    # ========================================================================
    # FISCAL QUARTER ANALYSIS
    # ========================================================================
    {
        "user_query": "Which quarter had the highest spending in fiscal year 2013-2014?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "fiscal_year": "2013-2014"
                    }
                },
                {
                    "$group": {
                        "_id": "$fiscal_quarter",
                        "total_spending": {"$sum": "$total_price"},
                        "order_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"total_spending": -1}
                },
                {
                    "$limit": 1
                }
            ]
        },
        "explanation": "Match fiscal year 2013-2014, group by fiscal_quarter, sum spending, sort descending, get top 1"
    },
    {
        "user_query": "Show quarterly spending for fiscal year 2014-2015",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "fiscal_year": "2014-2015"
                    }
                },
                {
                    "$group": {
                        "_id": "$fiscal_quarter",
                        "total_spending": {"$sum": "$total_price"},
                        "order_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
        },
        "explanation": "Match fiscal year, group by fiscal quarter, sum spending and count, sort by quarter"
    },

    # ========================================================================
    # FILTER QUERIES
    # ========================================================================
    {
        "user_query": "Show me all orders from the Department of Water Resources",
        "query_type": "find",
        "query": {
            "filter": {
                "department_name": {"$regex": "Water Resources", "$options": "i"}
            },
            "limit": 100
        },
        "explanation": "Find documents where department_name contains 'Water Resources' (case-insensitive), limit to 100"
    },
    {
        "user_query": "Show me IT Goods orders over $10,000",
        "query_type": "find",
        "query": {
            "filter": {
                "acquisition_type": "IT Goods",
                "total_price": {"$gt": 10000}
            },
            "limit": 100
        },
        "explanation": "Find IT Goods orders with total_price greater than 10000, limit to 100"
    },
    {
        "user_query": "How many orders did the Department of Corrections place?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "department_name": {"$regex": "Corrections", "$options": "i"}
                    }
                },
                {"$count": "total_orders"}
            ]
        },
        "explanation": "Count documents where department_name contains 'Corrections'"
    },

    # ========================================================================
    # AGGREGATION QUERIES
    # ========================================================================
    {
        "user_query": "What is the average order value by department?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$group": {
                        "_id": "$department_name",
                        "average_order_value": {"$avg": "$total_price"},
                        "total_orders": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"average_order_value": -1}
                },
                {
                    "$limit": 20
                }
            ]
        },
        "explanation": "Group by department, calculate average total_price, count orders, sort descending, limit to 20"
    },
    {
        "user_query": "How many different suppliers are in the database?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$group": {
                        "_id": "$supplier_name"
                    }
                },
                {"$count": "unique_suppliers"}
            ]
        },
        "explanation": "Group by supplier_name to get unique values, then count them"
    },
    {
        "user_query": "What was the most expensive single item purchased?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$sort": {"total_price": -1}
                },
                {
                    "$limit": 1
                }
            ]
        },
        "explanation": "Sort by total_price descending and get the first document"
    },

    # ========================================================================
    # COMPLEX QUERIES
    # ========================================================================
    {
        "user_query": "Compare spending between fiscal years 2012-2013 and 2013-2014",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$match": {
                        "fiscal_year": {"$in": ["2012-2013", "2013-2014"]}
                    }
                },
                {
                    "$group": {
                        "_id": "$fiscal_year",
                        "total_spending": {"$sum": "$total_price"},
                        "order_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
        },
        "explanation": "Match both fiscal years, group by fiscal_year, sum spending and count, sort by year"
    },
    {
        "user_query": "Which supplier had the most orders?",
        "query_type": "aggregate",
        "query": {
            "pipeline": [
                {
                    "$group": {
                        "_id": "$supplier_name",
                        "order_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"order_count": -1}
                },
                {
                    "$limit": 1
                }
            ]
        },
        "explanation": "Group by supplier_name, count orders, sort descending, get top 1"
    },
]


def get_few_shot_examples_text(num_examples: int = 5) -> str:
    """
    Get few-shot examples formatted as text for inclusion in prompts.

    Args:
        num_examples: Number of examples to include (default 5)

    Returns:
        Formatted examples string
    """
    import json

    if num_examples <= 0:
        return ""

    examples_to_use = FEW_SHOT_EXAMPLES[:num_examples]

    examples_text = "EXAMPLES:\n\n"

    for i, example in enumerate(examples_to_use, 1):
        examples_text += f"Example {i}:\n"
        examples_text += f"USER QUERY: {example['user_query']}\n"
        examples_text += f"RESPONSE:\n{json.dumps({'query_type': example['query_type'], 'query': example['query'], 'explanation': example['explanation']}, indent=2)}\n\n"

    return examples_text


def get_similar_examples(user_query: str, num_examples: int = 3) -> str:
    """
    Get examples most similar to the user query.

    Args:
        user_query: The user's question
        num_examples: Number of examples to return

    Returns:
        Formatted examples string
    """
    # Simple keyword-based matching
    # In production, you might use embeddings for better similarity

    query_lower = user_query.lower()

    # Keywords to match
    keywords = {
        "quarter": ["quarter", "q1", "q2", "q3", "q4", "quarterly"],
        "top": ["top", "most", "highest", "best", "largest"],
        "count": ["how many", "count", "number of"],
        "department": ["department"],
        "supplier": ["supplier", "vendor"],
        "spending": ["spending", "spent", "cost", "price", "expensive"],
        "item": ["item", "product"],
        "fiscal": ["fiscal", "fiscal year"],
    }

    # Score each example
    scored_examples = []
    for example in FEW_SHOT_EXAMPLES:
        score = 0
        example_lower = example["user_query"].lower()

        for category, words in keywords.items():
            if any(word in query_lower for word in words):
                if any(word in example_lower for word in words):
                    score += 1

        scored_examples.append((score, example))

    # Sort by score descending
    scored_examples.sort(key=lambda x: x[0], reverse=True)

    # Get top N examples
    selected_examples = [ex for score, ex in scored_examples[:num_examples]]

    return get_few_shot_examples_text(num_examples) if not selected_examples else format_examples_list(selected_examples)


def format_examples_list(examples: list) -> str:
    """Format a list of examples as text."""
    import json

    examples_text = "RELEVANT EXAMPLES:\n\n"

    for i, example in enumerate(examples, 1):
        examples_text += f"Example {i}:\n"
        examples_text += f"USER QUERY: {example['user_query']}\n"
        examples_text += f"RESPONSE:\n{json.dumps({'query_type': example['query_type'], 'query': example['query'], 'explanation': example['explanation']}, indent=2)}\n\n"

    return examples_text
