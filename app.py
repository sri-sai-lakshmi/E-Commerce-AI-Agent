# app.py
import streamlit as st
import google.generativeai as genai
import pandas as pd
from sqlalchemy import create_engine, text, inspect  # <-- Make sure 'inspect' is here
from duckduckgo_search import DDGS
import os
import json
from dotenv import load_dotenv

# --- 1. Configuration and Setup ---

# Load environment variables (your GEMINI_API_KEY)
load_dotenv()

# --- MySQL DATABASE CONFIGURATION ---
# !!! **UPDATE THESE VALUES to match load_data.py** !!!
DB_USER = "root"
DB_PASSWORD = "" # Your MySQL password
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "olist_db"

# Configure the Gemini API
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    # This is the NEW, corrected line
    # This is the NEW, corrected line
    GEMINI_MODEL = genai.GenerativeModel('gemini-2.5-pro')
except Exception as e:
    st.error(f"Error configuring Gemini: {e}. Is your GEMINI_API_KEY set in .env?")
    st.stop()

# --- 2. Database Connection and Schema ---

@st.cache_resource
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Failed to connect to MySQL database: {e}")
        st.stop()

@st.cache_data
def get_db_schema(_engine):
    """
    Introspects the database and returns a simplified schema string.
    This schema is what the LLM will use to write queries.
    """
    # Use the new SQLAlchemy inspect function
    inspector = inspect(_engine) 
    
    schema_info = []
    tables = inspector.get_table_names()
    
    for table in tables:
        columns = inspector.get_columns(table)
        col_names = [col['name'] for col in columns]
        schema_info.append(f"Table: {table}, Columns: {', '.join(col_names)}")
    
    return "\n".join(schema_info)

# Initialize connection and get schema
engine = get_db_connection()
DB_SCHEMA = get_db_schema(engine)


# --- 3. Tool Definitions (The "Agentic" Part) ---

def run_sql_agent(query_prompt: str, chat_history: list) -> str:
    """
    Tool 1: Text-to-SQL Agent
    Takes a natural language query, generates SQL, executes it, 
    and returns a natural language summary of the results.
    """
    st.write("🤖 Thinking in SQL...")

    # --- Step 3a: Generate SQL Query ---
    formatted_history = format_chat_history_for_prompt(chat_history)
    
    # !!! THIS PROMPT IS NOW FIXED !!!
    sql_prompt = f"""
    You are an expert MySQL database analyst.
    Your task is to generate a single, executable MySQL query to answer the user's question.
    
    DATABASE SCHEMA:
    {DB_SCHEMA}

    RULES:
    - ONLY output the SQL query, nothing else. No preamble, no explanation.
    - The query must be compatible with MySQL.
    - ALWAYS wrap table and column names in backticks (`).
    - Table names in the schema are correct as-is (e.g., `olist_orders_dataset`, NOT `olist_orders_dataset.csv`).
    - If a query is complex, use Common Table Expressions (CTEs) for clarity.
    - The `product_category_name_translation` table translates Portuguese category names. 
      You MUST join with it (on `product_category_name`) to show English names.
    
    CHAT HISTORY (for context):
    {formatted_history}
    
    USER'S QUESTION:
    "{query_prompt}"
    
    MySQL QUERY:
    ```sql
    """
    
    try:
        response = GEMINI_MODEL.generate_content(sql_prompt)
        sql_query = response.text.strip().replace("```sql", "").replace("```", "")
        st.code(sql_query, language="sql")
    except Exception as e:
        return f"Error generating SQL: {e}"

    # --- Step 3b: Execute SQL Query ---
    try:
        with engine.connect() as conn:
            result_df = pd.read_sql(text(sql_query), conn)
            result_json = result_df.to_json(orient="records")
    except Exception as e:
        return f"Error executing SQL: {e}. Query was: {sql_query}"

    # --- Step 3c: Summarize Results ---
    st.write("🧠 Analyzing results...")
    summary_prompt = f"""
    You are a helpful data analyst.
    The user asked this question: "{query_prompt}"
    
    We ran a SQL query and got this data (in JSON format):
    {result_json}
    
    Please provide a concise, natural language answer to the user's question based *only* on this data.
    - Do not mention the SQL query or JSON.
    - If the data is a single number or list, present it cleanly.
    - If the data is a table, summarize the key findings.
    """
    
    try:
        summary_response = GEMINI_MODEL.generate_content(summary_prompt)
        return summary_response.text
    except Exception as e:
        return f"Error summarizing results: {e}"

def run_web_agent(query_prompt: str) -> str:
    """
    Tool 2: Web Search Agent
    Uses DuckDuckGo to search the web for external information.
    """
    st.write("🤖 Searching the web...")
    
    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query_prompt, max_results=5))
        
        if not search_results:
            return "I couldn't find anything on the web for that query."
        
        # Format snippets for the LLM
        snippets = "\n".join([f"Snippet {i+1}: {r['body']}" for i, r in enumerate(search_results)])
        
        summary_prompt = f"""
        You are a helpful research assistant.
        The user asked: "{query_prompt}"
        
        I found these web search results:
        {snippets}
        
        Please provide a concise answer to the user's question based *only* on these snippets.
        Cite the snippet numbers if you want, but it's not required.
        """
        
        summary_response = GEMINI_MODEL.generate_content(summary_prompt)
        return summary_response.text
    except Exception as e:
        return f"Error during web search: {e}"

