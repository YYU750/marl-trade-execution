# Frozen Agent Replay UI

Run from `multi_agent_execution/` so the page can fetch the verified replay JSON:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/demo_frontend/`. The page reads `outputs/advanced_self_play/demo_frozen/demo_frozen_episode.json` directly and does not make API calls or modify model data.

Use the play button or slider to move through the 60 steps. The chart's solid segment advances to the selected decision step; the faint dashed segment shows the rest of the recorded path. Clicking the price chart selects the nearest step. Left/right arrow keys move one step and Space toggles playback.
