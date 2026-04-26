"""Tests for PawPal+ scheduling logic."""
import unittest
from pawpal_system import Owner, Pet, Task, Priority, TimeSlot, Frequency, Scheduler, ScheduleAgent


def make_owner(minutes=120):
    return Owner(name="TestOwner", available_minutes=minutes)


def make_pet(name="Rex", species="dog"):
    return Pet(name=name, species=species, age=2)


def make_task(name="Walk", duration=20, priority=Priority.HIGH,
              slot=TimeSlot.MORNING, freq=Frequency.DAILY, species_filter=None):
    return Task(name=name, category="general", duration_minutes=duration,
                priority=priority, time_slot=slot, frequency=freq,
                species_filter=species_filter)


class TestSchedulerFitsWithinBudget(unittest.TestCase):
    """Scheduled tasks must never exceed the owner's available minutes."""

    def test_total_time_within_budget(self):
        owner = make_owner(minutes=60)
        pet = make_pet()
        owner.add_pet(pet)
        pet.add_task(make_task("Walk", 30))
        pet.add_task(make_task("Play", 25))
        pet.add_task(make_task("Groom", 20))  # would push over 60

        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()
        total = sum(t.duration_minutes for t in plan)
        self.assertLessEqual(total, 60)

    def test_empty_plan_when_all_tasks_too_long(self):
        owner = make_owner(minutes=10)
        pet = make_pet()
        owner.add_pet(pet)
        pet.add_task(make_task("Walk", 30))

        plan = Scheduler(owner).generate_plan()
        self.assertEqual(plan, [])


class TestPriorityOrdering(unittest.TestCase):
    """Higher-priority tasks must be scheduled before lower-priority ones."""

    def test_high_before_low(self):
        owner = make_owner(minutes=60)
        pet = make_pet()
        owner.add_pet(pet)
        pet.add_task(make_task("LowTask", 15, Priority.LOW, freq=Frequency.AS_NEEDED))
        pet.add_task(make_task("HighTask", 15, Priority.HIGH))

        plan = Scheduler(owner).generate_plan()
        names = [t.name for t in plan]
        self.assertIn("HighTask", names)
        self.assertIn("LowTask", names)
        self.assertLess(names.index("HighTask"), names.index("LowTask"))

    def test_daily_before_as_needed_regardless_of_priority(self):
        owner = make_owner(minutes=60)
        pet = make_pet()
        owner.add_pet(pet)
        pet.add_task(make_task("LowDaily", 15, Priority.LOW, freq=Frequency.DAILY))
        pet.add_task(make_task("HighAsNeeded", 15, Priority.HIGH, freq=Frequency.AS_NEEDED))

        plan = Scheduler(owner).generate_plan()
        names = [t.name for t in plan]
        self.assertLess(names.index("LowDaily"), names.index("HighAsNeeded"))


class TestSpeciesFilter(unittest.TestCase):
    """Tasks with a species_filter must only apply to matching pets."""

    def test_dog_task_excluded_for_cat(self):
        owner = make_owner(minutes=120)
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(cat)
        cat.add_task(make_task("DogWalk", 30, species_filter="dog"))

        plan = Scheduler(owner).generate_plan()
        self.assertEqual(plan, [])

    def test_task_without_filter_applies_to_any_species(self):
        owner = make_owner(minutes=120)
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(cat)
        cat.add_task(make_task("Feed", 10, species_filter=None))

        plan = Scheduler(owner).generate_plan()
        self.assertEqual(len(plan), 1)


class TestTimeSlotSorting(unittest.TestCase):
    """sort_by_time() must return tasks in MORNING → AFTERNOON → EVENING → ANY order."""

    def test_sort_order(self):
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)
        pet.add_task(make_task("Evening", 10, slot=TimeSlot.EVENING))
        pet.add_task(make_task("Morning", 10, slot=TimeSlot.MORNING))
        pet.add_task(make_task("Afternoon", 10, slot=TimeSlot.AFTERNOON))

        sorted_tasks = Scheduler(owner).sort_by_time()
        slots = [t.time_slot for t in sorted_tasks]
        self.assertEqual(slots, [TimeSlot.MORNING, TimeSlot.AFTERNOON, TimeSlot.EVENING])


class TestConflictDetection(unittest.TestCase):
    """detect_time_conflicts() must flag tasks from different pets in the same slot."""

    def test_cross_pet_conflict_flagged(self):
        owner = make_owner(minutes=300)
        dog = make_pet("Buddy", "dog")
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(dog)
        owner.add_pet(cat)
        dog.add_task(make_task("DogMorning", 20, slot=TimeSlot.MORNING))
        cat.add_task(make_task("CatMorning", 20, slot=TimeSlot.MORNING))

        warnings = Scheduler(owner).detect_time_conflicts()
        self.assertTrue(any("Morning" in w for w in warnings))

    def test_no_conflict_different_slots(self):
        owner = make_owner(minutes=300)
        dog = make_pet("Buddy", "dog")
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(dog)
        owner.add_pet(cat)
        dog.add_task(make_task("DogMorning", 20, slot=TimeSlot.MORNING))
        cat.add_task(make_task("CatEvening", 20, slot=TimeSlot.EVENING))

        warnings = Scheduler(owner).detect_time_conflicts()
        self.assertEqual(warnings, [])


