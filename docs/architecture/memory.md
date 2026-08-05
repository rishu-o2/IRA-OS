# Memory Engine Architecture

## Overview

The Memory Engine is the kernel's persistent knowledge layer. It provides a structured, immutable, and rule-based memory subsystem for IRA OS without depending on Brain, Planner, Tools, Android, Desktop, or application-specific modules.

The Memory Engine stores facts and metadata, supports retrieval and tagging, and exposes retention policies for forgetting. It is intentionally in-memory only in Milestone 7.

## Core Responsibilities

- Store immutable `MemoryRecord` objects.
- Maintain indexes for fast lookup by id, namespace, tags, and owner.
- Support deterministic search with `SearchQuery`.
- Expose retention policies for cleanup and expiration.
- Publish lifecycle events for memory operations.
- Remain independent of the future reasoning/LLM layers.

## Package Structure

- `core/memory/exceptions.py` — Domain-specific exception hierarchy.
- `core/memory/models.py` — Immutable dataclasses for `MemoryRecord`, `SearchQuery`, `SearchResult`, and `MemoryStats`.
- `core/memory/store.py` — Storage-only layer for memory records.
- `core/memory/indexes.py` — In-memory indexes for O(1) lookup.
- `core/memory/search.py` — Rule-based search engine without AI.
- `core/memory/retention.py` — Forgetting policies and cleanup orchestration.
- `core/memory/manager.py` — Facade that composes storage, search, retention, and events.
- `core/memory/memory_module.py` — DI registration for the kernel container.

## Design Principles

- Immutable public models.
- JSON-serializable content only.
- No persistence, embeddings, or semantic ranking in Milestone 7.
- Strong separation between storage, search, retention, and orchestration.
- Events emitted for all mutation operations.
- Lifecycle hooks for `start()` and `shutdown()` to fit the kernel.

## Future Extensions

This architecture is designed so persistence, backups, export/import, and semantic search can be added later without changing the kernel-facing APIs.
