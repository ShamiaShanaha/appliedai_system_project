# PawPal+

**A smart daily care planner for busy pet owners including  an AI agent that detects and resolves scheduling conflicts automatically.**

---

## Original Project (Modules 1–3)

This project started as **PawPal+**, a Streamlit app designed to help a busy pet owner stay consistent with daily pet care. The original goals were to track care tasks (walks, feeding, medication, grooming, enrichment), apply scheduling constraints like time budget and priority, and produce a daily plan and explain why it chose that plan. The core system included four classes `Owner`, `Pet`, `Task`, and `Scheduler` and covered sorting by time slot, species-specific filtering, conflict detection, and recurring task rescheduling.

---

## Title and Summary

**PawPal+** is a multi-pet daily care scheduler that turns a list of tasks into a smart, conflict-free daily plan. It matters because real households often have more than one pet with overlapping care needs, and manually juggling those schedules across time slots is error-prone. PawPal+ automates that work: it detects when two pets are scheduled at the same time, resolves the conflict by moving one task to an open slot, scores its own confidence in the result, and runs 19 automated reliability tests without any external API or internet connection.

---

## Architecture Overview

The system has four main components that data flows through in order:

1. **Human input** — the owner enters pet profiles and care tasks via the Streamlit UI
2. **Scheduler** — generates a prioritized plan (HIGH before LOW, DAILY before AS_NEEDED) and runs conflict detection to flag when two pets share the same time slot
3. **ScheduleAgent** — an agentic plan → act → check loop that reads the conflicts, moves one task to an open slot, and re-checks until the schedule is clean; it stops as soon as it resolves the problem
4. **Human review** — the owner sees the resolved schedule, a confidence score (0.0–1.0), and a reliability report from 19 automated unit tests

The Unit Test Suite sits alongside the agent and runs automatically whenever the AI recommendation is triggered, giving the human a pass/fail signal they can use to trust the output.

