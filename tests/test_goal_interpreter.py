"""Tests for TREGO Goal Interpreter."""
from server.trego.goal import GoalInterpreter


def test_interpret_cpp_goals():
    interpreter = GoalInterpreter()
    goal = interpreter.interpret("Set up my laptop for C++ development.")
    assert goal.target_stack == "cpp"
    assert goal.category == "setup"
    assert len(goal.verification_criteria) > 0


def test_interpret_flutter_goals():
    interpreter = GoalInterpreter()
    goal = interpreter.interpret("Why isn't my Flutter project running?")
    assert goal.target_stack == "flutter"
    assert goal.category == "fix"

    goal2 = interpreter.interpret("Prepare this machine for Flutter development.")
    assert goal2.target_stack == "flutter"
    assert goal2.category == "setup"


def test_interpret_python_goals():
    interpreter = GoalInterpreter()
    goal = interpreter.interpret("Configure my machine for Python machine learning.")
    assert goal.target_stack == "python"
    assert goal.category == "setup"


def test_interpret_github_repo():
    interpreter = GoalInterpreter()
    goal = interpreter.interpret("Set up this GitHub project https://github.com/flutter/samples.git and run it.")
    assert goal.target_stack == "github"
    assert goal.repo_url == "https://github.com/flutter/samples.git"
