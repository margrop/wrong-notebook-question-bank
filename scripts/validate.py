#!/usr/bin/env python3
"""校验 index.json 与题库包：格式、题数、sha256、必填字段与题型取值。"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGES = {"primary", "junior_high", "senior_high", "university"}
SUBJECTS = {"math", "english", "chinese", "science", "physics", "chemistry", "biology", "history", "geography", "politics"}
QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false", "fill_blank", "calculation", "solution", "reading", "cloze", "writing", "other"}


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    if index.get("format") != "wrong-notebook-question-bank-index" or index.get("version") != 1:
        fail("index format/version")
    seen = set()
    total = 0
    for package in index["packages"]:
        pid = package["id"]
        if pid in seen:
            fail(f"duplicate package id {pid}")
        seen.add(pid)
        path = ROOT / package["file"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != package["sha256"]:
            fail(f"{pid}: sha256 mismatch")
        if len(raw) != package["sizeBytes"]:
            fail(f"{pid}: sizeBytes mismatch")
        body = json.loads(raw.decode("utf-8"))
        if body.get("format") != "wrong-notebook-question-bank" or body.get("version") != 1:
            fail(f"{pid}: bank format/version")
        meta = body["meta"]
        if meta["stage"] not in STAGES or meta["subject"] not in SUBJECTS:
            fail(f"{pid}: meta stage/subject")
        questions = body["questions"]
        if meta["count"] != len(questions) or package["count"] != len(questions):
            fail(f"{pid}: count mismatch")
        for question in questions:
            if question.get("stage", meta["stage"]) not in STAGES:
                fail(f"{pid}: question stage {question.get('id')}")
            if question.get("subjectKey", meta["subject"]) not in SUBJECTS:
                fail(f"{pid}: question subject {question.get('id')}")
            if not str(question.get("text") or "").strip():
                fail(f"{pid}: empty text {question.get('id')}")
            if question.get("questionType") not in QUESTION_TYPES:
                fail(f"{pid}: question type {question.get('id')}")
            points = question.get("knowledgePoints") or []
            if len(points) > 100:
                fail(f"{pid}: too many knowledge points {question.get('id')}")
        total += len(questions)
    print(f"OK: {len(index['packages'])} packages, {total} questions")


if __name__ == "__main__":
    main()
