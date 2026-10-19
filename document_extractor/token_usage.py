"""Token counts for one model call, in one shape for both vendors (D29).

OpenAI and TypeSafe each have their own usage class. Converting both into
this one keeps vendor types out of the CLI, which only adds the counts up.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    # None means the API did not report the count. It is kept apart from 0 so
    # a total that is missing some calls is not mistaken for a complete one.
    input_tokens: int | None
    output_tokens: int | None
