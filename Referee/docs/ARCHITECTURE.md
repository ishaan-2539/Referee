# Referee Architecture & System Design

## Overview
Referee is a self-hosted Model Context Protocol (MCP) server that provides financial agreement tracking for voice interfaces (Alexa+) and web environments.

                 ┌──────────────────────────────────────────┐
                 │          Alexa+ / Web Simulator          │
                 └────────────────────┬─────────────────────┘
                                      │ Streamable HTTP / MCP (2025-11-25)
                                      ▼
                 ┌──────────────────────────────────────────┐
                 │            Referee MCP Server            │
                 │         (Starlette + FastMCP)            │
                 └──────┬──────────────────────────┬────────┘
                        │                          │
          ┌─────────────▼────────────┐   ┌─────────▼────────────┐
          │  Parsing Engine          │   │  Vagueness Detector  │
          │  (Amazon Bedrock Nova +  │   │  (Pure Python        │
          │   Regex Fallback)        │   │   `vagueterms`)      │
          └──────────────────────────┘   └──────────────────────┘
                                                   │
                                         ┌─────────▼────────────┐
                                         │  Append-Only Event   │
                                         │  Store (SQLite)      │
                                         └─────────┬────────────┘
                                                   │
                                         ┌─────────▼────────────┐
                                         │  Verdict Engine      │
                                         │  (Deterministic)     │
                                         └──────────────────────┘

## Core Principles
1. **Model Parses, Rules Decide:** LLMs parse fuzzy utterances into slot structures. Deterministic rule engines evaluate vagueness and calculate verdicts.
2. **Append-Only Ledger:** Deal states are never overwritten. Every action (`created`, `term_set`, `locked`, `payment`, `amended`) appends a immutable event.
3. **Zero Network Dependencies on Core:** The vagueness detector and verdict engines are pure Python functions that operate offline without external APIs.