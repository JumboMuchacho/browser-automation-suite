# Architecture Overview

Popup Detector is a Selenium-based monitoring utility designed to detect
time-sensitive DOM events and alert a human operator.

## Flow

1. License validation
2. Chrome session initialization
3. DOM monitoring loop
4. Deposit address detection
5. Audible alert
6. Manual operator action

## Design Principles

- Human-in-the-loop automation
- Read-only monitoring (no financial actions)
- License-controlled execution
- Production-first packaging
