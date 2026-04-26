import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta  # new code
from enum import Enum
from typing import List, Optional

logging.basicConfig(
    filename="pawpal.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# new edit
class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# new code
class TimeSlot(Enum):
    MORNING = 1
    AFTERNOON = 2
    EVENING = 3
    ANY = 4


# Phase 4 Step 1
class Frequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"


@dataclass
class Task:
    name: str
    category: str
    duration_minutes: int
    priority: Priority
    species_filter: Optional[str] = None  # new edit: None means applies to any pet
    is_completed: bool = False
    time_slot: TimeSlot = TimeSlot.ANY          #new code: preferred time of day
    frequency: Frequency = Frequency.AS_NEEDED  # new code: how often this task recurs
    due_date: Optional[date] = None             # new code: when this task is next due

    def mark_complete(self) -> Optional["Task"]:  # new code: returns next occurrence if recurring
        """Mark this task as completed and return a new instance for the next occurrence if recurring."""
        self.is_completed = True

        if self.frequency == Frequency.DAILY:  # new code: reschedule tomorrow
            next_due = date.today() + timedelta(days=1)
        elif self.frequency == Frequency.WEEKLY:  # new code: reschedule next week
            next_due = date.today() + timedelta(weeks=1)
        else:
            return None  # new code: AS_NEEDED tasks don't auto-reschedule

        # new code: return a fresh copy of this task with the new due date
        return Task(
            name=self.name,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            species_filter=self.species_filter,
            is_completed=False,
            time_slot=self.time_slot,
            frequency=self.frequency,
            due_date=next_due
        )

    def edit(self, name: str, duration: int, priority: Priority) -> None:  # newcode 
        """Update the task's name, duration, and priority in place."""
        self.name = name
        self.duration_minutes = duration
        self.priority = priority

    def __repr__(self) -> str:  # newcode 
        """Return a readable string showing priority, name, duration, and status."""
        status = "Done" if self.is_completed else "Pending"
        return f"[{self.priority.name}] {self.name} ({self.duration_minutes} min) — {status}"


@dataclass
class Pet:
    name: str
    species: str  # ex.  "dog", "cat", "rabbit"
    age: int
    special_needs: str = ""
    tasks: List[Task] = field(default_factory=list)  # newcode 

    def get_profile(self) -> str:  # newcode 
        """Return a formatted summary string of the pet's details."""
        needs = f", Special needs: {self.special_needs}" if self.special_needs else ""
        return f"{self.name} ({self.species}, age {self.age}{needs})"

    def add_task(self, task: Task) -> None:  # newcode 
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def get_pending_tasks(self) -> List[Task]:  # newcode 
        """Return all tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.is_completed]


class Owner:
    def __init__(self, name: str, available_minutes: int, preferences: str = ""):
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences
        self.pets: List[Pet] = []  # newcode : supports multiple pets

    def add_pet(self, pet: Pet) -> None:  # new code
        """Add a pet to the owner's list of pets."""
        self.pets.append(pet)  # new code : append instead of overwrite

    def get_available_time(self) -> int:  # new code 
        """Return the owner's total available minutes for the day."""
        return self.available_minutes

    def update_preferences(self, preferences: str) -> None:  # newcode 2
        """Update the owner's scheduling preferences."""
        self.preferences = preferences

    def get_all_tasks(self) -> List[Task]:  # new code 
        """Return a flat list of all tasks across every pet."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner

    def _get_plan_with_pets(self) -> List[tuple]:  # new code : helper that pairs each task with its pet
        """Filter, sort, and return scheduled (pet, task) pairs within the time budget."""
        budget = self.owner.get_available_time()
        candidates = []
        for pet in self.owner.pets:
            for task in pet.get_pending_tasks():
                if task.species_filter is None or task.species_filter == pet.species:
                    candidates.append((pet, task))

        # new code: daily tasks always come first, then by priority, then time slot, then duration
        slot_order = {TimeSlot.MORNING: 1, TimeSlot.AFTERNOON: 2, TimeSlot.EVENING: 3, TimeSlot.ANY: 4}
        candidates.sort(key=lambda pt: (
            0 if pt[1].frequency == Frequency.DAILY else 1,  # new code: daily tasks first
            pt[1].priority.value,
            slot_order[pt[1].time_slot],                     # new code: sort by time slot
            pt[1].duration_minutes
        ))

        plan = []
        time_used = 0
        for pet, task in candidates:
            if time_used + task.duration_minutes <= budget:
                plan.append((pet, task))
                time_used += task.duration_minutes

        return plan

    def generate_plan(self) -> List[Task]:  # newcode 
        """Return the ordered list of tasks scheduled within the owner's time budget."""
        # new edit: Read available_minutes live from owner 
        # new edit: Filter tasks by pet species, then sort by priority then duration as tie-breaker
        return [task for _, task in self._get_plan_with_pets()]

    def sort_by_time(self) -> List[Task]:  # new code
        """Return all tasks across all pets sorted by time_slot (MORNING first, ANY last).

        Does not filter by completion status — returns all tasks regardless.
        Useful for displaying a time-ordered view of the full task list.
        """
        slot_order = {TimeSlot.MORNING: 1, TimeSlot.AFTERNOON: 2, TimeSlot.EVENING: 3, TimeSlot.ANY: 4}
        all_pending = self.owner.get_all_tasks()
        return sorted(all_pending, key=lambda t: slot_order[t.time_slot])

    def get_tasks_by_pet(self, pet_name: str) -> List[Task]:  # new code
        """Return all tasks belonging to the pet with the given name."""
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return pet.tasks
        return []

    def get_tasks_by_status(self, completed: bool) -> List[Task]:  # new code
        """Return all tasks across pets that match the given completion status."""
        return [t for t in self.owner.get_all_tasks() if t.is_completed == completed]

    def complete_and_reschedule(self, pet: Pet, task: Task) -> Optional[Task]:  # new code
        """Mark a task complete and automatically add the next occurrence to the pet if recurring.

        Args:
            pet: The pet that owns the task being completed.
            task: The task to mark as done.
        Returns:
            The newly created next Task if the frequency is DAILY or WEEKLY, otherwise None.
        """
        next_task = task.mark_complete()  # new code: mark done and get next occurrence
        if next_task is not None:
            pet.add_task(next_task)  # new code: add rescheduled task back to the pet
        return next_task

    def filter_tasks(self, pet_name: Optional[str] = None, completed: Optional[bool] = None) -> List[Task]:  # new code
        """Filter tasks by pet name, completion status, or both combined.

        Args:
            pet_name: If provided, only returns tasks belonging to that pet (case-insensitive).
            completed: If True, returns only completed tasks. If False, returns only pending tasks.
                       If None, returns tasks regardless of status.
        Returns:
            A list of Task objects matching the given filters.
        """
        results = self.owner.get_all_tasks()

        if pet_name is not None:  # new code: narrow by pet name if provided
            results = [
                task for pet in self.owner.pets
                if pet.name.lower() == pet_name.lower()
                for task in pet.tasks
            ]

        if completed is not None:  # new code: narrow by completion status if provided
            results = [t for t in results if t.is_completed == completed]

        return results

    def detect_time_conflicts(self) -> List[str]:  # new code
        """Detect overlapping tasks by simulating sequential start times within each slot.

        Assigns each slot a simulated start minute (MORNING=0, AFTERNOON=120, EVENING=240)
        and checks if any two tasks within the same slot have overlapping time windows.
        Returns:
            A list of conflict warning strings, empty if no overlaps are found.
        """
        warnings = []

        # new code: group scheduled (pet, task) pairs by time slot
        slot_buckets: dict = {slot: [] for slot in TimeSlot}
        for pet, task in self._get_plan_with_pets():
            slot_buckets[task.time_slot].append((pet, task))

        for slot, entries in slot_buckets.items():
            if len(entries) < 2:
                continue  # new code: need at least 2 tasks in a slot to have a conflict

            # new code: flag when tasks from different pets share the same slot
            # owner cannot be with two pets simultaneously
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    pet_a, task_a = entries[i]
                    pet_b, task_b = entries[j]
                    if pet_a.name != pet_b.name:  # new code: only flag cross-pet conflicts
                        warnings.append(
                            f"Conflict: '{task_a.name}' ({pet_a.name}) and "
                            f"'{task_b.name}' ({pet_b.name}) overlap in the {slot.name.capitalize()} slot."
                        )

        return warnings

    def safe_detect_conflicts(self) -> List[str]:  #new code
        """Lightweight wrapper that runs all conflict checks and returns warnings without crashing.

        Wraps detect_conflicts() and detect_time_conflicts() each in a try/except so that
        any unexpected error produces a readable warning instead of stopping the program.
        Returns:
            A list of warning strings. If no issues are found, returns a clean confirmation message.
        """
        warnings = []

        try:  # new code: guard slot overload check
            warnings.extend(self.detect_conflicts())
        except Exception as e:
            warnings.append(f"Warning: slot conflict check could not complete — {e}")

        try:  # new code: guard time overlap check
            warnings.extend(self.detect_time_conflicts())
        except Exception as e:
            warnings.append(f"Warning: time conflict check could not complete — {e}")

        if not warnings:  # new code: confirm clean schedule if no issues found
            warnings.append("No conflicts detected — schedule looks good.")

        return warnings

    def detect_conflicts(self) -> List[str]:  # new code
        """Check for time slot overloads and return a list of conflict warning strings."""
        warnings = []
        budget = self.owner.get_available_time()
        slot_budget = budget // 3  # new code: divide day equally across 3 slots

        slot_order = {TimeSlot.MORNING: 1, TimeSlot.AFTERNOON: 2, TimeSlot.EVENING: 3, TimeSlot.ANY: 4}
        slot_totals: dict = {TimeSlot.MORNING: 0, TimeSlot.AFTERNOON: 0, TimeSlot.EVENING: 0}

        for pet in self.owner.pets:
            for task in pet.get_pending_tasks():
                if task.time_slot in slot_totals:
                    slot_totals[task.time_slot] += task.duration_minutes

        for slot, total in slot_totals.items():  # new code: flag overloaded slots
            if total > slot_budget:
                warnings.append(
                    f"Conflict: {slot.name.capitalize()} slot is overloaded "
                    f"({total} min of tasks vs {slot_budget} min available)."
                )

        return warnings

    def explain_reasoning(self) -> str:  # newcode 
        """Return a human-readable summary of scheduled and excluded tasks with pet context."""
        plan_with_pets = self._get_plan_with_pets()  # new code : use helper to get pet context
        budget = self.owner.get_available_time()
        plan_tasks = [task for _, task in plan_with_pets]
        all_pending = [t for t in self.owner.get_all_tasks() if not t.is_completed]
        excluded = [t for t in all_pending if t not in plan_tasks]

        lines = [
            f"Daily plan for {self.owner.name} — {budget} min available",
            f"Scheduled {len(plan_with_pets)} task(s):",
        ]
        for pet, task in plan_with_pets:  # new code : show pet name and species per task
            lines.append(f"  - {task} → {pet.name} ({pet.species})")

        if excluded:
            lines.append(f"Excluded {len(excluded)} task(s) due to time or species mismatch:")
            for task in excluded:
                lines.append(f"  - {task}")

        all_warnings = self.safe_detect_conflicts()  # Phase 4 Step 4: use safe wrapper for all conflict checks
        lines.append("Warnings:")
        for warning in all_warnings:
            lines.append(f"  ! {warning}")

        return "\n".join(lines)


class ScheduleAgent:
    """Agentic workflow: plan → act → check to resolve scheduling conflicts."""

    SLOT_ORDER = [TimeSlot.MORNING, TimeSlot.AFTERNOON, TimeSlot.EVENING, TimeSlot.ANY]

    def __init__(self, owner: "Owner"):
        self.owner = owner
        self.log: List[str] = []  # human-readable step log shown in the UI

    def _log(self, msg: str) -> None:
        self.log.append(msg)
        logging.info(msg)

    # ── Phase 1: Plan ────────────────────────────────────────────────────────
    def plan(self) -> List[str]:
        """Identify current conflicts and return them."""
        self._log("AGENT PLAN: analysing current schedule for conflicts.")
        scheduler = Scheduler(owner=self.owner)
        conflicts = scheduler.safe_detect_conflicts()
        has_conflicts = any("No conflicts" not in c for c in conflicts)
        if not has_conflicts:
            self._log("AGENT PLAN: no conflicts found — nothing to fix.")
        else:
            for c in conflicts:
                if "No conflicts" not in c:
                    self._log(f"AGENT PLAN: detected — {c}")
        return conflicts

    # ── Phase 2: Act ─────────────────────────────────────────────────────────
    def act(self, conflicts: List[str]) -> List[dict]:
        """Try to resolve each conflict by moving a task to a different slot."""
        changes = []
        if all("No conflicts" in c for c in conflicts):
            self._log("AGENT ACT: no action needed.")
            return changes

        # Build a set of (pet_name, task_name) pairs mentioned in conflict warnings
        conflicted_pairs = set()
        _overlap_re = re.compile(
            r"Conflict: '(.+?)' \((.+?)\) and '(.+?)' \((.+?)\) overlap"
        )
        for msg in conflicts:
            m = _overlap_re.search(msg)
            if m:
                task_a, pet_a, task_b, pet_b = m.groups()
                conflicted_pairs.add((pet_a, task_a))
                conflicted_pairs.add((pet_b, task_b))

        # For slot-overload conflicts, collect all tasks in the overloaded slot
        overloaded_slots = set()
        for msg in conflicts:
            if "slot is overloaded" in msg:
                for slot in TimeSlot:
                    if slot.name.capitalize() in msg:
                        overloaded_slots.add(slot)

        for pet in self.owner.pets:
            for task in pet.get_pending_tasks():
                # Stop early if the schedule is already clean
                if self._check():
                    self._log("AGENT ACT: schedule is conflict-free — no further moves needed.")
                    return changes

                in_conflict = (pet.name, task.name) in conflicted_pairs or task.time_slot in overloaded_slots
                if not in_conflict:
                    continue

                original_slot = task.time_slot
                resolved = False
                for candidate in self.SLOT_ORDER:
                    if candidate == original_slot:
                        continue
                    # Tentatively move the task
                    task.time_slot = candidate
                    self._log(
                        f"AGENT ACT: trying '{task.name}' ({pet.name}) "
                        f"{original_slot.name} → {candidate.name}."
                    )
                    # Phase 3: Check
                    if self._check():
                        changes.append({
                            "pet": pet.name,
                            "task": task.name,
                            "from": original_slot.name.capitalize(),
                            "to": candidate.name.capitalize(),
                        })
                        self._log(
                            f"AGENT CHECK: conflict resolved — keeping "
                            f"'{task.name}' in {candidate.name}."
                        )
                        resolved = True
                        break
                    else:
                        self._log(
                            f"AGENT CHECK: still conflicted after move — reverting."
                        )
                        task.time_slot = original_slot  # revert if still broken

                if not resolved:
                    self._log(
                        f"AGENT ACT: could not resolve conflict for '{task.name}' ({pet.name}) — no free slot found."
                    )
        return changes

    # ── Phase 3: Check ───────────────────────────────────────────────────────
    def _check(self) -> bool:
        """Return True if the current schedule has no conflicts."""
        scheduler = Scheduler(owner=self.owner)
        results = scheduler.safe_detect_conflicts()
        return all("No conflicts" in r for r in results)

    # ── Confidence score ─────────────────────────────────────────────────────
    def confidence_score(self, result: dict) -> float:
        """Return a 0.0–1.0 score reflecting how well the agent performed.

        Scoring:
        - Resolved all conflicts → 0.7 base
        - No conflicts found at all → full 1.0 immediately
        - Each change made deducts 0.1 (fewer moves = higher confidence)
        - Floor is 0.1 so there is always a non-zero score
        """
        conflicts = result.get("conflicts_found", [])
        no_conflicts_at_start = all("No conflicts" in c for c in conflicts)
        if no_conflicts_at_start:
            return 1.0

        if not result.get("resolved", False):
            score = 0.1
        else:
            moves = len(result.get("changes", []))
            penalty = max(0, moves - 1) * 0.1  # first move is expected; penalize extras
            score = max(1.0 - penalty, 0.1)

        score = round(min(score, 1.0), 2)
        logging.info(f"AGENT CONFIDENCE: {score}")
        return score

    # ── Full run ─────────────────────────────────────────────────────────────
    def run(self) -> dict:
        """Execute the full plan → act → check loop and return a summary."""
        logging.info("AGENT START: beginning agentic scheduling loop.")
        conflicts = self.plan()
        changes = self.act(conflicts)
        clean = self._check()
        logging.info(
            f"AGENT END: {'schedule is clean' if clean else 'some conflicts remain'}. "
            f"{len(changes)} change(s) made."
        )
        return {
            "conflicts_found": conflicts,
            "changes": changes,
            "resolved": clean,
            "log": list(self.log),
        }
