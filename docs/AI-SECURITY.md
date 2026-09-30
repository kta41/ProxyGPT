# AI guardrails and OWASP-aligned tests

## Implemented scope

The current deterministic guardrails are wired into the standalone
`proxygpt-rag` CLI:

- User questions have an 8,000-character limit and are rejected when common
  credential, email, or SSN patterns are detected.
- Generated answers are blocked if they match those sensitive-data patterns.
- A bracketed source citation is accepted only when its exact identifier was
  returned by retrieval.
- Retrieved passages are serialized as untrusted evidence in a separate user
  message; the generator's system message says not to treat evidence as
  instructions. The CLI does not provide tools to the generator.

The detectors are intentionally simple patterns. They are not a general
prompt-injection classifier, DLP engine, or guarantee that the model cannot
disclose sensitive information. False positives and new credential formats
remain possible.

These checks protect only the standalone RAG CLI `search` / `ask` flow. They
do not intercept Open WebUI chat requests, user-uploaded files processed by
Open WebUI, or remote MCP/Tavily requests. Do not use these tests as evidence
that the complete platform is OWASP-certified or resistant to attacks.

## OWASP mapping and tests

`rag/tests/test_owasp_guardrails.py` contains offline, deterministic regression
tests:

| OWASP LLM risk | Tested behavior |
| --- | --- |
| LLM01 Prompt Injection | Retrieved hostile text stays in untrusted evidence and cannot replace the system message. |
| LLM02 Sensitive Information Disclosure | Common credential and personal-data patterns are rejected in questions and generated answers. |
| LLM05 Improper Output Handling | Citations outside the retrieved evidence are rejected before output. |
| LLM06 Excessive Agency | The RAG generator request does not define tools. |
| LLM10 Unbounded Consumption | Oversized questions are rejected before retrieval. |

Run the tests:

```bash
python3 -m pip install -e ./rag
python3 -m unittest discover -s rag/tests -v
```

These are control regression tests, not a complete OWASP Top 10 evaluation.
The next security step is a separate adversarial suite for direct and indirect
prompt injection, RAG poisoning, output policy violations, and unauthorized
tool use, followed by a runtime filter for normal Open WebUI conversations.

## MCP exposure

The configured MCP endpoint is the Tavily search proxy. It is a ClusterIP
service; NetworkPolicy permits Open WebUI ingress and HTTPS egress. Search
queries are sent to Tavily, an external provider. Do not include credentials,
personal data, or confidential document text in a search query. No
user-by-user MCP authorization or action audit log is currently provided.