class TestMarkCompleteAndReschedule(unittest.TestCase):
    """Completing a DAILY task should create a new task; AS_NEEDED should not."""

    def test_daily_creates_next_occurrence(self):
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)
        task = make_task("Feed", freq=Frequency.DAILY)
        pet.add_task(task)

        next_task = Scheduler(owner).complete_and_reschedule(pet, task)
        self.assertIsNotNone(next_task)
        self.assertFalse(next_task.is_completed)
        self.assertEqual(next_task.name, "Feed")

    def test_as_needed_no_reschedule(self):
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)
        task = make_task("Groom", freq=Frequency.AS_NEEDED)
        pet.add_task(task)

        next_task = Scheduler(owner).complete_and_reschedule(pet, task)
        self.assertIsNone(next_task)


class TestFilterTasks(unittest.TestCase):
    """filter_tasks() must correctly filter by pet name and/or completion status."""

    def test_filter_by_pet_name(self):
        owner = make_owner()
        dog = make_pet("Buddy")
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(dog)
        owner.add_pet(cat)
        dog.add_task(make_task("DogTask"))
        cat.add_task(make_task("CatTask"))

        results = Scheduler(owner).filter_tasks(pet_name="Buddy")
        self.assertTrue(all(t.name == "DogTask" for t in results))

    def test_filter_by_completed_status(self):
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)
        t1 = make_task("Done")
        t1.is_completed = True
        t2 = make_task("Pending")
        pet.add_task(t1)
        pet.add_task(t2)

        pending = Scheduler(owner).filter_tasks(completed=False)
        self.assertEqual([t.name for t in pending], ["Pending"])


class TestScheduleAgent(unittest.TestCase):
    """Tests for the agentic workflow: plan → act → check."""

    def _make_conflicting_owner(self):
        """Two pets with Morning tasks — guaranteed conflict."""
        owner = make_owner(minutes=120)
        dog = make_pet("Buddy", "dog")
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(dog)
        owner.add_pet(cat)
        dog.add_task(make_task("DogMorning", 20, slot=TimeSlot.MORNING))
        cat.add_task(make_task("CatMorning", 20, slot=TimeSlot.MORNING))
        return owner

    def test_agent_detects_conflict(self):
        """Agent plan() must identify a conflict when two pets share a slot."""
        owner = self._make_conflicting_owner()
        agent = ScheduleAgent(owner)
        conflicts = agent.plan()
        has_conflict = any("No conflicts" not in c for c in conflicts)
        self.assertTrue(has_conflict)

    def test_agent_resolves_conflict(self):
        """Agent run() must produce a clean schedule after acting."""
        owner = self._make_conflicting_owner()
        agent = ScheduleAgent(owner)
        result = agent.run()
        self.assertTrue(result["resolved"])

    def test_agent_makes_exactly_one_move(self):
        """Agent must stop after the minimum number of moves needed."""
        owner = self._make_conflicting_owner()
        agent = ScheduleAgent(owner)
        result = agent.run()
        self.assertEqual(len(result["changes"]), 1)

    def test_agent_no_action_when_clean(self):
        """Agent must make zero changes when there are no conflicts."""
        owner = make_owner(minutes=120)
        dog = make_pet("Buddy", "dog")
        cat = make_pet("Whiskers", "cat")
        owner.add_pet(dog)
        owner.add_pet(cat)
        dog.add_task(make_task("DogMorning", 20, slot=TimeSlot.MORNING))
        cat.add_task(make_task("CatEvening", 20, slot=TimeSlot.EVENING))
        agent = ScheduleAgent(owner)
        result = agent.run()
        self.assertEqual(result["changes"], [])
        self.assertTrue(result["resolved"])

    def test_agent_confidence_perfect(self):
        """Confidence score must be 1.0 when conflict is resolved in one move."""
        owner = self._make_conflicting_owner()
        agent = ScheduleAgent(owner)
        result = agent.run()
        score = agent.confidence_score(result)
        self.assertEqual(score, 1.0)

    def test_agent_confidence_no_conflicts(self):
        """Confidence score must be 1.0 when there were no conflicts to begin with."""
        owner = make_owner(minutes=120)
        dog = make_pet("Buddy", "dog")
        owner.add_pet(dog)
        dog.add_task(make_task("Walk", 20, slot=TimeSlot.MORNING))
        agent = ScheduleAgent(owner)
        result = agent.run()
        score = agent.confidence_score(result)
        self.assertEqual(score, 1.0)


def run_tests_and_summarize():
    """Run all tests and return a (summary_string, passed, total) tuple."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result = runner.run(suite)
    total = result.testsRun
    failed_cases = result.failures + result.errors
    failed = len(failed_cases)
    passed = total - failed
    if failed == 0:
        summary = f"{passed} out of {total} tests passed. All checks green."
    else:
        failed_names = [tc.id().split(".")[-1] for tc, _ in failed_cases]
        summary = f"{passed} out of {total} tests passed. Failed: {', '.join(failed_names)}."
    import logging
    logging.info(f"TEST SUMMARY: {summary}")
    return summary, passed, total


import os

if __name__ == "__main__":
    unittest.main(verbosity=2)
