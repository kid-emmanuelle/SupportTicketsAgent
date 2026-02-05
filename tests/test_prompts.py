from importlib.resources import files
import re


PROMPTS = ["priority.txt", "classify.txt", "response.txt"]


def test_prompts_exist_and_have_placeholders():
    for name in PROMPTS:
        text = (files("support_agent.prompts") / name).read_text(
            encoding="utf-8"
        )
        assert len(text) > 50
        # sanity: must contain at least one template placeholder
        assert re.search(r"{[a-zA-Z_][a-zA-Z0-9_]*}", text)
