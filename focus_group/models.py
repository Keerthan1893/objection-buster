from django.db import models
import uuid

class PreflightRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(max_length=255)
    product_url = models.URLField(max_length=500, null=True, blank=True)
    product_desc = models.TextField()
    research_data = models.TextField(null=True, blank=True) # New field for Tavily results
    summary = models.TextField(null=True, blank=True)
    pros = models.TextField(null=True, blank=True)
    cons = models.TextField(null=True, blank=True)
    pricing_strategy = models.TextField(null=True, blank=True)
    upgrade_suggestions = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='processing')
    created_at = models.DateTimeField(auto_now_add=True)

class AgentFeedback(models.Model):
    run = models.ForeignKey(PreflightRun, related_name='feedbacks', on_delete=models.CASCADE)
    persona = models.CharField(max_length=100)
    intent_score = models.IntegerField()
    objection = models.TextField()