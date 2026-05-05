#  Pixii Objection Buster
**An Autonomous AI Agent Swarm for Pre-Launch Product Strategy**



##  The Problem
90% of physical products fail because founders don't understand their market's hidden objections until *after* they launch. Growth marketers spend hundreds of hours manually reading competitor reviews to figure out product-market fit, pricing tolerance, and feature gaps.

##  The Solution
The **Objection Buster** completely automates market research and focus groups. 
By entering a competitor's Amazon URL (or just a product concept), this application:
1. **Scrapes the Market:** Bypasses Amazon bot-protections to scrape real 1-star and 5-star customer reviews.
2. **Deploys an Agent Swarm:** Concurrently fires up 3 specialized AI buyer personas (The Budget Shopper, The Skeptic, The Feature Obsessive) to attack the product based on live market data.
3. **Generates an Executive Strategy:** Synthesizes the swarm's feedback into a highly structured JSON report detailing actionable **Pricing Strategies** and **Upgrade Suggestions** to beat the competition.

---

##  Architecture & Tools Used
This is a full-stack, production-ready application featuring a fault-tolerant asynchronous background worker queue.

*   **Framework:** Django + Tailwind CSS
*   **Asynchronous Queue:** Celery + Redis (Handles the heavy LLM lifting without freezing the web server)
*   **API 1: OpenRouter (Agent Swarm Logic):** Uses Python's `concurrent.futures` to manage multiple Llama/Gemma models concurrently, reducing a 5-minute task to 10 seconds.
*   **API 2: Apify (Primary Scraper):** Utilizes residential proxies to synchronously scrape exact Amazon URLs without hitting CAPTCHAs.
*   **API 3: Tavily (Fallback Scraper):** An AI search engine used as a fault-tolerant fallback if the user provides a general concept rather than a specific URL.

---

##  How it Works (The Pipeline)
1. **User Input:** User enters a Product Name, Description, and an optional Competitor Amazon URL.
2. **Handoff:** Django passes the data to the Celery Worker Queue. The frontend gracefully polls the database for status updates.
3. **Data Ingestion:** The Celery worker hits Apify for direct scraping, falling back to Tavily for aggregate market sentiment if needed.
4. **Parallel Swarm:** 3 distinct AI Personas are triggered simultaneously to analyze the scraped data and output JSON intent scores and objections.
5. **Synthesis:** A final Expert AI model evaluates the swarm's results and generates a structured Executive Summary.

---

##  Running it Locally

### Prerequisites
*   Python 3.9+
*   Redis Server (Running via WSL on Windows, or natively on Mac/Linux)
*   API Keys (OpenRouter, Tavily, Apify)

### Setup Instructions
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_django_secret
   OPENROUTER_API_KEY=your_openrouter_key
   TAVILY_API_KEY=your_tavily_key
   APIFY_API_TOKEN=your_apify_token
   REDIS_URL=redis://127.0.0.1:6381/0
   ```
4. Run Migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the Django Server:
   ```bash
   python manage.py runserver
   ```
6. Start the Celery Worker (in a new terminal):
   ```bash
   celery -A config worker -l info -P solo
   ```
7. Open `http://127.0.0.1:8000/` in your browser.

---

##  Deployment (Render.com)
This project includes a `build.sh` and `start.sh` script, making it 1-click deployable to Render.
The `start.sh` script is uniquely configured to run both the Gunicorn web server AND the Celery worker concurrently on a single free Render Web Service.

*(Note: Render's free tier spins down after 15 minutes of inactivity. The first request after spinning down may take ~50 seconds to boot the server).*
