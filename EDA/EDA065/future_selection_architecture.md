# Future source selection architecture

1. Resolve an explicit filename when present.
2. Run the existing Strict Resolver.
3. Keep its output when the source contract is resolved and confidence/content verification is sufficient.
4. Fall back only for not-applicable, empty, ambiguous, contradictory, or low-confidence selections.
5. Build generic Top-5 candidates and compact document probes.
6. Ask a future planner to choose only among those probes.
7. Expand to Top-10 when Top-5 cannot establish a document.
8. Suppress when ambiguity remains.

For multiple documents, preserve required roles and evaluate set recall. Same-name documents require normalized path/project identity. Companyless questions must not default to internal-only; retain external candidates until a content probe establishes scope. Seating layouts should prefer PPTX/XML or Excel coordinate executors; Vision is a fallback when native structure cannot resolve the relation.
