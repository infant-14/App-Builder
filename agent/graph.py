import time
from dotenv import load_dotenv
#from langchain.globals import set_verbose, set_debug
from langchain.chat_models import init_chat_model
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from agent.prompts import *
from agent.states import *
from agent.tools import write_file, read_file, get_current_directory, list_files

_ = load_dotenv()

#set_debug(True)
#set_verbose(True)

llm = init_chat_model("gpt-4o-mini")


def invoke_with_retry(runnable, input_data, config=None, max_attempts=5, initial_delay=2):
    """Invokes a runnable (LLM or Agent) with exponential backoff on exceptions."""
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            if config:
                return runnable.invoke(input_data, config)
            else:
                return runnable.invoke(input_data)
        except Exception as e:
            if attempt == max_attempts:
                print(f"Failed after {max_attempts} attempts: {e}")
                raise e
            print(f"API connection error (Attempt {attempt}/{max_attempts}): {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2


def planner_agent(state: dict) -> dict:
    """Converts user prompt into a structured Plan."""
    user_prompt = state["user_prompt"]
    resp = invoke_with_retry(
        llm.with_structured_output(Plan),
        planner_prompt(user_prompt)
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")
    return {"plan": resp}


def architect_agent(state: dict) -> dict:
    """Creates TaskPlan from Plan."""
    plan: Plan = state["plan"]
    resp = invoke_with_retry(
        llm.with_structured_output(TaskPlan),
        architect_prompt(plan=plan.model_dump_json())
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")

    resp.plan = plan
    print(resp.model_dump_json())
    return {"task_plan": resp}


def coder_agent(state: dict) -> dict:
    """LangGraph tool-using coder agent."""
    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    existing_content = read_file.run(current_task.filepath)

    task_plan = coder_state.task_plan
    plan_data = ""
    if task_plan.plan:
        plan_data = (
            f"App Name: {task_plan.plan.name}\n"
            f"Description: {task_plan.plan.description}\n"
            f"Tech Stack: {task_plan.plan.techstack}\n"
            f"Features requested:\n" + "\n".join([f"- {f}" for f in task_plan.plan.features]) + "\n"
        )
    
    # Compile the list of steps and mark their statuses
    steps_progress = ""
    for idx, step in enumerate(steps):
        status = "COMPLETED" if idx < coder_state.current_step_idx else ("IN_PROGRESS" if idx == coder_state.current_step_idx else "PENDING")
        steps_progress += f"- Step {idx + 1}: {step.filepath} -> {step.task_description} ({status})\n"

    user_prompt = (
        f"We are building the application according to this overall plan:\n"
        f"{plan_data}\n"
        f"Implementation Steps and Progress:\n"
        f"{steps_progress}\n"
        f"Your current task:\n"
        f"- Target File: {current_task.filepath}\n"
        f"- Task Description: {current_task.task_description}\n\n"
        f"Existing content of {current_task.filepath}:\n"
        f"```\n{existing_content}\n```\n\n"
        f"Instructions:\n"
        f"1. You MUST write the complete and updated contents to the exact Target File path: '{current_task.filepath}' using the `write_file` tool. Do not call `write_file` with any other path, name variation, or extension (e.g. if the Target File is '{current_task.filepath}', you must write it to exactly '{current_task.filepath}').\n"
        f"2. BEFORE modifying/writing to {current_task.filepath}, you must check if other files in the project (like HTML, CSS, or JS files) already exist. Use list_files and read_file to view their contents. For example, if you are writing JS, read the generated HTML first to make sure your selectors and IDs match exactly.\n"
        f"3. Ensure the code you write is FULLY interactive, feature-complete, loads initial data/state on page load, and has working functionality for all actions. DO NOT use placeholder comments, mock handlers, or half-implemented stubs.\n"
    )

    system_prompt = coder_system_prompt()
    coder_tools = [read_file, write_file, list_files, get_current_directory]
    react_agent = create_react_agent(llm, coder_tools)

    invoke_with_retry(
        react_agent,
        {"messages": [{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}]}
    )

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}


graph = StateGraph(dict)

graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get("status") == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)

graph.set_entry_point("planner")
agent = graph.compile()
if __name__ == "__main__":
    result = agent.invoke({"user_prompt": "Build a colourful modern todo app in html css and js"},
                          {"recursion_limit": 100})
    print("Final State:", result)