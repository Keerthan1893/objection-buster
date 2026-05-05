from rest_framework import serializers
from .models import PreflightRun, AgentFeedback

class AgentFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentFeedback
        fields = ['persona', 'intent_score', 'objection']

class PreflightRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreflightRun
        fields = ['id', 'product_name', 'product_url', 'product_desc', 'status', 'research_data', 'summary', 'pros', 'cons', 'pricing_strategy', 'upgrade_suggestions']
        read_only_fields = ['id', 'status', 'research_data', 'summary', 'pros', 'cons', 'pricing_strategy', 'upgrade_suggestions']