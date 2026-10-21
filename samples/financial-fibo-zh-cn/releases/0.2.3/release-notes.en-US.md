# Local candidate0.2.3 — pending complete acceptance

Requires OpenBKN >=0.2.1 <0.3.0. Not published or added to the official catalogue.

- Preserve independently complete issuer amounts and proved zero totals while keeping incomplete or zero-denominator ratios unknown. Missing opening coverage cannot become zero.
- Add bounded request-local dated observations to the same three native functions; retain four required scalar inputs. Batch limits:20 portfolios,12 observations including the base,3MiB UTF8 output. Scalar calls retain200 portfolios. Real execution boundaries require separate validation.
- Align bilingual business requirements, Skill and BKN runtime guidance; one native call per run_code, scoped projections, independent dates/evidence and explicit unknowns.
- Clarify public identity-field ownership, Boolean representation, controlled values, zero-balance audit scope and displayed rounding. Original0.2.2 grades remain immutable; this version needs fresh complete regression runs and live perturbations.
- Keep the20 locked data tables and all fictional records unchanged in both languages.

Multi-observation requests allow at most 20 portfolios and 12 observations including the base; scalar requests retain the 200-portfolio input bound. The guard measures the complete compact JSON serialization as UTF-8 bytes and rejects results above 3 MiB. Native platform preflight observed a 4 MiB result quota; the 3 MiB application guard leaves transport headroom. These input-count bounds do not guarantee that every maximum-size input succeeds: result size depends on records and evidence. On a limit failure reduce portfolios or observations; never truncate required rows or evidence. The revised candidate still requires native platform validation and complete acceptance.
