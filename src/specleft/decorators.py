"""Decorator and context manager for SpecLeft test metadata and step tracking."""

from __future__ import annotations

import functools
import inspect
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class StepResult:
    """Result of a test step execution."""

    description: str
    status: str  # "passed", "failed", "skipped"
    start_time: datetime
    end_time: datetime | None = None
    error: str | None = None


# Thread-local storage for current test context
_test_context = threading.local()


def get_current_steps() -> list[StepResult]:
    """Get the list of steps for the current test.

    Returns:
        List of StepResult objects for the current test execution.
    """
    if not hasattr(_test_context, "steps"):
        _test_context.steps = []
    return cast(list[StepResult], _test_context.steps)


def clear_steps() -> None:
    """Clear the steps for the current test context."""
    _test_context.steps = []


def is_in_specleft_test() -> bool:
    """Check if currently executing within a @specleft decorated test.

    Returns:
        True if inside a @specleft test, False otherwise.
    """
    return getattr(_test_context, "in_specleft_test", False)


def _set_in_specleft_test(value: bool) -> None:
    """Set the in_specleft_test flag.

    Args:
        value: Whether we are inside a @specleft test.
    """
    _test_context.in_specleft_test = value


class _SpecLeftDecorator:
    """Decorator class that also exposes the step context manager."""

    def __call__(self, feature_id: str, scenario_id: str) -> Callable[[F], F]:
        """Decorator to mark tests with SpecLeft metadata.

        Args:
            feature_id: The feature ID (e.g., "AUTH-001").
            scenario_id: The scenario ID (e.g., "login-success").

        Returns:
            Decorated function with metadata attached.
        """

        def decorator(func: F) -> F:
            func._specleft_feature_id = feature_id  # type: ignore[attr-defined]
            func._specleft_scenario_id = scenario_id  # type: ignore[attr-defined]

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Initialize step collection for this test
                clear_steps()
                _set_in_specleft_test(True)
                try:
                    return func(*args, **kwargs)
                finally:
                    _set_in_specleft_test(False)

            # Copy metadata to wrapper
            wrapper._specleft_feature_id = feature_id  # type: ignore[attr-defined]
            wrapper._specleft_scenario_id = scenario_id  # type: ignore[attr-defined]

            return wrapper  # type: ignore[return-value]

        return decorator

    @staticmethod
    @contextmanager
    def step(description: str) -> Generator[StepResult, None, None]:
        """Context manager for recording test steps.

        Args:
            description: Description of the step (supports f-strings).

        Yields:
            StepResult object that will be populated with timing and status.

        Example:
            with specleft.step("Given user has valid credentials"):
                # test code here
                pass

            with specleft.step(f"When user logs in with '{username}'"):
                # dynamic description
                pass
        """
        step_result = StepResult(
            description=description,
            status="passed",
            start_time=datetime.now(),
        )

        try:
            yield step_result
            step_result.status = "passed"
        except Exception as e:
            step_result.status = "failed"
            step_result.error = str(e)
            raise
        finally:
            step_result.end_time = datetime.now()
            get_current_steps().append(step_result)


# Module-level instance for use as decorator
specleft = _SpecLeftDecorator()

# Also expose step as module-level function for convenience
step = specleft.step


def reusable_step(description: str) -> Callable[[F], F]:
    """Decorator for reusable step functions that are automatically traced.

    When a function decorated with @reusable_step is called from within a
    @specleft decorated test, it will automatically be recorded as a step.
    When called outside of a @specleft test, the function executes normally
    without any tracing overhead.

    The description supports parameter interpolation using {param_name} syntax.
    Parameter values are substituted from the function's actual arguments.

    Args:
        description: Step description with optional {param_name} placeholders.

    Returns:
        Decorator function that wraps the original function.

    Example:
        @reusable_step("User logs in with {username}")
        def login_user(username: str, password: str):
            browser.get("/login")
            browser.find("#username").send_keys(username)
            browser.find("#password").send_keys(password)
            browser.find("#login-btn").click()

        @specleft(feature_id="AUTH-001", scenario_id="login-success")
        def test_login():
            # This call is automatically traced as:
            # "User logs in with user@example.com"
            login_user("user@example.com", "SecurePass123!")
            assert browser.current_url == "/dashboard"
    """

    def decorator(func: F) -> F:
        # Store the step description on the function for introspection
        func._specleft_step_description = description  # type: ignore[attr-defined]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Only trace if called from within a @specleft test
            if is_in_specleft_test():
                # Interpolate parameters into description
                sig = inspect.signature(func)
                try:
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    # Format description with actual parameter values
                    formatted_desc = description.format(**bound_args.arguments)
                except (KeyError, ValueError, TypeError):
                    # If interpolation fails, use original description
                    formatted_desc = description

                # Use step context manager to record execution
                with step(formatted_desc):
                    return func(*args, **kwargs)
            else:
                # Called outside @specleft test, just execute normally
                return func(*args, **kwargs)

        # Copy the step description to the wrapper
        wrapper._specleft_step_description = description  # type: ignore[attr-defined]

        return wrapper  # type: ignore[return-value]

    return decorator
