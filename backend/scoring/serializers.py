"""API serializers for scoring rubrics and evaluation records."""

from rest_framework import serializers

from .models import DEFAULT_SCORING_WEIGHTS, ResumeEvaluation, ScoringRubric


class ScoringRubricSerializer(serializers.ModelSerializer):
    requisition_reference = serializers.UUIDField(source="requisition.reference_code", read_only=True)

    class Meta:
        model = ScoringRubric
        fields = ("public_id", "requisition_reference", "name", "weights", "version", "is_active", "notes", "updated_by", "created_at", "updated_at")
        read_only_fields = ("public_id", "requisition_reference", "version", "is_active", "updated_by", "created_at", "updated_at")

    def validate_weights(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Weights must be a JSON object.")
        if set(value) != set(DEFAULT_SCORING_WEIGHTS):
            raise serializers.ValidationError({
                "required_keys": list(DEFAULT_SCORING_WEIGHTS),
                "detail": "Provide exactly the five SRS scoring criteria.",
            })
        if any(not isinstance(value[key], int) or isinstance(value[key], bool) for key in DEFAULT_SCORING_WEIGHTS):
            raise serializers.ValidationError("Every criterion weight must be an integer.")
        normalized = {key: value[key] for key in DEFAULT_SCORING_WEIGHTS}
        if any(weight < 0 or weight > 100 for weight in normalized.values()):
            raise serializers.ValidationError("Each weight must be between 0 and 100.")
        if sum(normalized.values()) != 100:
            raise serializers.ValidationError("Scoring rubric weights must total exactly 100.")
        return normalized


class EvaluationListSerializer(serializers.ModelSerializer):
    candidate_reference = serializers.UUIDField(source="candidate.public_id", read_only=True)
    resume_reference = serializers.UUIDField(source="resume_document.public_id", read_only=True)
    requisition_reference = serializers.UUIDField(source="requisition.reference_code", read_only=True)

    class Meta:
        model = ResumeEvaluation
        fields = (
            "public_id", "candidate_reference", "resume_reference", "requisition_reference",
            "version", "overall_score", "assessed_weight", "criterion_scores", "evidence",
            "missing_or_unclear_items", "parsing_warnings", "confidence_level",
            "recommendation_for_human_review", "overall_assessment", "model_version",
            "prompt_version", "created_at",
        )
        read_only_fields = fields


class EvaluationRequestSerializer(serializers.Serializer):
    resume_document = serializers.UUIDField(required=False)


class EvaluationDetailSerializer(EvaluationListSerializer):
    rubric = ScoringRubricSerializer(read_only=True)

    class Meta(EvaluationListSerializer.Meta):
        fields = EvaluationListSerializer.Meta.fields + ("rubric",)
