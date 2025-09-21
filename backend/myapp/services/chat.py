from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

@csrf_exempt
def get_chatbot_reply(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        # Make sure to read the body as JSON
        data = json.loads(request.body.decode('utf-8'))
        user_query = data.get("query", "")
        
        if not user_query:
            return JsonResponse({"error": "No query provided"}, status=400)

        system_prompt = (
            "You are an expert agricultural assistant. Answer farmers' questions clearly, "
            "give practical advice on crops, soil, irrigation, and weather, and avoid generic AI answers."
        )

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "max_completion_tokens": 256
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }

        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response_data = response.json()

        if response.status_code != 200:
            return JsonResponse({"error": response_data.get("error", "Unknown error")}, status=500)

        reply = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return JsonResponse({"reply": reply})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
