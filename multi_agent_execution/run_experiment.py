#!/usr/bin/env python3
"""Primary project entry point: simultaneous A/B Q-learning self-play.

The historical single-learner/fixed-opponent benchmark is kept separately in
run_standard_benchmark.py. This entry point always runs the advanced model.
"""
from run_advanced_self_play import main


if __name__ == "__main__":
    main()
