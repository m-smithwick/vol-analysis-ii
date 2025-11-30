# SYSTEM INSTRUCTION: SPRINT CLOSE ROUTINE

We are wrapping up the current unit of work. Execute the following "Garbage Collection" sequence strictly in this order. Do not skip steps.

## PHASE 1: ARCHIVE & HISTORY
1. **Read** `PROJECT-STATUS.md.md` and `SESSION_IMPROVEMENTS_SUMMARY.md`.
2. **Append** the contents of the `project_state.md` (specifically the "Active Plan" and "Context Dump" sections) to the TOP of `SESSION_IMPROVEMENTS_SUMMARY.md` under a new Header: `## Session [YYYY-MM-DD]: [Goal Name]`.
   - *Constraint:* Summarize any verbose thinking into bullet points. Keep it high-signal.
3. **Clear** `PROJECT-STATUS.md.md` so only the skeleton headers remain (Context, Architectural Impact, Plan, Janitor Queue).

## PHASE 2: ARCHITECTURAL SYNC
4. **Audit** the file changes from this session against `CODE_MAP.txt`.
   - Did we create any NEW files? If yes, add them to the appropriate section in `CODE_MAP.txt` with a one-sentence description of intent.
   - Did we DEPRECATE any files? If yes, move them to the "Archive" section or delete the line.
   - *Constraint:* Maintain the existing formatting of `CODE_MAP.txt` perfectly.

## PHASE 3: TECHNICAL DEBT CARRY-OVER
5. **Review** the "Janitor Queue" from the old `PROJECT-STATUS.md`.
   - If items are critical/blocking: Add them to the NEW (blank) `PROJECT-STATUS.md.md` as the first tasks.
   - If items are minor: Append them to a `backlog.md` file (create if missing).

## PHASE 4: FINAL REPORT
6. **Output** a final summary in the chat:
   - "Sprint Archived."
   - "Map Updated: [Yes/No]"
   - "Debt Carried Over: [Number of items]"
   - "Ready for next objective."