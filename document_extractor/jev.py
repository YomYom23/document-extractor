"""The only module that talks to TypeSafe's Jev model (D25).

A trimmed copy of lead-bot's wrapper: this project asks only `Choice`
questions. Keeping every Jev call here means an SDK change is a one-file fix.
"""

from collections.abc import Mapping

from typesafe_sdk import Choice, ChoiceAnswer, TypeSafeClient, TypeSafeError


class JevError(Exception):
    """Jev failed or answered incompletely. Callers leave the field null."""


class Jev:
    def __init__(self, client: TypeSafeClient | None = None) -> None:
        # Without a client the SDK builds one that reads TYPESAFE_API_KEY from
        # the environment. Tests never get here: they fake `ask` instead.
        self._client = client if client is not None else TypeSafeClient()

    def ask(
        self, state: str, questions: Mapping[str, Choice]
    ) -> dict[str, ChoiceAnswer]:
        """Send the page text and named questions; get one answer per name."""
        try:
            response = self._client.system_one(state, questions)
        except TypeSafeError as error:
            # Every SDK failure (timeout, 500, bad key) becomes one error type,
            # so callers need a single `except JevError`.
            raise JevError(str(error)) from error

        answers: dict[str, ChoiceAnswer] = {}
        for question_key in questions:
            answer = response.answers.get(question_key)
            # A missing or wrong-typed answer is a failure, not a default:
            # reading it as "no answer" silently would hide an API change.
            if not isinstance(answer, ChoiceAnswer):
                raise JevError(f"no Choice answer for {question_key!r}")
            answers[question_key] = answer
        return answers
