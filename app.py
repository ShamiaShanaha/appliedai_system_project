import logging

import streamlit as st
from pawpal_system import Owner, Pet, Task, Priority, TimeSlot, Frequency, Scheduler, ScheduleAgent
from tests import run_tests_and_summarize

logging.basicConfig(
    filename="pawpal.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("A smart daily care planner for busy pet owners.")

# ── Session state init ────────────────────────────────────────────────────────
if "owner_name" not in st.session_state:
    st.session_state.owner_name = ""
if "available_minutes" not in st.session_state:
    st.session_state.available_minutes = 60
if "pets" not in st.session_state:
    st.session_state.pets = []  # list of Pet objects, persists across submissions


# ── Section 1: Owner & Pet Setup ─────────────────────────────────────────────
st.header("1. Owner & Pet Setup")
st.caption("Add each pet one at a time. Previously added pets are kept.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    owner_name_input = st.text_input("Owner name", value="Jordan", key="owner_name_input")
with c2:
    pet_name_input = st.text_input("Pet name", key="pet_name_input")
with c3:
    species_input = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"], key="species_input")
with c4:
    available_minutes_input = st.number_input(
        "Available minutes today", min_value=10, max_value=480, value=60, step=10, key="avail_input"
    )

if st.button("Add Pet", type="primary"):
    if not pet_name_input.strip():
        st.warning("Please enter a pet name.")
    else:
        # Check for duplicate pet name
        existing_names = [p.name.lower() for p in st.session_state.pets]
        if pet_name_input.strip().lower() in existing_names:
            st.warning(f"A pet named '{pet_name_input.strip()}' is already added.")
        else:
            new_pet = Pet(name=pet_name_input.strip(), species=species_input, age=0)
            st.session_state.pets.append(new_pet)
            st.session_state.owner_name = owner_name_input.strip()
            st.session_state.available_minutes = int(available_minutes_input)
            st.success(
                f"Owner '{owner_name_input.strip()}' and pet '{new_pet.name}' ({species_input}) set up."
            )

if st.session_state.pets:
    st.write("**Registered pets:**", "  |  ".join(p.name for p in st.session_state.pets))

    if st.button("Clear All Pets"):
        st.session_state.pets = []
        st.rerun()

st.divider()


# ── Section 2: Tasks ──────────────────────────────────────────────────────────
st.header("2. Tasks")
st.caption("Add tasks below. Each task is added directly to your pet using add_task().")

if not st.session_state.pets:
    st.info("Add at least one pet in Section 1 before adding tasks.")
else:
    t1, t2, t3, t4, t5 = st.columns(5)
    with t1:
        task_pet_idx = st.selectbox(
            "Pet",
            range(len(st.session_state.pets)),
            format_func=lambda i: st.session_state.pets[i].name,
            key="task_pet_sel",
        )
    with t2:
        task_name = st.text_input("Task title", key="task_name_input")
    with t3:
        task_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20, key="task_dur")
    with t4:
        task_priority = st.selectbox("Priority", ["high", "medium", "low"], key="task_pri")
    with t5:
        task_slot = st.selectbox(
            "Time of day",
            ["Morning", "Afternoon", "Evening", "Any"],
            key="task_slot",
        )

    slot_map = {
        "Morning": TimeSlot.MORNING,
        "Afternoon": TimeSlot.AFTERNOON,
        "Evening": TimeSlot.EVENING,
        "Any": TimeSlot.ANY,
    }

    if st.button("Add Task", type="primary"):
        if not task_name.strip():
            st.warning("Please enter a task title.")
        else:
            new_task = Task(
                name=task_name.strip(),
                category="general",
                duration_minutes=int(task_duration),
                priority=Priority[task_priority.upper()],
                time_slot=slot_map[task_slot],
                frequency=Frequency.DAILY,
            )
            st.session_state.pets[task_pet_idx].add_task(new_task)
            st.success(
                f"Task '{new_task.name}' added to {st.session_state.pets[task_pet_idx].name}."
            )

    # Display all tasks grouped by pet
    st.markdown("**Current tasks:**")
    any_tasks = False
    for pet in st.session_state.pets:
        if pet.tasks:
            any_tasks = True
            st.markdown(f"*{pet.name} ({pet.species})*")
            rows = [
                {
                    "title": t.name,
                    "duration_minutes": t.duration_minutes,
                    "priority": t.priority.name.lower(),
                    "time_of_day": t.time_slot.name.capitalize(),
                }
                for t in pet.tasks
            ]
            st.table(rows)
    if not any_tasks:
        st.info("No tasks added yet.")

st.divider()


# ── Section 3: Build Schedule ─────────────────────────────────────────────────
if "schedule_generated" not in st.session_state:
    st.session_state.schedule_generated = False
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None

st.header("3. Build Schedule")
st.caption("Generates a prioritized daily plan from your pet's tasks within your available time.")

if st.button("Generate Schedule", type="primary"):
    if not st.session_state.pets:
        st.error("Add at least one pet in Section 1 first.")
    elif not any(pet.tasks for pet in st.session_state.pets):
        st.error("Add at least one task in Section 2 first.")
    else:
        st.session_state.schedule_generated = True
        st.session_state.agent_result = None  # reset agent result on new schedule

if st.session_state.schedule_generated and st.session_state.pets:
    owner = Owner(
        name=st.session_state.owner_name or "Owner",
        available_minutes=st.session_state.available_minutes,
    )
    for pet in st.session_state.pets:
        owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    plan_with_pets = scheduler._get_plan_with_pets()
    budget = owner.get_available_time()
    plan_tasks = [task for _, task in plan_with_pets]
    total_time = sum(t.duration_minutes for t in plan_tasks)

    st.markdown(f"**{owner.name}** — {budget} min available")
    st.progress(min(total_time / budget, 1.0), text=f"{total_time} / {budget} min used")

    st.markdown("#### Conflict Warnings")
    conflicts = scheduler.safe_detect_conflicts()
    for msg in conflicts:
        if "No conflicts" in msg:
            st.success(msg)
        else:
            st.warning(msg)

    st.markdown("#### Today's Scheduled Tasks")
    if plan_with_pets:
        st.table([
            {
                "Pet": pet.name,
                "Task": task.name,
                "Time of Day": task.time_slot.name.capitalize(),
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority.name.upper(),
            }
            for pet, task in plan_with_pets
        ])
    else:
        st.warning("No tasks fit within the available time.")

    st.markdown("#### All Tasks by Time of Day")
    sorted_tasks = scheduler.sort_by_time()
    if sorted_tasks:
        st.table([
            {
                "Pet": next((p.name for p in st.session_state.pets if task in p.tasks), "—"),
                "Task": task.name,
                "Time Slot": task.time_slot.name.capitalize(),
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority.name.upper(),
                "Frequency": task.frequency.value,
            }
            for task in sorted_tasks
        ])

    st.divider()
    st.markdown("#### 🤖 AI Agent: Auto-Fix Conflicts")
    st.caption("The agent will plan, act, and check its own work to resolve any conflicts.")

    if st.button("Get AI Recommendation", type="primary"):
        logging.info("User triggered ScheduleAgent.")
        agent_owner = Owner(
            name=st.session_state.owner_name or "Owner",
            available_minutes=st.session_state.available_minutes,
        )
        for pet in st.session_state.pets:
            agent_owner.add_pet(pet)
        try:
            agent = ScheduleAgent(owner=agent_owner)
            result = agent.run()
            result["confidence"] = agent.confidence_score(result)
            result["agent"] = agent
            st.session_state.agent_result = result
        except Exception as e:
            logging.error(f"ScheduleAgent error: {e}")
            st.session_state.agent_result = {"error": str(e)}

    # Display agent result if available
    if st.session_state.agent_result:
        result = st.session_state.agent_result
        if "error" in result:
            st.error(f"Agent encountered an error: {result['error']}")
        else:
            with st.expander("Agent reasoning log", expanded=True):
                for step in result["log"]:
                    st.markdown(f"- {step}")

            if result["changes"]:
                st.markdown("**Changes made:**")
                for change in result["changes"]:
                    st.info(
                        f"Moved **{change['task']}** ({change['pet']}) "
                        f"from {change['from']} → {change['to']}"
                    )
            else:
                st.info("No task moves were needed or possible.")

            if result["resolved"]:
                st.success("Agent check passed — schedule is now conflict-free.")
            else:
                st.warning(
                    "Agent could not fully resolve all conflicts. "
                    "Try adjusting task durations or available minutes."
                )

            # Confidence score
            score = result.get("confidence", 0.0)
            st.markdown(f"**Agent confidence score: {score}**")
            st.progress(score, text=f"{int(score * 100)}% confidence")

            # Test summary
            st.divider()
            st.markdown("#### Reliability Report")
            try:
                summary, passed, total = run_tests_and_summarize()
                if passed == total:
                    st.success(summary)
                else:
                    st.warning(summary)
                logging.info(f"Reliability report shown: {summary}")
            except Exception as e:
                logging.error(f"Test runner error: {e}")
                st.error(f"Could not run reliability tests: {e}")
