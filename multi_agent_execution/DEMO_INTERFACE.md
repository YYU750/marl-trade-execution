# A/B Agent Demo Interface

This interface exports one frozen replay of the existing simultaneous A/B tabular Q-learning policy for the course front end. It uses the `wuxinhan-1` self-play checkpoint family; it is not the rule-guided Double Q fixed-opponent experiment.

## Run

From `multi_agent_execution/`:

```powershell
python .\export_agent_demo.py
```

Defaults: `outputs/advanced_self_play/checkpoint_qtables_run1.json`, checkpoint 500, normal volatility, 30 bp one-way fee, seed `20261105`. Output, `run_config.json`, and `DEMO_QA.md` are in `outputs/advanced_self_play/demo_frozen/`.

Optional arguments:

```powershell
python .\export_agent_demo.py --checkpoint 300 --scenario high_volatility --seed 20261106 --output .\outputs\advanced_self_play\demo_frozen\demo_high_vol.json
```

If the checkpoint lives elsewhere, pass `--checkpoint-file` (a sibling `run_manifest.json` is required for provenance). The exporter compares its trace-producing frozen replay with the repository's original `run_advanced_self_play.episode()` on the same checkpoint, seed, and configuration before writing output. The checkpoint manifest records the source hashes used when training; the run config separately records the source commit and hashes used for this replay. The existing simulator, learner, reward, state/action definitions, matching assumptions, and cost calculations remain untouched.

## Frozen replay semantics

- Evaluation uses frozen agents, `training=False`, and `epsilon=0`; no Q update is applied.
- The exporter hashes each agent's Q table and action-visit counts before and after replay.
- Every step records both agents' observations, feasible actions, action Q values and visit counts, selected action, feasibility floor, joint order flow, market transition, and per-agent cost decomposition.
- Q values and visit counts are numeric policy diagnostics, not natural-language reasoning and not an LLM chain of thought.
- The included one-episode trace is illustrative, not an aggregate performance estimate or convergence/equilibrium claim.

## JSON fields

Top level: schema/type, source ref and checkpoint identity/hash, replay mode, config, before/after policy-table hashes, parity against the original episode function, cost summary, 60 steps, and interpretation limits.

Each step contains `market_transition` and `agents.A` / `agents.B`. Each agent has `observation`, `decision`, and `execution` objects. `decision.all_actions` maps every action to its name, TWAP multiple, Q value, visit count, and feasibility; `feasible_actions` is the legal subset for the current state. Cost terms are expressed as bp of the parent-order notional. The per-step cost identity is price drift + half spread + temporary impact + fee. Permanent impact changes the next mid and is not added again as a same-step charge. If shares remain unfilled, the total-cost difference is explicitly reported as the opportunity-cost residual.

## Display boundaries

- Both agents decide from the same pre-trade mid and previous-step opponent flow; neither sees the other's current action.
- This is tabular Q-learning, not an LLM-generated trading agent.
- 30 bp is 0.3% one-way fee.
- The simulator assumes batch execution and full fills for submitted child orders; it omits order-book queueing, rejects, and partial fills.
- Feasibility constraints and simulator fill assumptions drive completion; a 100% simulated completion rate is not a real-market guarantee.
- Permanent impact enters later prices; do not count it as an additional current fill charge.
