"""Multi-agent layer for the SJ Project Planner Agent.

Each agent is a thin wrapper around an LLM call with a structured-JSON contract
plus a deterministic rule-based fallback so the demo runs without Azure OpenAI.
The wiring is compatible with the Microsoft Agent Framework: each class exposes
an async ``run`` method that accepts a typed input and returns a typed output.
"""
