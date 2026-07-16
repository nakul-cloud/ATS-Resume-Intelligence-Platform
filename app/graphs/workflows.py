from langgraph.graph import END, START, StateGraph

# Import edges
from app.graphs.edges.parser_edges import route_parsing
from app.graphs.edges.self_eval_edges import route_self_eval
from app.graphs.nodes.interview_nodes import ie_evaluate_answer_node

# Import nodes
from app.graphs.nodes.parser_nodes import rp_extract_node, rp_parse_node, rp_store_node
from app.graphs.nodes.self_eval_nodes import (
    se_confidence_feedback_node,
    se_decide_node,
    se_error_handler_node,
    se_evaluate_node,
    se_gap_analysis_node,
    se_interview_prep_node,
)

# Import states
from app.graphs.state import InterviewEvalState, ResumeParserState, SelfEvalState

# =====================================================================
# 1. RESILIENT RESUME PARSER WORKFLOW
# =====================================================================

# Build Resume Parser Graph
resume_parser_builder = StateGraph(ResumeParserState)
resume_parser_builder.add_node("extract", rp_extract_node)
resume_parser_builder.add_node("parse", rp_parse_node)
resume_parser_builder.add_node("store", rp_store_node)

# Hook up entry point as standard edge using START
resume_parser_builder.add_edge(START, "extract")
resume_parser_builder.add_edge("extract", "parse")
resume_parser_builder.add_conditional_edges(
    "parse",
    route_parsing,
    {
        "store": "store",
        "parse": "parse",
        "failed": END
    }
)
resume_parser_builder.add_edge("store", END)
resume_parser_app = resume_parser_builder.compile()


# =====================================================================
# 2. AGENTIC SELF-EVALUATION WORKFLOW
# =====================================================================

# Build Self-Evaluation Graph
self_eval_builder = StateGraph(SelfEvalState)
self_eval_builder.add_node("evaluate", se_evaluate_node)
self_eval_builder.add_node("decide", se_decide_node)
self_eval_builder.add_node("confidence_agent", se_confidence_feedback_node)
self_eval_builder.add_node("gap_agent", se_gap_analysis_node)
self_eval_builder.add_node("interview_agent", se_interview_prep_node)
self_eval_builder.add_node("error_handler", se_error_handler_node)

# Hook up entry point as standard edge using START
self_eval_builder.add_edge(START, "evaluate")
self_eval_builder.add_edge("evaluate", "decide")
self_eval_builder.add_conditional_edges(
    "decide",
    route_self_eval,
    {
        "confidence_agent": "confidence_agent",
        "gap_agent": "gap_agent",
        "interview_agent": "interview_agent",
        "error_handler": "error_handler"
    }
)
self_eval_builder.add_edge("confidence_agent", END)
self_eval_builder.add_edge("gap_agent", END)
self_eval_builder.add_edge("interview_agent", END)
self_eval_builder.add_edge("error_handler", END)
agentic_self_eval_app = self_eval_builder.compile()


# =====================================================================
# 3. ADAPTIVE INTERVIEW WORKFLOW
# =====================================================================

# Build Interview Evaluation Graph
interview_eval_builder = StateGraph(InterviewEvalState)
interview_eval_builder.add_node("evaluate_answer", ie_evaluate_answer_node)

# Hook up entry point as standard edge using START
interview_eval_builder.add_edge(START, "evaluate_answer")
interview_eval_builder.add_edge("evaluate_answer", END)
interview_eval_app = interview_eval_builder.compile()
