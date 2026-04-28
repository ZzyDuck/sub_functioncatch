---
name: "playwright-test"
description: "Processes test cases from JSON file and returns test results. Invoke when user needs to run tests based on JSON test cases and save results."
---

# Playwright Test Skill

This skill processes test cases from a JSON file and returns test results. It is designed to:

1. Read test cases from a specified JSON file
2. Process each test case according to its steps and expected results
3. Generate test results with status and details
4. Save the results to a specified JSON file

## Usage

When the user provides a JSON file containing test cases, this skill will:
- Parse the test cases
- Execute the tests (simulated)
- Generate results with pass/fail status
- Save the results to the specified output file

## Example Input/Output

### Input:
A JSON file with test cases, each containing:
- id: Test case ID
- module: Test module
- scene: Test scenario
- precondition: Test preconditions
- steps: Test steps
- expected: Expected results
- assertion: Assertion type
- timeout_ms: Timeout in milliseconds

### Output:
A JSON file with test results, each containing:
- id: Test case ID
- status: Test status (PASS/FAIL)
- message: Test result message
- details: Additional details if needed