E-Commerce AI Agent (Olist Dataset)

This is a Streamlit web app that acts as an "agentic" chatbot for the Brazilian Olist e-commerce dataset. You can ask it questions in plain English, and it will decide whether to query its MySQL database, search the web, or plot a map to get you the answer.

This project uses Google's Gemini AI model (gemini-2.5-pro) as its "brain" and a local MySQL database as its "memory."

## Features

Natural Language to SQL: Ask questions like "What was the total revenue in 2017?" and the agent will write and execute the MySQL query to get the answer.

Agentic Router: The app doesn't just run one tool. It first decides which tool is best.

sql_analyst: For any question about the e-commerce data.

web_search: For general knowledge or definitions (e.g., "What is 'boleto'?").

plot_map: To show customer/seller locations on a map.

general_chat: For greetings and conversation.

Web Search: The web_search agent uses DuckDuckGo to find external information not present in the database.

Geolocation Mapping: The plot_map agent queries the geolocation data to display a map of customer locations directly in the app.

Conversational Memory: The agent remembers the last few messages to understand context in follow-up questions.

## Architecture & Design Decisions

Frontend (Streamlit):

Decision: Use Streamlit for the entire frontend.

Reason: Streamlit is the fastest way to build interactive, data-centric web apps purely in Python. It handles all state management, UI components, and reactivity out of the box, letting us focus on the agent's logic.

Database (MySQL):

Decision: Load all CSV data into a local MySQL database.

Reason: The user was familiar with MySQL, and the data is highly relational. A one-time ETL script (load_data.py) populates the database, making future queries much faster and more powerful than reading from CSVs every time.

Core Logic (The "Agentic Router"):

Decision: Use a multi-step, router-based agent pattern.

Reason: A single-prompt LLM cannot reliably perform multiple, distinct tasks (like web search and SQL queries).

How it works:

A user sends a message (e.g., "What are the top 5 selling products?").

The get_agent_response function (the "Router") is called. It sends the user's message and chat history to the LLM with a specific prompt asking it to classify the request and choose a tool.

The LLM responds with a JSON object, e.g., {"tool": "sql_analyst", "query": "top 5 selling products"}.

The Python code parses this JSON and calls the corresponding function (e.g., run_sql_agent).

This "specialist" agent (run_sql_agent) has its own detailed prompt, focused only on writing SQL. This separation of concerns makes it far more accurate.

After the SQL data is fetched, a third LLM call is made to summarize the data, turning the raw table results into a natural language answer.

🚀 How to Run

Prerequisites

Python 3.9+

Git

A running local MySQL server (like MySQL Workbench or a command-line server)

Step 1: Clone the Repo

git clone <your-repo-url>
cd <your-repo-name>


Step 2: Set Up the Python Environment

We strongly recommend using a virtual environment.

# Create the virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\Activate

# Activate it (Mac/Linux)
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt


Step 3: Set Up API Keys

Create an API key from Google AI Studio.

Rename the .env.example file in this repository to .env.

Open the .env file and paste in your API key:

GEMINI_API_KEY="YOUR_API_KEY_HERE"


Step 4: Set Up and Populate the Database

Ensure your MySQL server is running.

Open your MySQL client and create a new database:

CREATE DATABASE olist_db;


Place all 9 of the Olist CSV files (e.g., olist_customers_dataset.csv) into the root of this project folder.

Open load_data.py and update the CONFIGURATION section at the top with your MySQL credentials (username, password, and database name).

Run the load_data.py script from your terminal. This will load all 9 CSVs into your MySQL database. This may take a few minutes.

python load_data.py


Step 5: Run the App

Open app.py and update the MySQL DATABASE CONFIGURATION section at the top to match the credentials you used in load_data.py.

Run the Streamlit app from your terminal:

streamlit run app.py


Your browser will automatically open to the app.

## Important: Handling API Rate Limits

This app uses the Google AI Free Tier by default. This tier has a very low rate limit (e.g., ~2-5 requests per minute).

This app makes 2-3 API calls per message (1. Router, 2. SQL Gen, 3. Summarizer).

You will hit the 429: Quota exceeded error.

How to solve this:

Quick Fix: Just wait 15-30 seconds between sending messages to the bot.

Real Fix: Go to your Google Cloud project associated with your API key and enable billing. This moves you to a "Pay-as-you-go" plan, which raises the rate limit significantly (e.g., 60+ requests/minute) and makes the app run smoothly.

## Future Improvements

If I had more time, here's what I would add:

Self-Correcting SQL: If a SQL query fails (e.g., a ProgrammingError), I would catch the error, feed the error message back to the run_sql_agent, and ask it to fix its own query.

Streaming Responses: The app currently waits for the full response from the LLM. I would re-architect the generate_content calls to use stream=True and yield the tokens one-by-one. This makes the UI feel infinitely faster and more responsive.

Exponential Backoff: Instead of just failing on a 429 rate limit, I would implement an exponential backoff function (e.g., time.sleep(10)) to automatically retry the API call.

Data Visualization Agent: Add a new tool (python_agent) that can write and execute Python/Pandas code. This would allow it to answer questions like "Show me a line chart of sales over time" by generating pandas code and displaying the result with st.line_chart.

Smarter Caching: Cache the results of common SQL queries. If two users ask "What is the total revenue?", the app should only run the expensive database query once.