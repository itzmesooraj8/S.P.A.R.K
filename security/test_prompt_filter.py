import pytest
from security.prompt_filter import scan_prompt, PromptScanResult

def test_scan_prompt_none_input():
    result = scan_prompt(None)
    assert result == PromptScanResult(score=0.0, suspicious=False, reasons=())

def test_scan_prompt_empty_string():
    result = scan_prompt("")
    assert result == PromptScanResult(score=0.0, suspicious=False, reasons=())

def test_scan_prompt_normal_prompt():
    result = scan_prompt("Hello, what is the capital of France?")
    assert result == PromptScanResult(score=0.0, suspicious=False, reasons=())

def test_scan_prompt_single_injection():
    result = scan_prompt("Please ignore previous instructions.")
    assert result.score == 0.25
    assert result.suspicious is False
    assert "ignore previous instructions" in result.reasons

def test_scan_prompt_multiple_injections():
    result = scan_prompt("system prompt jailbreak")
    assert result.score == 0.5
    assert result.suspicious is True
    assert "system prompt" in result.reasons
    assert "jailbreak" in result.reasons

def test_scan_prompt_capped_score():
    result = scan_prompt("ignore previous instructions disregard the above system prompt developer message jailbreak")
    assert result.score == 1.0
    assert result.suspicious is True
    assert len(result.reasons) == 5

def test_scan_prompt_code_fences():
    result = scan_prompt("Here is some code:\n```python\nprint('hello')\n```")
    assert result.score == 0.1
    assert result.suspicious is False
    assert "code_fence" in result.reasons

def test_scan_prompt_long_content():
    long_text = "a" * 1201
    result = scan_prompt(long_text)
    assert result.score == 0.1
    assert result.suspicious is False
    assert "long_content" in result.reasons

def test_scan_prompt_mixed():
    long_text = "a" * 1201
    prompt = f"ignore previous instructions ```code```\n```more code```\n{long_text}"
    result = scan_prompt(prompt)
    assert result.score == 0.45  # 0.25 + 0.1 + 0.1
    assert result.suspicious is False
    assert "ignore previous instructions" in result.reasons
    assert "code_fence" in result.reasons
    assert "long_content" in result.reasons