**Interactive diagram:** [View on mermaid.live](https://mermaid.live/edit#pako:eNptkk9PGzEQxb_KyAdODQpqVbU5IIUsEP4GAT11e3DtWWLhtSN7nCgQvjuzXnBS6B5W8s5vnvc9vWehvEYxAtFYv1JzGQjuq9oBP-PftaiT_vFV81t9_wbT1Eo3gtnKYYA9uEGCO6S0qMUfGAwO4YgXuo97cC_jI1SSJI96saNMTJi4U3PUyWIos0meVd12MD4YMk-o4cZK9wE5ZmTiXWONIqiQUJHxW-i4gzY1W-qRCI1PTtdiAyc7F48f0FFZOsnKpzxf2M6d0Tw1zRqKSkFPMzplVCoaQeuXCMROI5AHhyuI1u_g04yfMc4Xq8cRBByE5Iow6E8Ozt4cRDLWFtC4h87D9F9GWewC2sA533CL0dslp_ZuskhW-S8udvxDZSJ7XRfkvEd287h8S7pLQyGr-oAw3B8ODvaHZe8io1f_rQnc4tLgKsIs0SJt477sd_rDNa_-coYrh5G7lAwhHPwE4lN8L9Usu7NG_jXW0Jp1Fz5s9Wa9nvgCosXQSqO5zM-C5tjmWmtsZLIkXl5eATf-5Ks)

---

## Setup Instructions

**1. Clone or download the project**

```bash
cd ai110-module2show-pawpal-starter
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv

# Mac / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the Streamlit app**

```bash
streamlit run app.py or 
python -m streamlit run app.py
```

**5. (Optional) Run tests directly from the terminal**

```bash
python -m pytest tests.py -v
```

---

## Sample Interactions

### Example 1 — Cross-pet conflict detected and resolved

**Input:**
- Owner: Jordan, 120 minutes available
- Pet 1: Buddy (dog) — Morning Walk, 30 min, HIGH priority, Morning slot
- Pet 2: Whiskers (cat) — Feeding, 10 min, HIGH priority, Morning slot
- Click **Generate Schedule**, then **Get AI Recommendation**

**AI Output (agent reasoning log):**
```
AGENT PLAN: analysing current schedule for conflicts.
AGENT PLAN: detected — Conflict: 'Feeding' (Whiskers) and 'Morning Walk' (Buddy) overlap in the Morning slot.
AGENT ACT: trying 'Morning Walk' (Buddy) MORNING → AFTERNOON.
AGENT CHECK: conflict resolved — keeping 'Morning Walk' in AFTERNOON.
AGENT ACT: schedule is conflict-free — no further moves needed.
```
- Changes made:
Moved **Morning Walk** (Buddy) from Morning → Afternoon
- Verdict: Agent check passed — schedule is now conflict-free.
- Confidence score: **1.0** (resolved in one move)

---

### Example 2 — No conflicts, agent takes no action

**Input:**
- Owner: Jordan, 120 minutes available
- Pet 1: Buddy (dog) — Morning Walk, 30 min, Morning slot
- Pet 2: Whiskers (cat) — Medication, 15 min, Evening slot
- Click **Generate Schedule**, then **Get AI Recommendation**

**AI Output:**
```
AGENT PLAN: analysing current schedule for conflicts.
AGENT PLAN: no conflicts found — nothing to fix.
AGENT ACT: no action needed.
```
- Changes made: None
- Verdict: Agent check passed — schedule is now conflict-free.
- Confidence score: **1.0**

---

### Example 3 — Budget constraint filters out low-priority tasks

**Input:**
- Owner: Jordan, 40 minutes available
- Pet: Buddy (dog) — Morning Walk (30 min, Morning, HIGH), Enrichment Play (20 min,Afternoon, LOW), Grooming (10 min,Evening, MEDIUM)

**Scheduled output:**
| Pet | Task | Time of Day | Duration (min) | Priority |
|-----|------|-------------|----------------|----------|
| Buddy | Morning Walk | Morning | 30 | HIGH |
| Buddy | Grooming | Evening | 10 | MEDIUM |

Enrichment Play is excluded — it would push the total to 60 min, exceeding the 40-minute budget.

---

## Design Decisions

**Pure Python agentic loop (no API key required)**
The `ScheduleAgent` implements a plan → act → check loop entirely in Python. This means the app works offline and does not require any external service, API key, or paid subscription a deliberate tradeoff that sacrifices natural language reasoning for full reliability and zero cost.

**Session state persistence in Streamlit**
Streamlit reruns the entire script on every interaction. Storing `pets`, `schedule_generated`, and `agent_result` in `st.session_state` prevents data from disappearing when buttons are clicked. Without this, clicking "Get AI Recommendation" would erase the schedule it was supposed to analyze.

**Reading conflict messages correctly**
When the agent finds a conflict, it needs to know which pet and which task to move. The first version couldn't read that information correctly, so it did nothing there was no error, no fix, just silence. The fix was teaching it to read the conflict message in a smarter way so it could actually find and move the right task.

**Early-exit after first resolution**
The agent stops after the first move that makes the schedule conflict-free. It does not continue reassigning tasks just because more conflicting pairs were in the original list. This keeps the schedule as close to the owner's original intent as possible.

**Confidence scoring**
The confidence score rewards resolving a conflict in one move (1.0), penalizes each extra move beyond the first (−0.1 per move), and assigns 0.1 if the agent could not resolve the conflict at all. This gives the human an at-a-glance signal of how cleanly the agent performed.

---

## Testing Summary

19 automated unit tests are organized across 7 test classes and run every time the AI agent is used in the app.

| Test Class | What it checks |
|---|---|
| `TestSchedulerFitsWithinBudget` | The schedule never goes over the owner's available minutes |
| `TestPriorityOrdering` | High priority tasks are always scheduled before lower ones |
| `TestSpeciesFilter` | A task meant for a dog does not get assigned to a cat |
| `TestTimeSlotSorting` | Tasks are shown in order: Morning, then Afternoon, then Evening |
| `TestConflictDetection` | Two pets in the same time slot gets flagged as a conflict |
| `TestMarkCompleteAndReschedule` | Daily tasks get rescheduled after completion and one-time tasks do not |
| `TestFilterTasks` | You can filter tasks by pet name or by whether they are done or not |
| `TestScheduleAgent` | The agent finds conflicts, fixes them in one move, and scores itself correctly |

**What worked:** All 19 tests pass. The agent reliably detects and resolves single conflicts in one move and correctly takes no action when the schedule is already clean.

**What didn't at first:** Three tests failed because the agent couldn't read the conflict messages correctly. It looked like everything was working, but the agent was quietly doing nothing it had no error, no fix. Once the way it read those messages was corrected, all three tests passed.

**What I learned:** Silent exception handling is one of the hardest bugs to catch. The agentig bappeared to run without errors, but it was doing nothing. Writing tests that assert on specific outputs like the number of changes made forced the issue to surface rather than hiding behind a clean-looking UI.

---

## Reflection

Building the agent taught me that you do not need a fancy AI model to make something feel intelligent. A simple plan, act, check loop was enough to detect and fix scheduling conflicts on its own. The trickiest part was getting it to stop at the right time.The first version kept moving tasks even after the problem was already fixed, so I had to make it re-check the schedule after every move instead of just working through the original list.

Testing also taught me that something can look fine on the screen and still be broken underneath. The only way to really know if the code works is to write tests that check the actual results. Watching the test count go from 16/19 to 19/19 after finding and fixing the bug made that very clear.

This project also showed me that good AI design is not just about what the machine does but it is about knowing what the human should still be in charge of. The agent does the repetitive work, but the owner still looks over the results before trusting them. That balance is something I would keep in mind for any future project.
