# Frozen A/B Demo QA

## Result

The real checkpoint at episode 500 replayed successfully and produced `demo_frozen_episode.json` with 60 synchronized time steps and 120 per-agent decision records. No training or Q update was run.

| Item | Verified result |
|---|---|
| Replay branch / HEAD | `codex/agent-demo-integration` / `79dab6f7b148361abbe494df5a25b411cd4d7aca` (based on `wuxinhan-1`) |
| Checkpoint | `../checkpoint_qtables_run1.json`, key `500`, SHA-256 `01ab763ceff9d5469556dd9829e42faf5bf38be3919cd69231ce69c434cde015` |
| Run manifest | `../run_manifest.json`, SHA-256 `321ee82d1a41c7c317f1216e571fbeca7910e36b73bbef769dc49a67782c2b34` |
| Replay | seed `20261105`, normal volatility, one-way fee `30 bp`, epsilon `0` |
| A / B cost | `19.7462951837 bp` / `21.1715213918 bp` |
| A / B completion | `0.9999999999999997` / `0.9999999999999994`; both report zero unfilled shares (floating-point representation) |
| A / B checkpoint Q states and visit states | `361 / 361` and `380 / 380` |
| A actions | wait 25, half 5, base 2, 1.5x 1, 2x 27 |
| B actions | wait 26, base 4, 1.5x 8, 2x 22 |
| Cost reconciliation residual | A `4.93e-12 bp`; B `4.03e-12 bp` |

## Executed Checks

Run from `multi_agent_execution/`:

```powershell
python -m py_compile export_agent_demo.py
python export_agent_demo.py
```

Both commands passed. The exporter also ran the original `run_advanced_self_play.episode()` and compared its frozen result against the trace export on the same checkpoint, seed and configuration. Costs, completion, unfilled shares and both action-count maps matched exactly; output reported `source_episode_parity=PASS` and `q_table_unchanged=True`.

An independent JSON check passed for: 60 steps; exactly A/B per step; identical pre-trade mid; selected actions and quantities feasible; joint submitted volume equals the two submitted quantities; the four per-step cost terms sum to weighted shortfall; per-step totals reconcile to episode costs; action counts match; no update flag is set; and checkpoint-derived Q-table plus action-visit hashes equal both the recorded pre- and post-replay hashes.

The user-provided front-end screenshot was spot-checked against JSON step 18: displayed mid `99.9460`, A wait / 95,000 shares remaining / Q `-0.6345`, B base-TWAP / 1,666.67 shares / Q `-0.7240`, temporary impact `0.175 bp`, and next mid `99.9485` all match after display rounding. This checks displayed data only, not full front-end interaction behavior.

The bundled front end was also checked with a DOM interaction smoke against the real JSON: it loaded all 60 steps, rendered five actions for both agents, selected step 18 from both slider and chart, displayed the matching A/B actions and market impact, advanced with the play timer, and responded to pause and next-step controls. `node --check demo_frontend/app.js` passed. Static HTTP requests for the page and replay JSON returned 200. This smoke did not measure browser rendering across multiple viewport sizes.

| Agent | Q-table + action-visits SHA-256 before | SHA-256 after |
|---|---|---|
| A | `689650e04fe3870838912acaa43c1bf8ca5a810784b7428eeb9fb9e0ca3c9753` | same |
| B | `7fdec216ab5aeb9f7e410115edcb380a3fc44bcdd6e23432546b01a3770d2601` | same |

## Integration and Provenance Notes

The provided exporter expected `episode(..., trace_rows=...)`, while the target branch's `episode()` has no `trace_rows` parameter. The integrated exporter therefore records the trace in a separate, read-only replay path and requires parity with the repository's original episode function before writing the JSON. No simulator, learning, reward, state/action, matching, or cost source file was changed.

The checkpoint run manifest's `script_sha256` and `schedule_aware_q_sha256` match historical commit `4305cbb4395459fe6edffbb9a8605a0db25bed1c`; the current replay source is `79dab6f7b148361abbe494df5a25b411cd4d7aca`. The run config preserves both the manifest source hashes and current replay source hashes. This distinguishes checkpoint training provenance from demo replay provenance; it does not claim that training ran from the current HEAD.

The generated example is a single frozen replay, not a performance estimate, convergence test, or equilibrium result. The simulator assumes batch fills and does not model queueing, rejects, or partial fills. No broad legacy test suite was rerun because this change is isolated to the demo exporter; no training was started.

## Files

- `demo_frozen_episode.json` — full A/B decision trace.
- `run_config.json` — replay settings, checkpoint/manifest hashes, and current source hashes.
- SHA-256 of the JSON: `69266613bc337259857750c1b7c0da6d3b6da428948408c6acb131c72d9b9c1e`.
- SHA-256 of the run config: `7b45dfd31dc28ae8f010b8c0365a0876cccf5f2a1a4e0b306e9b282bf88e94dd`.
