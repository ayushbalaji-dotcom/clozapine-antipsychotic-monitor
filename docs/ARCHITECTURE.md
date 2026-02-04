# Architecture

## Overview
The system ingests medication orders and monitoring events, calculates monitoring schedules, and exposes a worklist UI with audit trails.

## Components
- FastAPI backend (API + scheduling engine)
- PostgreSQL (pseudonymised data only; identifiers disabled by default)
- Jinja2 server-rendered UI (minimal)
- Ruleset JSON (versioned monitoring schedules)

## Data Flow
EPR export -> CSV upload -> Tracker -> Worklist + Notifications

## Tech Stack Rationale
- FastAPI: lean, typed, OpenAPI generation
- PostgreSQL: reliable relational store with JSON and UUID support
- Jinja2: minimal UI with low attack surface
