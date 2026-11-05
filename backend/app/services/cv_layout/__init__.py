"""Shared CV structure and layout rules.

One place for everything that decides how a CV is structured and laid out, so
the in-app preview, PDF, DOCX and Markdown exports can't drift apart:

- credentials.py - Certifications & Training as grouped, structured entries
- normalize.py   - structural clean-up of CV markdown (old and new) and the
                   user's section order / inclusion choices
- blocks.py      - one markdown -> block parser both exporters render from
- options.py     - target length + spacing presets
- fit.py         - real rendered page counts, overflow notice, suggestions
"""
