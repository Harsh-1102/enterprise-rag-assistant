"""
evaluation.py - Comprehensive RAG Evaluation Framework

Evaluates RAG performance across:
1. Retrieval Hit Rate (Hit@K) & Document Precision
2. Context Relevance
3. Answer Correctness / Semantic Similarity
4. Groundedness / Faithfulness (Context-to-Answer overlap)
5. Hallucination Detection Rate (especially on out-of-domain questions)
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from src.rag_pipeline import INSUFFICIENT_INFO_RESPONSE, RAGPipeline

# Gold-standard benchmark evaluation dataset for Enterprise HR domain
HR_BENCHMARK_DATASET: List[Dict[str, Any]] = [
    {
        "id": "Q01",
        "question": (
            "What is the annual paid leave entitlement for "
            "full-time employees?"
        ),
        "expected_source": "Leave_Policy.pdf",
        "expected_answer": (
            "Full-time employees receive 20 days of paid annual leave per "
            "calendar year, accrued monthly at 1.67 days."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q02",
        "question": (
            "How many days of sick leave can an employee take "
            "without a medical certificate?"
        ),
        "expected_source": "Leave_Policy.pdf",
        "expected_answer": (
            "Employees may take up to 2 consecutive days of sick leave "
            "without a medical certificate; 3 or more days requires a "
            "doctor note."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q03",
        "question": (
            "What are the core hours when all employees must be available "
            "under the Work From Home policy?"
        ),
        "expected_source": "Work_From_Home_Policy.pdf",
        "expected_answer": (
            "Employees working remotely must be active and available during "
            "core hours between 10:00 AM and 4:00 PM local time."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q04",
        "question": (
            "What is the standard notice period required for "
            "employee resignation?"
        ),
        "expected_source": "Employee_Handbook.pdf",
        "expected_answer": (
            "The standard resignation notice period is 30 calendar days for "
            "permanent employees, or 15 days during probation."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q05",
        "question": (
            "What are the attendance tracking rules and how is "
            "tardiness handled?"
        ),
        "expected_source": "Attendance_Policy.docx",
        "expected_answer": (
            "Employees must clock in within a 15-minute grace period. "
            "Three unexcused late arrivals within a calendar month "
            "trigger a written warning."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q06",
        "question": (
            "What health and wellness insurance coverage is provided to "
            "employees and dependents?"
        ),
        "expected_source": "Employee_Benefits.pdf",
        "expected_answer": (
            "The company provides comprehensive medical, dental, and vision "
            "insurance covering eligible dependents up to $500,000 annual "
            "maximum."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q07",
        "question": (
            "What is the company policy regarding workplace harassment "
            "and reporting misconduct?"
        ),
        "expected_source": "Code_Of_Conduct.docx",
        "expected_answer": (
            "Zero tolerance for harassment, discrimination, or retaliation; "
            "reports can be filed via HR or the anonymous ethics hotline."
        ),
        "category": "in_domain",
    },
    {
        "id": "Q08",
        "question": (
            "What is the capital of France and what is its population?"
        ),
        "expected_source": "NONE",
        "expected_answer": INSUFFICIENT_INFO_RESPONSE,
        "category": "out_of_domain",
    },
    {
        "id": "Q09",
        "question": "Who won the FIFA World Cup in 2022?",
        "expected_source": "NONE",
        "expected_answer": INSUFFICIENT_INFO_RESPONSE,
        "category": "out_of_domain",
    },
]


class RAGEvaluator:
    """Automated evaluation suite for Retrieval-Augmented Generation."""

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline

    @staticmethod
    def _tokenize(text: str) -> set:
        """Tokenizes text into lowercase word tokens, ignoring punctuation."""
        return set(re.findall(r"\w+", text.lower()))

    def calculate_token_f1(self, prediction: str, ground_truth: str) -> float:
        """Computes word-level token overlap F1 score."""
        pred_tokens = self._tokenize(prediction)
        gt_tokens = self._tokenize(ground_truth)

        if not pred_tokens or not gt_tokens:
            return 0.0

        common = pred_tokens.intersection(gt_tokens)
        if not common:
            return 0.0

        precision = len(common) / len(pred_tokens)
        recall = len(common) / len(gt_tokens)
        return round(2 * (precision * recall) / (precision + recall), 3)

    def calculate_groundedness(
        self, answer: str, context_chunks: List[str]
    ) -> float:
        """
        Estimates answer groundedness (faithfulness):
        Calculates percentage of informative words in the answer that appear
        directly in the retrieved document chunks.
        """
        if not context_chunks or not answer.strip():
            return 0.0

        if INSUFFICIENT_INFO_RESPONSE in answer:
            # Fallback triggered properly, considered 100% grounded
            return 1.0

        # Gather context vocabulary
        context_text = " ".join(context_chunks).lower()
        context_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", context_text))

        # Stop words to ignore
        stopwords = {
            "the", "and", "is", "in", "to", "of", "for", "with", "a", "an",
            "on", "at", "this", "that", "from", "by", "as", "are", "be",
            "was", "will", "or", "have", "has", "had", "can", "should",
            "could", "may", "must", "per", "our", "all"
        }

        answer_words = [
            w for w in re.findall(r"\b[a-zA-Z]{3,}\b", answer.lower())
            if w not in stopwords
        ]

        if not answer_words:
            return 1.0

        supported_words = [w for w in answer_words if w in context_words]
        return round(len(supported_words) / len(answer_words), 3)

    def evaluate_item(
        self, item: Dict[str, Any], top_k: int = 4
    ) -> Dict[str, Any]:
        """Evaluates a single benchmark test sample."""
        question = item["question"]
        expected_source = item["expected_source"]
        expected_answer = item["expected_answer"]
        category = item["category"]

        # Run RAG pipeline
        response = self.pipeline.query(question, top_k=top_k)
        retrieved_files = [c.filename for c in response.retrieved_chunks]
        context_texts = [c.text for c in response.retrieved_chunks]

        # 1. Retrieval Hit@K
        if category == "out_of_domain":
            thresh = self.pipeline.similarity_threshold
            below_thresh = response.retrieval_confidence < thresh
            retrieval_hit = (
                below_thresh or INSUFFICIENT_INFO_RESPONSE in response.answer
            )
        else:
            retrieval_hit = any(
                expected_source.lower() in f.lower() for f in retrieved_files
            )

        # 2. Answer F1 Score against reference
        answer_f1 = self.calculate_token_f1(response.answer, expected_answer)

        # 3. Groundedness / Faithfulness
        groundedness = self.calculate_groundedness(
            response.answer, context_texts
        )

        # 4. Hallucination Check
        if category == "out_of_domain":
            is_hallucinating = (
                INSUFFICIENT_INFO_RESPONSE not in response.answer
            )
        else:
            is_hallucinating = (
                groundedness < 0.45
                and INSUFFICIENT_INFO_RESPONSE not in response.answer
            )

        preview = (
            response.answer[:150] + "..."
            if len(response.answer) > 150
            else response.answer
        )

        return {
            "id": item["id"],
            "question": question,
            "category": category,
            "expected_source": expected_source,
            "retrieved_sources": list(set(retrieved_files)),
            "retrieval_hit": retrieval_hit,
            "confidence_score": response.retrieval_confidence,
            "groundedness": groundedness,
            "answer_f1": answer_f1,
            "hallucination": is_hallucinating,
            "execution_time_sec": response.execution_time,
            "generated_answer": preview,
        }

    def run_benchmark(
        self,
        dataset: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 4
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Runs complete benchmark evaluation and computes aggregate metrics.
        """
        data = dataset or HR_BENCHMARK_DATASET
        results = [self.evaluate_item(item, top_k=top_k) for item in data]
        df = pd.DataFrame(results)

        hit_rate = df["retrieval_hit"].mean()
        avg_groundedness = df["groundedness"].mean()
        avg_f1 = df["answer_f1"].mean()
        hallucination_rate = df["hallucination"].mean()
        avg_latency = df["execution_time_sec"].mean()

        metrics = {
            "Retrieval Hit Rate (Hit@K)": round(float(hit_rate) * 100, 1),
            "Average Groundedness Score": round(
                float(avg_groundedness) * 100, 1
            ),
            "Average Answer F1": round(float(avg_f1) * 100, 1),
            "Hallucination Rate": round(float(hallucination_rate) * 100, 1),
            "Average Latency (seconds)": round(float(avg_latency), 2),
        }

        return df, metrics
