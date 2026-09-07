# server/core/llms.py
"""Fast, schema-native LLM helpers for the codebase intelligence graph."""
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

load_dotenv()

# Getting api keys for models
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# =========================
# OPENAI MODELS
# =========================

OPENAI_MODELS = [
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-5-mini",
    "gpt-5",
    "gpt-4o-mini",
    "gpt-4o",
]

# Reusable function that creates openai models
def get_openai_llm(model_name: str):
    """Create a deterministic ChatOpenAI client for one configured model name."""
    api_key = os.getenv("OPENAI_API_KEY") or "sk-dummy-key-set-in-env-before-invoking"
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=0,  # keep every chain's ceiling consistent
    )


def get_structured_llm(schema, model_name: str = "gpt-4.1-mini"):
    """Return the fast primary model with native structured output.

    Graph schemas are deliberately closed and use provider-enforced bounds, such as
    the maximum number of interpreted requirements.
    """
    return get_openai_llm(model_name).with_structured_output(schema).with_retry(
        stop_after_attempt=2,
        wait_exponential_jitter=False,
    )


def get_function_calling_llm(
    schema,
    model_name: str = "gpt-4.1-mini",
    timeout_seconds: float = 45,
):
    """Return a validated function-calling chain for flexible editor payloads."""
    api_key = os.getenv("OPENAI_API_KEY") or "sk-dummy-key-set-in-env-before-invoking"
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=0,
        timeout=timeout_seconds,
    ).with_structured_output(
        schema,
        method="function_calling",
    ).with_retry(
        stop_after_attempt=1,
        wait_exponential_jitter=False,
    )


# =========================
# PREDEFINED INSTANCES
# =========================

# OpenAI fallback chain
openai_llms = [get_openai_llm(m) for m in OPENAI_MODELS]


# FINAL OPENAI CHAIN - For highest accuracy tasks with fallbacks
openai_accuracy_chain = openai_llms[0].with_fallbacks(
    fallbacks=openai_llms[1:],  # use later models as fallbacks
).with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True
)

# Standard aliases for graph pipelines
elite_accuracy_chain = openai_accuracy_chain
groq_reasoning = openai_accuracy_chain
