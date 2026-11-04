from rest_framework import serializers


class LLMTestRequestSerializer(serializers.Serializer):
    prompt=serializers.CharField(
        required=False,allow_blank=False,max_length=300,
        default="Reply with the single word READY.",
    )
