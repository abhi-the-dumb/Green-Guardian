from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json

from services.chat import get_chatbot_reply  # import your service function



@api_view(['POST'])
def chat_with_bot(request):
    """
    POST /api/chat/
    Body: { "query": "your question here" }
    """
    user_query = request.data.get("query")
    
    if not user_query:
        return Response(
            {"success": False, "error": "Missing 'query' field in request."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        reply = get_chatbot_reply(user_query)
        return Response({"success": True, "reply": reply})
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
