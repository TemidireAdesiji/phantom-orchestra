"""Tests for Scene."""

from phantom.performer.scene import Scene
from phantom.signal.report.control import PerformerState
from phantom.voice.message import MessageRole


class TestSceneInitialisation:
    def test_scene_initialises_with_correct_session_id(self):
        scene = Scene(session_id="abc-123")
        assert scene.session_id == "abc-123"

    def test_scene_default_iteration_zero(self):
        scene = Scene(session_id="s")
        assert scene.iteration == 0

    def test_scene_default_max_iterations(self):
        scene = Scene(session_id="s")
        assert scene.max_iterations == 100

    def test_scene_default_state_is_loading(self):
        scene = Scene(session_id="s")
        assert scene.current_state == PerformerState.LOADING

    def test_scene_default_budget_spent_is_zero(self):
        scene = Scene(session_id="s")
        assert scene.budget_spent_usd == 0.0

    def test_scene_default_max_budget_is_none(self):
        scene = Scene(session_id="s")
        assert scene.max_budget_usd is None

    def test_scene_history_empty_by_default(self):
        scene = Scene(session_id="s")
        assert scene.history == []

    def test_scene_outputs_empty_by_default(self):
        scene = Scene(session_id="s")
        assert scene.outputs == {}


class TestSceneBudgetExceeded:
    def test_budget_exceeded_false_when_no_max_budget(self):
        scene = Scene(session_id="s", max_budget_usd=None)
        scene.budget_spent_usd = 9999.0
        assert scene.budget_exceeded is False

    def test_budget_exceeded_false_when_under_limit(self):
        scene = Scene(session_id="s", max_budget_usd=10.0)
        scene.budget_spent_usd = 5.0
        assert scene.budget_exceeded is False

    def test_budget_exceeded_true_when_at_limit(self):
        scene = Scene(session_id="s", max_budget_usd=5.0)
        scene.budget_spent_usd = 5.0
        assert scene.budget_exceeded is True

    def test_budget_exceeded_true_when_over_limit(self):
        scene = Scene(session_id="s", max_budget_usd=5.0)
        scene.budget_spent_usd = 6.0
        assert scene.budget_exceeded is True


class TestSceneIterationsExceeded:
    def test_iterations_not_exceeded_below_max(self):
        scene = Scene(session_id="s", max_iterations=10)
        scene.iteration = 9
        assert scene.iterations_exceeded is False

    def test_iterations_exceeded_at_max(self):
        scene = Scene(session_id="s", max_iterations=10)
        scene.iteration = 10
        assert scene.iterations_exceeded is True

    def test_iterations_exceeded_above_max(self):
        scene = Scene(session_id="s", max_iterations=5)
        scene.iteration = 99
        assert scene.iterations_exceeded is True


class TestSceneShouldStop:
    def test_should_stop_false_when_running_normally(self):
        scene = Scene(session_id="s", max_iterations=100)
        scene.current_state = PerformerState.RUNNING
        assert scene.should_stop is False

    def test_should_stop_true_when_iterations_exceeded(self):
        scene = Scene(session_id="s", max_iterations=1)
        scene.iteration = 1
        scene.current_state = PerformerState.RUNNING
        assert scene.should_stop is True

    def test_should_stop_true_when_budget_exceeded(self):
        scene = Scene(session_id="s", max_budget_usd=1.0)
        scene.budget_spent_usd = 2.0
        scene.current_state = PerformerState.RUNNING
        assert scene.should_stop is True

    def test_should_stop_true_when_state_complete(self):
        scene = Scene(session_id="s")
        scene.current_state = PerformerState.COMPLETE
        assert scene.should_stop is True

    def test_should_stop_true_when_state_failed(self):
        scene = Scene(session_id="s")
        scene.current_state = PerformerState.FAILED
        assert scene.should_stop is True

    def test_should_stop_true_when_state_stopped(self):
        scene = Scene(session_id="s")
        scene.current_state = PerformerState.STOPPED
        assert scene.should_stop is True


class TestSceneMutationHelpers:
    def test_add_user_message_appends_to_history(self):
        scene = Scene(session_id="s")
        scene.add_user_message("hello")
        assert len(scene.history) == 1
        assert scene.history[0].role == MessageRole.USER
        assert scene.history[0].content == "hello"

    def test_add_user_message_multiple_times(self):
        scene = Scene(session_id="s")
        scene.add_user_message("first")
        scene.add_user_message("second")
        assert len(scene.history) == 2


class TestSceneToSummary:
    def test_to_summary_returns_dict(self):
        scene = Scene(session_id="sum-test")
        result = scene.to_summary()
        assert isinstance(result, dict)

    def test_to_summary_contains_expected_keys(self):
        scene = Scene(session_id="k")
        summary = scene.to_summary()
        expected = {
            "session_id",
            "current_state",
            "iteration",
            "max_iterations",
            "history_length",
            "directive_count",
            "report_count",
            "budget_spent_usd",
            "max_budget_usd",
            "budget_exceeded",
            "iterations_exceeded",
            "should_stop",
            "output_keys",
        }
        assert expected.issubset(summary.keys())

    def test_to_summary_session_id_matches(self):
        scene = Scene(session_id="my-session")
        assert scene.to_summary()["session_id"] == "my-session"

    def test_to_summary_history_length_reflects_messages(self):
        scene = Scene(session_id="s")
        scene.add_user_message("a")
        scene.add_user_message("b")
        assert scene.to_summary()["history_length"] == 2
