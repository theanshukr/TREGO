"""Test suite for Real Mouse and Keyboard tools."""
import unittest
from unittest.mock import MagicMock

from shared.protocol import ToolCall, ToolName
from server.agent.tools import _ALLOWED_TOOLS, TOOL_SCHEMAS, _validate_args, dispatch, reset_session_limits
from server.agent.computer import ClientComputer
from client.executor import computer as client_computer


class TestRealInput(unittest.TestCase):
    def setUp(self):
        reset_session_limits()

    def test_protocol_tool_names(self):
        expected_tools = [
            "click", "double_click", "right_click", "middle_click",
            "mouse_move", "mouse_down", "mouse_up", "drag_to",
            "type", "paste", "key", "key_down", "key_up", "hotkey", "scroll",
        ]
        # Verify all expected tools are in _ALLOWED_TOOLS
        for t in expected_tools:
            self.assertIn(t, _ALLOWED_TOOLS, f"Tool {t} should be allowed in tools.py")

    def test_tool_schemas_present(self):
        schema_names = {s["function"]["name"] for s in TOOL_SCHEMAS}
        expected_schemas = [
            "mouse_move", "click", "double_click", "right_click", "middle_click",
            "mouse_down", "mouse_up", "drag_to", "type", "paste",
            "key", "key_down", "key_up", "hotkey", "scroll",
        ]
        for name in expected_schemas:
            self.assertIn(name, schema_names, f"Schema for {name} must be in TOOL_SCHEMAS")

    def test_mouse_arg_validation(self):
        # Valid mouse move
        call_valid = ToolCall(name="mouse_move", args={"x": 500, "y": 300, "duration": 0.5})
        err = _validate_args(call_valid)
        self.assertIsNone(err)
        self.assertEqual(call_valid.args["duration"], 0.5)

        # Invalid coords
        call_invalid = ToolCall(name="mouse_move", args={"x": "invalid", "y": 300})
        err = _validate_args(call_invalid)
        self.assertIsNotNone(err)
        self.assertIn("must be integers", err["error"])

        # Drag to
        call_drag = ToolCall(name="drag_to", args={"x": 100, "y": 200, "duration": 1.0, "button": "left"})
        err = _validate_args(call_drag)
        self.assertIsNone(err)

    def test_keyboard_arg_validation(self):
        # Valid type
        call_type = ToolCall(name="type", args={"text": "hello world"})
        err = _validate_args(call_type)
        self.assertIsNone(err)

        # Dangerous command injection in type (e.g. encoded command / eval)
        call_danger = ToolCall(name="type", args={"text": "powershell -encodedcommand SGVsbG8="})
        err = _validate_args(call_danger)
        self.assertIsNotNone(err)
        self.assertIn("rejected", err["error"])

        # Reset session limits so the rolling danger token buffer is cleared
        reset_session_limits()

        # Valid paste
        call_paste = ToolCall(name="paste", args={"text": "safe code block or note"})
        err = _validate_args(call_paste)
        self.assertIsNone(err)

        # Single key down / up
        call_kd = ToolCall(name="key_down", args={"key": "shift"})
        self.assertIsNone(_validate_args(call_kd))

        call_ku = ToolCall(name="key_up", args={"key": "shift"})
        self.assertIsNone(_validate_args(call_ku))

    def test_client_computer_proxy_methods(self):
        comp = ClientComputer("test_client")
        expected_methods = [
            "mouse_move", "click", "double_click", "right_click", "middle_click",
            "mouse_down", "mouse_up", "drag_to", "type", "paste",
            "key", "key_down", "key_up", "hotkey", "scroll",
        ]
        for method in expected_methods:
            self.assertTrue(hasattr(comp, method), f"ClientComputer must have {method}")

    def test_executor_computer_functions(self):
        expected_functions = [
            "mouse_move", "click", "double_click", "right_click", "middle_click",
            "mouse_down", "mouse_up", "drag_to", "type", "paste",
            "key", "key_down", "key_up", "hotkey", "scroll",
        ]
        for fn in expected_functions:
            self.assertTrue(hasattr(client_computer, fn), f"client/executor/computer must export {fn}")


def test_real_input_protocol_and_schemas():
    case = TestRealInput()
    case.test_protocol_tool_names()
    case.test_tool_schemas_present()


def test_real_input_arg_validation():
    case = TestRealInput()
    case.test_mouse_arg_validation()
    case.test_keyboard_arg_validation()


def test_real_input_proxies():
    case = TestRealInput()
    case.test_client_computer_proxy_methods()
    case.test_executor_computer_functions()


if __name__ == "__main__":
    unittest.main()
