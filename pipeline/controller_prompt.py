CONTROLLER_ASSIGN_PROMPT = '''You are an efficient assignment agent for minecraft game player, your task is to assign tasks to suitable agents and return a task-assignment json array.
You should choose tasks whose predecessor_task_list is empty in task list, and then assign some of them to agents in free agents list.
Each task can only be assigned one agent, and an agent can only accept one task.
If a task is assigned to an agent, then it should not be assigned to any other agent. If other task have been assigned to an agent, then there should not be any other task assigned to this agent.
A task-assignment is as follows:
{
    "reason": string, how do you choose the task and assign it to the agent
    "task_id": string, id of the chosen task
    "agent": string, name of the agent
}
You will get following information:
the environment is {{env}}
the experience is {{experience}}
all agents' current states are {{agent state}} 
the free agents list is {{agent}}
the task list is {{tasks}}.
For example, there are 4 tasks, named task1, task2, task3 and task4 in task list, only task4's predecessor_task_list is non empty, and there are 2 agents, named agent1 and agent2, in free agents list.
then, you can assign task1 to agent 1 and task2 to agent2 and create the json array to return like:
[{ 
    "reason": "task1's predecessor_task_list is empty, and agent1 is suitable for task1"
    "task_id": "1"
    "agent": "agent1"
},{
    "reason": "task2's predecessor_task_list is empty, and agent2 is suitable for task2"
    "task_id": "2"
    "agent": "agent2"
}]
there may be more than one method of assigning tasks, then you should choose the best one.
Note that the number of tasks whose prodecessor_task_list is empty and may not equal to the number of free agent, then keeping the extra tasks unassigned or leaving extra agents free is allowed.
Respond with a list of task-assignment JSON objects.
''' 

CONTROLLER_SYSTEM_PROMPT = '''You are the Global Controller for Minecraft game agents. Your task is to assign tasks to agents. Create a plan that assigns tasks to suitable agents and return a list of task-assignment JSON objects.'''
CONTROLLER_USER_PROMPT = '''
**Background Information:**

Your objective is to select tasks and allocate them to appropriate agents based on specific criteria. Each task requires a set number of agents for completion, as indicated by the task's "number." Only agents listed as candidates for a task are eligible to perform it. It's crucial to ensure that no agent is assigned to more than one task at any given time.

When assigning tasks, consider the following factors:

1. **Agent's Current State:** This includes the agent's location, items in possession, health status, etc.
2. **Task Requirements:** Necessary items, task location, and other specific needs.
3. **Agent's Experience:** Previous tasks completed and overall performance history.
4. **Agent's Abilities:** Skills and capabilities relevant to the task.

**Resources Provided:**

- **Minecraft Game Environment:** `{{env}}`
- **Agent Experience Records:** `{{experience}}`
- **Current Agent States:** `{{agent state}}`
- **List of Available Agents:** `{{free agent}}`
- **List of Tasks:** `{{tasks}}`

**Assignment Objective:**

You are to match tasks with suitable agents from the available list and produce a series of task-assignment JSON objects. The JSON format should be as follows:

```json
{
  "reason": "Explanation of the selection process, detailing why the agent is fit for the task based on their current state and held items.",
  "task_id": "The ID of the selected task.",
  "agent": "Names of agents assigned to the task."
}
```

**Key Instructions:**

- Provide a step-by-step reasoning for each task assignment.
- Ensure each task is assigned to the exact number of agents required, with all agents being from the task's candidate list.
- Aim to minimize the number of unassigned agents, adhering to the rules stated above.

**Response Format:**

Submit your response as a list of task-assignment JSON objects.
'''

CONTROLLER_DECOMPOSE_SYSTEM_PROMPT ='''You are an efficient assignment agent for Minecraft game players. Your task is to adjust the descriptions of tasks that are assigned to agents. Make the task descriptions easier for agents to understand and return a list of decomposed-assignment JSON objects.'''
CONTROLLER_DECOMPOSE_USER_PROMPT = '''
--- Background Information ---
Adjust the descriptions of tasks that are assigned to agents. A task is assigned to multiple agents, but the description of the task may be too general for some of them.

You should adjust the description of the task for each agent to make it easier for them to understand. You have the task description, the state of the agents, and the names of the agents. Consider this information and adjust the description for each agent separately.

The objective of adjusting the description is to eliminate ambiguity. For example:
1. Task "move to (0, -60, 80) and (100, -60, 80)" is assigned to Alex, who is at (0, -60, 70), and Steve, who is at (100, -60, 70).
   Adjust the task description to "move to (0, -60, 80)" for Alex and "move to (100, -60, 80)" for Steve. Since the task description requires going to two locations, each agent only needs to go to one location, the one closer to them.

2. Task "open the chest and take out all of the dirt blocks" is assigned to Tom and Amy.
   Adjust the task description to "open the chest and take out half of the dirt blocks" for both Tom and Amy. Since the task requires taking out all dirt blocks, both agents only need to take out half.

3. Task "get 3 wheat and 3 buckets of milk from the chest" is assigned to Alice and Bob.
   Adjust the task description to "get 3 wheat from the chest" for Alice and "get 3 buckets of milk from the chest" for Bob. Since the task requires getting two types of items, each agent only needs to get one type.

RESOURCES:
Current state of all agents:
{{agent state}} 

Task description:
{{task description}}

Task milestones:
{{task milestones}}

Name list of agents:
{{agent name}}

You will adjust the description of the task for each agent and return a list of decomposed-assignment JSON objects. For example, for the task "move to (0, -60, 80) and (100, -60, 80)" assigned to Alex and Steve, you should return:
[{
    "reason": "Both agents have the same abilities to do the task, and they have the same items. The task description requires going to two locations. (0, -60, 80) is closer to Alex, so he should move there.",
    "description": "move to (0, -60, 80)",
    "milestones": ["at (0, -60, 80)"],
    "agent": "Alex"
},
{
    "reason": "Both agents have the same abilities to do the task, and they have the same items. The task description requires going to two locations. (100, -60, 80) is closer to Steve, so he should move there.",
    "description": "move to (100, -60, 80)",
    "milestones": ["at (100, -60, 80)"],
    "agent": "Steve"
}]

*** Important Notice ***
- Use natural language for reasoning and only provide the decomposed-assignment JSON once.
- If the task description is already accurate and easy to understand, then you don't need to make any adjustments.
- Ensure the description is adjusted for all agents. That means the length of the returned decomposed-assignment JSON list must be equal to the length of the agent name list.
Respond with a list of task-assignment JSON objects.
'''