def run_map_agent() -> str:
    """
    Tool 3: Map Plotting Agent
    Fetches customer geolocation data and displays it on a Streamlit map.
    """
    st.write("🤖 Generating map of customer locations...")
    
    try:
        # A simple query to get a sample of customer locations
        map_query = """
        SELECT 
            geo.geolocation_lat,
            geo.geolocation_lng
        FROM 
            `olist_customers_dataset.csv` c
        JOIN 
            `olist_geolocation_dataset.csv` geo 
        ON 
            c.customer_zip_code_prefix = geo.geolocation_zip_code_prefix
        LIMIT 2000;
        """
        with engine.connect() as conn:
            map_df = pd.read_sql(text(map_query), conn)
        
        # Rename for st.map
        map_df.rename(columns={'geolocation_lat': 'lat', 'geolocation_lng': 'lon'}, inplace=True)
        
        # Display the map in Streamlit
        st.map(map_df, zoom=3)
        return "Here is a map showing the locations of 2,000 sample customers."
        
    except Exception as e:
        return f"Error generating map: {e}"

def run_chat_agent(query_prompt: str, chat_history: list) -> str:
    """
    Tool 4: General Chat Agent
    For holding a normal conversation.
    """
    st.write("🤖 Just chatting...")
    
    # !!! THIS IS THE FIX !!!
    formatted_history = format_chat_history_for_prompt(chat_history)
    
    prompt = f"""
    You are a friendly and helpful conversational AI.
    
    CHAT HISTORY (for context):
    {formatted_history}
    
    USER'S QUESTION:
    "{query_prompt}"
    
    YOUR RESPONSE:
    """
    
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error in chat: {e}"

# --- 4. NEW Helper Function for Chat History ---

def format_chat_history_for_prompt(chat_history: list) -> str:
    """Converts the chat history list of dicts to a simple string."""
    if not chat_history:
        return "No history yet."
    
    formatted_string = ""
    # We only need the last few messages for context
    for message in chat_history[-5:]: # Get last 5 messages
        role = "User" if message['role'] == 'user' else "Assistant"
        content = message['content'].replace('\n', ' ').strip()
        formatted_string += f"{role}: {content}\n"
    return formatted_string

# --- 5. The Agent Orchestrator (Router) ---

def get_agent_response(user_prompt: str, chat_history: list) -> str:
    """
    This is the main "Router" or "Orchestrator" agent.
    It decides which tool to use based on the user's prompt.
    """
    
    # This is the master prompt for the router.
    # !!! THIS IS THE FIX !!!
    formatted_history = format_chat_history_for_prompt(chat_history)
    
    router_prompt = f"""
    You are an AI agent orchestrator for an e-commerce data analysis chatbot.
    Your job is to classify the user's query and select the *only* correct tool to answer it.
    
    You have the following tools:
    1.  **sql_analyst**: Use this for any question that requires analyzing the e-commerce database.
        Examples: "What are the top 5 selling products?", "Total revenue last quarter?", "Average review score?"
    
    2.  **web_search**: Use this for general knowledge, definitions, real-time information, or product details *not* in the database.
        Examples: "What is 'Olist'?", "Define 'average order value'", "What's the weather in Sao Paulo?"
    
    3.  **plot_map**: Use this *only* when the user explicitly asks to see locations on a map.
        Examples: "Show me where my customers are", "Plot seller locations on a map"
    
    4.  **general_chat**: Use this for greetings, follow-ups, or when no other tool is appropriate.
        Examples: "Hello", "Thanks!", "Wow, that's cool", "What can you do?"

    Given the chat history and the new user query, respond with a *single* JSON object 
    indicating the tool to use and the query for that tool.
    
    JSON format: {{"tool": "tool_name", "query": "query_for_the_tool"}}
    
    ---
    CHAT HISTORY:
    {formatted_history}
    
    NEW USER QUERY:
    "{user_prompt}"
    ---
    
    YOUR JSON RESPONSE:
    """

    try:
        # Ask the LLM to choose a tool
        response = GEMINI_MODEL.generate_content(router_prompt)
        
        # Clean and parse the JSON response
        tool_choice_json = response.text.strip().replace("```json", "").replace("```", "")
        tool_choice = json.loads(tool_choice_json)
        
        tool = tool_choice.get("tool")
        query_for_tool = tool_choice.get("query")

        # --- Call the chosen tool ---
        if tool == "sql_analyst":
            return run_sql_agent(query_for_tool, chat_history)
        elif tool == "web_search":
            return run_web_agent(query_for_tool)
        elif tool == "plot_map":
            return run_map_agent()
        elif tool == "general_chat":
            return run_chat_agent(query_for_tool, chat_history)
        else:
            return f"Error: The router selected an invalid tool ('{tool}')."
            
    except json.JSONDecodeError:
        st.error(f"Error: The agent's routing decision was not valid JSON: {response.text}")
        return run_chat_agent(user_prompt, chat_history) # Fallback to chat
    except Exception as e:
        return f"An error occurred in the agent orchestrator: {e}"


# --- 6. Streamlit Chat Interface ---

st.set_page_config(page_title="E-Commerce AI Agent", page_icon="🛍️")
st.title("🛍️ E-Commerce AI Agent")
st.caption(f"Chat with your Olist dataset in `{DB_NAME}`. Powered by Gemini & Streamlit.")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I help you analyze the e-commerce data today?"}]

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get new user input
if user_prompt := st.chat_input("What's the total revenue this year?"):
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_prompt)
    
    # Generate and display agent's response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Call the main agent orchestrator
            response_text = get_agent_response(user_prompt, st.session_state.messages)
            
            # Display the final response
            st.markdown(response_text)
            
            # Add agent response to history
            st.session_state.messages.append({"role": "assistant", "content": response_text})