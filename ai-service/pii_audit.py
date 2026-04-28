"""
pii_audit.py - PII Audit Script
Tool-21: Audit Planning and Scheduling
AI Developer 3 - Day 9 Task

HOW TO RUN:
    python pii_audit.py
"""

import os
import re

# PII PATTERNS TO SEARCH FOR
PII_PATTERNS = {
    "Email Address":     r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",
    "Phone Number":      r"\b(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
    "Credit Card":       r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
    "Password in code":  r"(password|passwd|pwd)\s*=\s*['\"].+['\"]",
    "API Key hardcoded": r"(api_key|apikey|secret|token)\s*=\s*['\"][a-zA-Z0-9_\-]{10,}['\"]",
    "National ID":       r"\b\d{3}-\d{2}-\d{4}\b",
}

# DANGEROUS LOG PATTERNS
DANGEROUS_LOG_PATTERNS = {
    "Logging full request body": r"log(ger)?\.(info|debug|warning|error)\s*\(.*request\.(body|data|json)",
    "Logging password":          r"log(ger)?\.(info|debug|warning|error)\s*\(.*password",
    "Print sensitive data":      r"print\s*\(.*password",
}

# FILES TO CHECK
FILES_TO_CHECK = [
    "app.py",
    "routes/sanitisation.py",
    "security_test.py",
]

results = []
total_issues = 0


def scan_file(filepath, patterns, scan_type):
    issues = []
    if not os.path.exists(filepath):
        return issues

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "os.getenv" in line or "os.environ" in line:
                    continue
                if "${" in line:
                    continue
                issues.append({
                    "file": filepath,
                    "line": line_num,
                    "type": scan_type,
                    "pattern": pattern_name,
                    "content": line.strip()[:80]
                })
    return issues


print("")
print("="*60)
print("TOOL-21 PII AUDIT REPORT")
print("AI Developer 3 - Day 9")
print("="*60)

for filepath in FILES_TO_CHECK:
    print("")
    print(f"--- Scanning: {filepath} ---")

    pii_issues = scan_file(filepath, PII_PATTERNS, "PII Data")
    log_issues = scan_file(filepath, DANGEROUS_LOG_PATTERNS, "Dangerous Logging")
    all_issues = pii_issues + log_issues

    if not all_issues:
        print(f"CLEAN - No PII or dangerous logging found!")
    else:
        for issue in all_issues:
            print(f"WARNING Line {issue['line']}: [{issue['pattern']}] -> {issue['content']}")
            total_issues += 1

    results.append({"file": filepath, "issues": all_issues})

print("")
print("="*60)
print("PII AUDIT SUMMARY")
print("="*60)
print(f"Files Scanned  : {len(FILES_TO_CHECK)}")
print(f"Total Issues   : {total_issues}")
if total_issues == 0:
    print("Result         : CLEAN - No PII leaks found!")
else:
    print("Result         : Issues found - review above")
print("="*60)
