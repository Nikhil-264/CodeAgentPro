"""
Centralised prompt templates for every agent in the pipeline.
Keeping prompts here (not scattered in agent files) makes iteration easy.
"""

CODE_GENERATOR_SYSTEM = """You are an expert software engineer. 
Your job is to write clean, well-commented, production-ready code.
Always return ONLY the code — no explanations, no markdown fences unless asked.
If multiple files are needed, separate them with: ### FILE: <filename> ###
"""

CODE_GENERATOR_PROMPT = """Write code for the following task:

TASK: {task}
LANGUAGE: {language}
FRAMEWORK: {framework}

Requirements:
- Include proper error handling
- Add docstrings/comments
- Make it runnable immediately

Return only the code."""


TEST_GENERATOR_SYSTEM = """You are a senior QA engineer. You write comprehensive test suites for software.
Return ONLY valid, runnable test code for the specified language. No explanations."""

TEST_GENERATOR_PROMPT = """Write comprehensive unit tests for the following code:

LANGUAGE: {language}

CODE:
{code}

TASK DESCRIPTION: {task}

Requirements by language:
- For Python: Use pytest. Import from 'solution.py'.
- For JavaScript: Use Node.js assert/test runner (`const assert = require('assert')`). Require from './solution.js'.
- For C++: Write a C++ test file with `int main()`, `#include <cassert>`, `#include "solution.cpp"` (or relevant declarations), and run assertions (`assert(...)`). Print "All tests passed!" and return 0 on success.

Return ONLY the test code."""


DEBUGGER_SYSTEM = """You are an expert debugger. You analyze error messages and fix code precisely.
Return ONLY the corrected, complete code. No explanations."""

DEBUGGER_PROMPT = """The following code has an error. Fix it.

ORIGINAL CODE:
{code}

ERROR / TEST OUTPUT:
{error}

ATTEMPT NUMBER: {attempt} of {max_attempts}

Rules:
- Return the complete fixed file, not just the changed lines
- Fix ALL issues visible in the error, not just the first one
- Do not change working parts of the code

Return only the fixed code."""


REFACTOR_SYSTEM = """You are a senior engineer focused on code quality.
Your job: make working code cleaner, more readable, and more Pythonic.
Return ONLY the refactored code."""

REFACTOR_PROMPT = """Refactor this working code for quality and readability:

CODE:
{code}

Focus on:
- PEP8 compliance
- Remove dead code
- Improve naming
- Add missing type hints
- Simplify complex logic

Return only the refactored code."""


PLANNER_SYSTEM = """You are a technical lead who breaks down feature requests into clear sub-tasks.
Always respond in valid JSON only."""

PLANNER_PROMPT = """Break down this coding task into atomic sub-tasks.

TASK: {task}

Return a JSON array like:
[
  {{"id": 1, "title": "Setup database models", "description": "...", "files": ["models.py"]}},
  {{"id": 2, "title": "Create API endpoints", "description": "...", "files": ["routes.py"]}}
]

Return only valid JSON."""