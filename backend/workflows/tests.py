import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from .graph import build_candidate_scoring_graph


class LangGraphHumanApprovalTests(SimpleTestCase):
    def test_scoring_graph_pauses_and_resumes_after_human_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "workflow-checkpoints.sqlite3")
            scorer = Mock(return_value=SimpleNamespace(
                pk=42, public_id="evaluation-uuid", overall_score=81,
                confidence_level="HIGH",
                recommendation_for_human_review="REVIEW_RECOMMENDED",
            ))
            config = {"configurable": {"thread_id": "test-thread-001"}}
            with SqliteSaver.from_conn_string(db_path) as checkpointer:
                checkpointer.setup()
                graph = build_candidate_scoring_graph(checkpointer, scorer=scorer)
                initial = {
                    "workflow_run_id": "workflow-uuid",
                    "candidate_pk": 1,
                    "candidate_public_id": "candidate-uuid",
                    "resume_document_public_id": "resume-uuid",
                    "actor_pk": None,
                }
                paused = graph.invoke(initial, config)
                self.assertIn("__interrupt__", paused)
                self.assertEqual(paused["evaluation_pk"], 42)
                scorer.assert_called_once()

                completed = graph.invoke(Command(resume={
                    "review_id": "shortlist-review-uuid",
                    "decision": "APPROVE_FOR_SCREENING",
                    "resulting_candidate_status": "APPROVED_FOR_SCREENING",
                }), config)
                self.assertEqual(completed["workflow_result"], "COMPLETED")
                self.assertEqual(completed["decision"], "APPROVE_FOR_SCREENING")
                scorer.assert_called_once()
