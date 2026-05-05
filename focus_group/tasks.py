from celery import shared_task
import requests
import json
import os
import concurrent.futures
from .models import PreflightRun, AgentFeedback

@shared_task
def run_agent_swarm(run_id):
    run = None
    try:
        run = PreflightRun.objects.get(id=run_id)
        api_key = os.getenv('OPENROUTER_API_KEY')
        tavily_key = os.getenv('TAVILY_API_KEY')
        
        # ==========================================
        # TOOL 1: LIVE MARKET RESEARCH (APIFY / TAVILY)
        # ==========================================
        live_market_data = "No live market data available."
        apify_token = os.getenv('APIFY_API_TOKEN')
        
        if run.product_url and apify_token:
            print("Initiating Perfect Amazon Scrape via Apify...")
            apify_url = f"https://api.apify.com/v2/acts/junglee~amazon-reviews-scraper/run-sync-get-dataset-items?token={apify_token}"
            payload = {
                "productUrls": [{"url": run.product_url}],
                "maxReviews": 15,
                "sort": "recent"
            }
            try:
                scrape_response = requests.post(apify_url, json=payload, timeout=120)
                if scrape_response.status_code in [200, 201]:
                    reviews = scrape_response.json()
                    extracted_data = []
                    for review in reviews:
                        rating = review.get('ratingScore', 'Unknown')
                        text = review.get('reviewDescription', '')
                        extracted_data.append(f"[{rating} Stars]: {text}")
                    live_market_data = "\n".join(extracted_data)
                    if not live_market_data:
                        live_market_data = "No live market data available."
                    else:
                        run.research_data = "Successfully pulled direct Amazon Reviews via Apify."
                        run.save()
                        print("Apify Scrape Successful!")
                else:
                    print("Apify Failed:", scrape_response.text)
            except Exception as e:
                print("Apify Error:", e)

        if live_market_data == "No live market data available." and tavily_key:
            # Fallback to Tavily if no URL or Apify fails
            try:
                search_response = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": f"What is the average price and top customer complaints for: {run.product_name} on Amazon?",
                        "search_depth": "basic",
                        "max_results": 3
                    },
                    timeout=15
                )
                if search_response.status_code == 200:
                    results = search_response.json().get('results', [])
                    live_market_data = " ".join([r['content'] for r in results])
                    run.research_data = live_market_data
                    run.save()
                else:
                    print(f"Tavily API Error: {search_response.status_code} - {search_response.text}")
            except Exception as e:
                print(f"Tavily Request Failed: {e}")

        # ==========================================
        # TOOL 2: THE AGENT SWARM (OPENROUTER API)
        # ==========================================
        personas = [
            {"role": "The Budget Shopper", "prompt": "You are a price-sensitive Amazon shopper. Identify a financial hesitation."},
            {"role": "The Skeptic", "prompt": "You assume e-commerce products are low quality. Find a potential flaw in durability."},
            {"role": "The Feature Obsessive", "prompt": "You care deeply about material specs. Find a missing technical detail."}
        ]
        
        def fetch_persona(persona):
            system_prompt = f"""
            {persona['prompt']} 
            Use this LIVE MARKET DATA to inform your critique: '{live_market_data}'.
            
            CRITICAL INSTRUCTION: 
            You must find a specific objection based on the market data and the product description. Do not give generic advice.
            
            YOU MUST OUTPUT ONLY VALID JSON. Format EXACTLY like this example: 
            {{
                "intent_score": 30, 
                "objection": "I am worried the aluminum handle will snap under heavy weight."
            }}
            """
            
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "openrouter/free", # Fast model
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Product: {run.product_name}. Description: {run.product_desc}"}
                    ]
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"OpenRouter API Error: {response.status_code} - {response.text}")
                return None
            
            res_json = response.json()
            content = res_json.get('choices', [{}])[0].get('message', {}).get('content')
            
            if not content:
                print(f"Warning: AI returned empty content for persona {persona['role']}")
                return None
                
            content = content.replace('```json', '').replace('```', '').strip()
            try:
                data = json.loads(content)
                return {
                    "role": persona["role"],
                    "intent_score": data.get('intent_score', 50),
                    "objection": data.get('objection', 'Unclear objection')
                }
            except json.JSONDecodeError:
                print(f"Error: AI returned invalid JSON: {content}")
                return None

        feedback_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(fetch_persona, p) for p in personas]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    feedback_results.append(res)
                    
        for res in feedback_results:
            AgentFeedback.objects.create(
                run=run,
                persona=res["role"],
                intent_score=res["intent_score"],
                objection=res["objection"]
            )
            
        # ==========================================
        # TOOL 3: SUMMARY GENERATION
        # ==========================================
        all_feedbacks = AgentFeedback.objects.filter(run=run)
        feedback_text = "\n".join([f"{f.persona} ({f.intent_score}% intent): {f.objection}" for f in all_feedbacks])
        
        summary_prompt = f"""
        You are an expert product analyst and e-commerce strategist. Review the following buyer objections and market research.
        
        Market Research:
        {live_market_data}
        
        Buyer Objections:
        {feedback_text}
        
        CRITICAL INSTRUCTION:
        Provide a concise overall summary, a list of positive aspects (pros), a list of negative aspects (cons), 2-3 specific pricing strategies or suggestions, and 2-3 product upgrade/feature suggestions.
        
        YOU MUST OUTPUT ONLY VALID JSON. Format EXACTLY like this example:
        {{
            "summary": "Overall, the product has strong potential but faces pricing and durability concerns.",
            "pros": ["Innovative design", "Good for specific use cases"],
            "cons": ["High price compared to competitors", "Durability concerns from Skeptic persona"],
            "pricing_strategy": ["Lower the price to $49 to match competitors", "Offer a bundle deal"],
            "upgrade_suggestions": ["Reinforce the handle with steel", "Add a carrying case"]
        }}
        """
        
        summary_response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "openrouter/free",
                "messages": [
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": f"Product: {run.product_name}"}
                ]
            },
            timeout=30
        )
        
        if summary_response.status_code == 200:
            sum_res_json = summary_response.json()
            sum_content = sum_res_json.get('choices', [{}])[0].get('message', {}).get('content', '')
            sum_content = sum_content.replace('```json', '').replace('```', '').strip()
            import re
            json_match = re.search(r'\{.*\}', sum_content, re.DOTALL)
            if json_match:
                try:
                    sum_data = json.loads(json_match.group(0))
                    run.summary = sum_data.get('summary', '')
                    run.pros = json.dumps(sum_data.get('pros', []))
                    run.cons = json.dumps(sum_data.get('cons', []))
                    run.pricing_strategy = json.dumps(sum_data.get('pricing_strategy', []))
                    run.upgrade_suggestions = json.dumps(sum_data.get('upgrade_suggestions', []))
                except Exception as e:
                    print(f"Error parsing summary JSON: {e}")
            
        run.status = 'completed'
        run.save()
        
    except Exception as e:
        if run:
            run.status = 'failed'
            run.save()
        print(f"Task Failed: {e}")