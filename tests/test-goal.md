# Test Goal: Add a new code grader type to BioAgentEval

Add a "json_schema" code grader that validates agent responses against a JSON schema. The grader should:
- Accept a JSON schema as part of the task definition
- Validate the agent's response against the schema
- Return pass/fail with specific validation errors
- Include unit tests
