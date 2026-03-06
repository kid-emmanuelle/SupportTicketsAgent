"""Batch evaluation runner."""

from pathlib import Path
import sys

import pandas as pd


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.support_agent.config import Settings, get_settings
from src.support_agent.cortex_agent.rest_client import CortexAgentsRestClient
from src.support_agent.cortex_agent.service import get_cortex_rest_client
from src.support_agent.eval.data_sampling import (
    create_stratified_sample,
    get_tickets_data,
    print_sample_statistics,
)
from src.support_agent.eval.scoring import (
    compute_rag_metrics_batch,
    extract_context_from_agent_output,
    generate_agent_completion,
)
from src.support_agent.snowflake_client import Session, create_snowpark_session


# ============================================================================
# PIPELINE CONFIGURATION
# ============================================================================

EVALUATION_CONFIG = {
    "input_table_name": "PROJECT_DB.CURATED.TICKETS_CLEANED",
    "output_table_name": "PROJECT_DB.EVAL.TESTSET",
    "results_table_name": "PROJECT_DB.EVAL.RESULTS",
    "samples_per_combination": 2,
    "stratify_columns": ["type", "priority", "language"],  # 24 different values
    "random_state": 42,
    "run_evaluation": True,
    "evaluation_model": "claude-3-5-sonnet",
}


# ============================================================================
# BATCH EVALUATION
# ============================================================================


def run_batch_evaluation(
    session: Session,
    settings: Settings,
    client_agent: CortexAgentsRestClient,
    sample_df: pd.DataFrame,
    evaluation_model: str,
) -> pd.DataFrame:
    """Run evaluation on all samples in the test set."""
    print("\n" + "=" * 80)
    print("BATCH EVALUATION - AGENT RESPONSES")
    print("=" * 80)

    evaluation_data = []
    total = len(sample_df)

    # Step 1: Generate agent responses for all samples
    for idx, row in sample_df.iterrows():
        print(f"\nGenerating response for ticket {idx + 1}/{total}...")

        query = row["rewritten_body"]
        ground_truth = row["cleaned_answer"]

        # Generate agent response
        agent_output = generate_agent_completion(settings, client_agent, query)
        context = extract_context_from_agent_output(agent_output)

        evaluation_data.append(
            {
                "ticket_id": idx,
                "language": row.get("language", "N/A"),
                "priority": row.get("priority", "N/A"),
                "type": row.get("type", "N/A"),
                "query": query,
                "ground_truth": ground_truth,
                "agent_answer": agent_output["agent_answer"],
                "context": context,
                "used_search": agent_output["used_search_tools"],
                "agent_model": agent_output["agent_model_name"],
                "total_input_tokens": agent_output[
                    "total_context_input_tokens"
                ],
                "total_output_tokens": agent_output["total_output_tokens"],
            }
        )

    print("\n✓ All agent responses generated!")

    # Step 2: Compute all metrics in Snowflake (batch processing)
    print("\n" + "=" * 80)
    print("BATCH EVALUATION - COMPUTING METRICS")
    print("=" * 80)

    evaluation_df = pd.DataFrame(evaluation_data)
    return compute_rag_metrics_batch(
        session, evaluation_df, model=evaluation_model
    )


# ============================================================================
# MAIN EVALUATION FUNCTION
# ============================================================================


def main():
    """Run batch evaluation on stratified sample."""
    # Initialize Snowflake session
    settings = get_settings()
    session = create_snowpark_session(settings)

    try:
        print("=" * 80)
        print("EVALUATION PIPELINE - SAMPLE CREATION")
        print("=" * 80)

        print("\nStep 1: Fetching tickets data...")
        df = get_tickets_data(session, EVALUATION_CONFIG["input_table_name"])
        print(f"✓ Loaded {len(df)} tickets")
        df=df.sample(100)

        print("\nStep 2: Creating stratified sample...")
        sample = create_stratified_sample(
            df,
            samples_per_combination=EVALUATION_CONFIG[
                "samples_per_combination"
            ],
            stratify_columns=EVALUATION_CONFIG["stratify_columns"],
            random_state=EVALUATION_CONFIG["random_state"],
        )
        print(f"✓ Created sample with {len(sample)} tickets")

        print_sample_statistics(sample, "STRATIFIED SAMPLE STATISTICS")

        print("\nStep 3: Saving sample to Snowflake...")
        df_snowpark = session.create_dataframe(sample)
        df_snowpark.write.mode("overwrite").save_as_table(
            EVALUATION_CONFIG["output_table_name"]
        )
        print(f"✓ Saved to {EVALUATION_CONFIG['output_table_name']}")

        # Run evaluation if enabled
        if EVALUATION_CONFIG["run_evaluation"]:
            print("\nStep 4: Running batch evaluation...")
            client_agent = get_cortex_rest_client(settings)

            results_df = run_batch_evaluation(
                session,
                settings,
                client_agent,
                sample,
                evaluation_model=EVALUATION_CONFIG["evaluation_model"],
            )

            print("\nStep 5: Saving evaluation results...")
            results_snowpark = session.create_dataframe(results_df)
            results_snowpark.write.mode("overwrite").save_as_table(
                EVALUATION_CONFIG["results_table_name"]
            )
            print(f"✓ Saved to {EVALUATION_CONFIG['results_table_name']}")

            # Print summary statistics
            print("\n" + "=" * 80)
            print("EVALUATION SUMMARY")
            print("=" * 80)
            print(f"Total tickets evaluated: {len(results_df)}")
            print("\nAverage Scores:")
            print(
                f"  Faithfulness:      {results_df['faithfulness_score'].mean():.3f}"
            )
            print(
                f"  Answer Relevancy:  {results_df['answer_relevancy_score'].mean():.3f}"
            )
            print(
                f"  Context Precision: {results_df['context_precision_score'].mean():.3f}"
            )
            print(
                f"  Context Recall:    {results_df['context_recall_score'].mean():.3f}"
            )
            print(
                f"  Overall Average:   {results_df['average_score'].mean():.3f}"
            )

            if "language" in results_df.columns:
                print("\nBy Language:")
                print(results_df.groupby("language")["average_score"].mean())

            if "priority" in results_df.columns:
                print("\nBy Priority:")
                print(results_df.groupby("priority")["average_score"].mean())

        print("\n" + "=" * 80)
        print("EVALUATION PIPELINE COMPLETE!")
        print("=" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    main()
