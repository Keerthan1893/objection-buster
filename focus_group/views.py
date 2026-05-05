from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import PreflightRun
from .serializers import PreflightRunSerializer, AgentFeedbackSerializer
from .tasks import run_agent_swarm

def index(request):
    """Serves the HTML frontend."""
    return render(request, 'focus_group/index.html')

@api_view(['POST'])
def start_run(request):
    """Validates data and hands off to Celery."""
    serializer = PreflightRunSerializer(data=request.data)
    if serializer.is_valid():
        run = serializer.save()
        run_agent_swarm.delay(run.id) 
        return Response({'run_id': run.id}, status=status.HTTP_202_ACCEPTED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def check_status(request, run_id):
    """Frontend polls this to get task status and final data."""
    try:
        run = PreflightRun.objects.get(id=run_id)
    except PreflightRun.DoesNotExist:
        return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)

    response_data = {'status': run.status}

    if run.status == 'completed':
        feedbacks = run.feedbacks.all()
        feedback_data = AgentFeedbackSerializer(feedbacks, many=True).data
        avg_score = sum(f['intent_score'] for f in feedback_data) // len(feedback_data) if feedback_data else 0
        response_data['results'] = feedback_data
        response_data['avg_score'] = avg_score
        response_data['research_data'] = run.research_data # RETURN RESEARCH
        response_data['summary'] = run.summary
        try:
            import json
            response_data['pros'] = json.loads(run.pros) if run.pros else []
            response_data['cons'] = json.loads(run.cons) if run.cons else []
            response_data['pricing_strategy'] = json.loads(run.pricing_strategy) if run.pricing_strategy else []
            response_data['upgrade_suggestions'] = json.loads(run.upgrade_suggestions) if run.upgrade_suggestions else []
        except Exception:
            response_data['pros'] = []
            response_data['cons'] = []
            response_data['pricing_strategy'] = []
            response_data['upgrade_suggestions'] = []

    return Response(response_data, status=status.HTTP_200_OK)