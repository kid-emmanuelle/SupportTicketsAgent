"""Metrics calculation and LLM judge prompts."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from snowflake.snowpark.functions import call_builtin, col, lit
from snowflake.snowpark.session import Session

from ..config import Settings
from ..cortex_agent.rest_client import CortexAgentsRestClient


# ============================================================================
# PROMPT LOADING
# ============================================================================


def load_prompt(prompt_name: str) -> str:
    """Load prompt from text file.

    Args:
        prompt_name: Name of the prompt file (without .txt extension)

    Returns:
        Prompt content as string
    """
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_path = prompts_dir / f"{prompt_name}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)

    with Path.open(prompt_path, encoding="utf-8") as f:
        return f.read()


# Load evaluation prompts at module level
FAITHFULNESS_PROMPT = load_prompt("eval_faithfulness")
ANSWER_RELEVANCY_PROMPT = load_prompt("eval_answer_relevancy")
CONTEXT_PRECISION_PROMPT = load_prompt("eval_context_precision")
CONTEXT_RECALL_PROMPT = load_prompt("eval_context_recall")


# ============================================================================
# AGENT COMPLETION
# ============================================================================


def generate_agent_completion(
    settings: Settings, client_agent: CortexAgentsRestClient, query: str
) -> dict:
    """Generate answer from Cortex Agent and extract metadata."""
    result = client_agent.run_agent_with_object(
        database=settings.database,
        schema=settings.cortex_agent_schema,
        agent_name=settings.cortex_agent_name,
        thread_id=None,
        parent_message_id=None,
        user_text=query,
        stream=True,
    )

    # Extract result metadata
    used_search_tools = False
    tool_use_list = []
    tool_result_list = []

    for step in result.raw_response["content"]:
        if step["type"] == "tool_use":
            tool_use_name = step["tool_use"]["name"]
            tool_use_input = step["tool_use"]["input"]
            if tool_use_name == "cortex_search":
                used_search_tools = True
            tool_use_list.append([tool_use_name, tool_use_input])
        elif step["type"] == "tool_result":
            tool_result_name = step["tool_result"]["name"]
            tool_result_status = step["tool_result"]["status"]
            tool_result_output = step["tool_result"]["content"]
            tool_result_list.append(
                [tool_result_name, tool_result_status, tool_result_output]
            )

    metadata = result.raw_response["metadata"]["usage"]["tokens_consumed"][0]

    return {
        "agent_answer": result.assistant_text,
        "used_search_tools": used_search_tools,
        "tool_use_list": tool_use_list,
        "tool_result_list": tool_result_list,
        "agent_model_name": metadata["model_name"],
        "total_context_input_tokens": metadata["input_tokens"]["total"],
        "total_output_tokens": metadata["output_tokens"],
        "reasoning": result.raw_response["content"],
    }


def extract_context_from_agent_output(agent_output: dict[str, Any]) -> str:
    """Extract retrieved context from agent tool results.

    Args:
        agent_output: Output from agent containing tool_result_list

    Returns:
        Concatenated context string
    """
    retrieved_contexts = []
    for tool_result in agent_output.get("tool_result_list", []):
        if tool_result[0] == "cortex_search" and tool_result[1] == "success":
            retrieved_contexts.append(str(tool_result[2]))

    return (
        "\n\n".join(retrieved_contexts)
        if retrieved_contexts
        else "No context retrieved"
    )


# ============================================================================
# BATCH METRIC COMPUTATION IN SNOWFLAKE
# ============================================================================


def compute_rag_metrics_batch(
    session: Session,
    evaluation_df: pd.DataFrame,
    model: str = "claude-3-5-sonnet",
) -> pd.DataFrame:
    """Compute all RAG metrics for a batch of evaluations directly in Snowflake.

    Args:
        session: Snowflake session
        evaluation_df: DataFrame with columns: query, ground_truth, agent_answer, context
        model: Cortex model to use for evaluation

    Returns:
        DataFrame with added metric columns (scores and explanations)
    """
    print(
        f"Computing metrics for {len(evaluation_df)} evaluations using {model}..."
    )

    # Ensure column names are uppercase before uploading
    df_upper = evaluation_df.copy()
    df_upper.columns = [c.upper() for c in df_upper.columns]

    # Upload evaluation data to temporary table
    temp_table = "PROJECT_DB.EVAL.TEMP_METRIC_COMPUTATION"
    df_snowpark = session.create_dataframe(df_upper)
    df_snowpark.write.mode("overwrite").save_as_table(temp_table)

    # Load the table back as Snowpark DataFrame
    temp_df = session.table(temp_table)

    print("  → Preparing evaluation prompts...")

    # Prepare prompts with data substitution using Snowpark functions
    # Faithfulness: {context}, {answer}
    faithfulness_prompt = call_builtin(
        "REPLACE",
        call_builtin(
            "REPLACE",
            lit(FAITHFULNESS_PROMPT),
            lit("{context}"),
            col("CONTEXT"),
        ),
        lit("{answer}"),
        col("AGENT_ANSWER"),
    )

    # Answer Relevancy: {query}, {answer}
    answer_relevancy_prompt = call_builtin(
        "REPLACE",
        call_builtin(
            "REPLACE",
            lit(ANSWER_RELEVANCY_PROMPT),
            lit("{query}"),
            col("QUERY"),
        ),
        lit("{answer}"),
        col("AGENT_ANSWER"),
    )

    # Context Precision: {query}, {context}
    context_precision_prompt = call_builtin(
        "REPLACE",
        call_builtin(
            "REPLACE",
            lit(CONTEXT_PRECISION_PROMPT),
            lit("{query}"),
            col("QUERY"),
        ),
        lit("{context}"),
        col("CONTEXT"),
    )

    # Context Recall: {query}, {ground_truth}, {context}
    context_recall_prompt = call_builtin(
        "REPLACE",
        call_builtin(
            "REPLACE",
            call_builtin(
                "REPLACE",
                lit(CONTEXT_RECALL_PROMPT),
                lit("{query}"),
                col("QUERY"),
            ),
            lit("{ground_truth}"),
            col("GROUND_TRUTH"),
        ),
        lit("{context}"),
        col("CONTEXT"),
    )

    print("  → Computing all metrics in Snowflake...")

    # Call Cortex Complete for all metrics
    faithfulness_response = call_builtin(
        "SNOWFLAKE.CORTEX.COMPLETE", lit(model), faithfulness_prompt
    ).alias("FAITHFULNESS_RESPONSE")

    answer_relevancy_response = call_builtin(
        "SNOWFLAKE.CORTEX.COMPLETE", lit(model), answer_relevancy_prompt
    ).alias("ANSWER_RELEVANCY_RESPONSE")

    context_precision_response = call_builtin(
        "SNOWFLAKE.CORTEX.COMPLETE", lit(model), context_precision_prompt
    ).alias("CONTEXT_PRECISION_RESPONSE")

    context_recall_response = call_builtin(
        "SNOWFLAKE.CORTEX.COMPLETE", lit(model), context_recall_prompt
    ).alias("CONTEXT_RECALL_RESPONSE")

    # Add all metric responses to DataFrame
    result_snowpark = temp_df.select(
        "*",
        faithfulness_response,
        answer_relevancy_response,
        context_precision_response,
        context_recall_response,
    )

    # Convert to pandas
    result_df = result_snowpark.to_pandas()
    result_df.columns = [c.lower() for c in result_df.columns]

    print("  → Parsing metric responses...")

    # Parse JSON responses and extract scores
    def parse_metric_response(response_text: str) -> dict:
        """Parse JSON response from LLM judge."""
        if not isinstance(response_text, str):
            return {"score": 0.0, "explanation": "Invalid response"}

        response_text = response_text.strip()

        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = (
                    response_text.split("```")[1].split("```")[0].strip()
                )

            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: try to find JSON object in text
            import re

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {
                "score": 0.0,
                "explanation": "Failed to parse",
                "error": response_text[:100],
            }

    # Parse all metric responses
    result_df["faithfulness_parsed"] = result_df["faithfulness_response"].apply(
        parse_metric_response
    )
    result_df["answer_relevancy_parsed"] = result_df[
        "answer_relevancy_response"
    ].apply(parse_metric_response)
    result_df["context_precision_parsed"] = result_df[
        "context_precision_response"
    ].apply(parse_metric_response)
    result_df["context_recall_parsed"] = result_df[
        "context_recall_response"
    ].apply(parse_metric_response)

    # Extract scores and explanations
    result_df["faithfulness_score"] = result_df["faithfulness_parsed"].apply(
        lambda x: x.get("score", 0.0)
    )
    result_df["faithfulness_explanation"] = result_df[
        "faithfulness_parsed"
    ].apply(lambda x: x.get("explanation", ""))

    result_df["answer_relevancy_score"] = result_df[
        "answer_relevancy_parsed"
    ].apply(lambda x: x.get("score", 0.0))
    result_df["answer_relevancy_explanation"] = result_df[
        "answer_relevancy_parsed"
    ].apply(lambda x: x.get("explanation", ""))

    result_df["context_precision_score"] = result_df[
        "context_precision_parsed"
    ].apply(lambda x: x.get("score", 0.0))
    result_df["context_precision_explanation"] = result_df[
        "context_precision_parsed"
    ].apply(lambda x: x.get("explanation", ""))

    result_df["context_recall_score"] = result_df[
        "context_recall_parsed"
    ].apply(lambda x: x.get("score", 0.0))
    result_df["context_recall_explanation"] = result_df[
        "context_recall_parsed"
    ].apply(lambda x: x.get("explanation", ""))

    # Calculate average score
    result_df["average_score"] = (
        result_df["faithfulness_score"]
        + result_df["answer_relevancy_score"]
        + result_df["context_precision_score"]
        + result_df["context_recall_score"]
    ) / 4

    # Drop intermediate columns
    result_df = result_df.drop(
        columns=[
            "faithfulness_response",
            "answer_relevancy_response",
            "context_precision_response",
            "context_recall_response",
            "faithfulness_parsed",
            "answer_relevancy_parsed",
            "context_precision_parsed",
            "context_recall_parsed",
        ]
    )

    # Clean up temporary table
    session.sql(f"DROP TABLE IF EXISTS {temp_table}").collect()

    print("✓ All metrics computed!")
    return result_df


# ============================================================================
# REPORTING
# ============================================================================


def print_evaluation_metrics(metrics: dict[str, Any]) -> None:
    """Print evaluation metrics in a formatted way."""
    print("\n" + "=" * 80)
    print("EVALUATION METRICS")
    print("=" * 80)
    print(
        f"Faithfulness:       {metrics['faithfulness']['score']:.2f} - {metrics['faithfulness']['explanation']}"
    )
    print(
        f"Answer Relevancy:   {metrics['answer_relevancy']['score']:.2f} - {metrics['answer_relevancy']['explanation']}"
    )
    print(
        f"Context Precision:  {metrics['context_precision']['score']:.2f} - {metrics['context_precision']['explanation']}"
    )
    print(
        f"Context Recall:     {metrics['context_recall']['score']:.2f} - {metrics['context_recall']['explanation']}"
    )
    print(f"\nAverage Score:      {metrics['average_score']:.2f}")
    print("=" * 80)
