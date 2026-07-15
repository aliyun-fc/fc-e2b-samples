# BrowserUse examples

`01_browseruse_basic.py` creates an E2B browser sandbox, connects BrowserUse to
browsertool over authenticated CDP, then runs one task.

`02_browseruse_advanced.py` runs three sequential tasks with one BrowserUse
browser object and one E2B sandbox. This demonstrates session and browser reuse.

Both examples always stop the BrowserUse connection and destroy their sandbox.
