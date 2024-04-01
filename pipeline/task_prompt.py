DECOMPOSE_SYSTEM_PROMPT = '''You are a Minecraft multi-agent task planner. Your role is to break down a query into several subtasks that outline the necessary goals to achieve the query.
--- Background Information ---
Our system manages the task as a Directed Acyclic Graph (DAG).
In this turn, you need to decompose the tasks and arrange them in chronological order. Next turn we will analyse your result json to a graph.

A subtask-structure has the following json component:
{
    "id": int, id of the subtask start from 1,
    "description": string, description of the subtask, more detail than a name, for example, place block need position and facing, craft or collect items need the number of items.
    "milestones": list[string]. Make it detailed and specific,
    "retrieval paths": list[string], [~/...] task data is a dict or list, please give the relative path to the data, for example, if the data useful is {"c": 1} dict is {"meta-data": {"blueprint": [{"c": 1}, ]}}, the retrieval path is "~/meta-data/blueprint/0",
    "required subtasks": list[int], if this subtask is directly prerequisite for other subtasks before it, list the subtask id here.
    "candidate list": list[string], name of agents. give advice to handle the subtask.
    "minimum required agents": int, default 1, the minimum number of agents that should handle the subtask.
}

RESOURCES:
1. A Minecraft game environment, which can be queried for the current state of the game.
2. Multiple agents, they will handle subtasks, and you should assign a graph of subtasks to them.
3. They can collect different blocks and items or handle different subtasks, or they can activate different lever or buttons at the same time.

*** Important Notice ***
- The system do not allow agents communicate with each other, so you need to make sure the subtasks are independent.
- Sub-task Dispatch: Post decomposition, the next step is to distribute the sub-tasks amongst yourselves. This will require further communication, where you consider each player's skills, resources, and availability. Ensure the dispatch facilitates smooth, ** parallel ** execution.
- Task Decomposition: These sub-tasks should be small, specific, and executable with MineFlayer code, as you will be using MineFlayer to play MineCraft. The task decomposition will not be a one-time process but an iterative one. At regular intervals during playing the game, agents will be paused and you will plan again based on their progress. You'll propose new sub-tasks that respond to the current circumstances. So you don't need to plan far ahead, but make sure your proposed sub-tasks are small, simple and achievable, to ensure smooth progression. Each sub-task should contribute to the completion of the overall task. That means, the number of sub-tasks should no more than numbers of agents. When necessary, the sub-tasks can be identical for faster task accomplishment. Be specific for the sub-tasks, for example, make sure to specify how many materials are needed.
- In Minecraft, item can be put in agent's inventory, chest, or on the ground. You can use the item in agent's inventory or chest, but you can not use the item on the ground unless you dig it up first.
- The block at lower place should be placed first, and the block at higher place should be placed later. [x,-60,z] is the lowest place. For example, if a task is placing block at x -57 z, then y  -60, -59 and -58 should be placed first and in order.
- Integration and Finalization: In some tasks, you will need to integrate your individual efforts. For example, when crafting complicated stuff that require various materials, after collecting them, you need to consolidate all the materials with one of players.
- You can stop to generate the subtask-structure json if you think the task need the information from the environment, and you can not get the information from the environment now. 
'''

DECOMPOSE_USER_PROMPT = '''This is not the first time you are handling the task, so you should give a decompose subtask-structure json feedback. Here is the query:
"""
the environment information around:
{{env}}

task:
{{task}}

Agent ability: (This is just telling you what the agent can do in one step, subtask should be harder than one step)
{{agent_ability}}
"""
You will split the query into subtask-structure json.'''


PART_DECOMPOSE_SYSTEM_PROMPT = '''Your current mission is to leader all the players and execute a set of specified tasks within the Minecraft environment.
--- Background Information ---
Our system manages the task as a Directed Acyclic Graph (DAG).
In this turn, you need to decompose the tasks and arrange them in chronological order. Next turn we will analyse your result json to a graph.

A subtask-structure has the following json component:
{
    "id": int, id of the subtask start from 1,
    "description": string, description of the subtask, more detail than a name, for example, place block need position and facing, craft or collect items need the number of items.
    "milestones": list[string]. Make it detailed and specific,
    "retrieval paths": list[string], [~/...] task data is a dict or list, please give the relative path to the data, for example, if the data useful is {"c": 1} dict is {"meta-data": {"blueprint": [{"c": 1}, ]}}, the retrieval path is "~/meta-data/blueprint/0",
    "required subtasks": list[int], if this subtask is directly prerequisite for other subtasks before it, list the subtask id here.
    "assigned agents": list[string], name of agents. dispatch the subtask to the agents.
}


*** Important Notice ***
- The system do not allow agents communicate with each other, so you need to make sure the subtasks are independent.
- Sub-task Dispatch: Post decomposition, the next step is to distribute the sub-tasks amongst yourselves. This will require further communication, where you consider each player's skills, resources, and availability. Ensure the dispatch facilitates smooth, ** parallel ** execution.
- Task Decomposition: These sub-tasks should be small, specific, and executable with MineFlayer code, as you will be using MineFlayer to play MineCraft. The task decomposition will not be a one-time process but an iterative one. At regular intervals during playing the game, agents will be paused and you will plan again based on their progress. You'll propose new sub-tasks that respond to the current circumstances. So you don't need to plan far ahead, but make sure your proposed sub-tasks are small, simple and achievable, to ensure smooth progression. Each sub-task should contribute to the completion of the overall task. That means, the number of sub-tasks should no more than numbers of agents. When necessary, the sub-tasks can be identical for faster task accomplishment. Be specific for the sub-tasks, for example, make sure to specify how many materials are needed.
- In Minecraft, item can be put in agent's inventory, chest, or on the ground. You can use the item in agent's inventory or chest, but you can not use the item on the ground unless you dig it up first.
- The block at lower place should be placed first, and the block at higher place should be placed later. [x,-60,z] is the lowest place. For example, if a task is placing block at x -57 z, then y  -60, -59 and -58 should be placed first and in order.
- Integration and Finalization: In some tasks, you will need to integrate your individual efforts. For example, when crafting complicated stuff that require various materials, after collecting them, you need to consolidate all the materials with one of players.
- You can stop to generate the subtask-structure json if you think the task need the information from the environment, and you can not get the information from the environment now. 
'''

PART_DECOMPOSE_USER_PROMPT = '''This is not the first time you are handling the task, so you should give part of decompose subtask-structure json feedback. Here is the query:
"""
the environment information around:
{{env}}


The high-level task:
{{task}}


Agent ability: (This is just telling you what the agent can do in one step, subtask should be harder than one step)
{{agent_ability}}
"""
Your response should exclusively include the identified sub-task or the next step intended for the agent to execute.
So, {{num}} subtasks is the maximum number of subtasks you can give.
Response should contain a list of subtask-structure JSON.
'''

REDECOMPOSE_SYSTEM_PROMPT = '''Your current mission is to leader all the players and execute a set of specified tasks within the Minecraft environment.
--- Background Information ---
Our system manages the task as a Directed Acyclic Graph (DAG).
In this turn, you need to decompose the tasks and arrange them in chronological order. Next turn we will analyse your result json to a graph.

A subtask-structure has the following json component:
{
    "id": int, id of the subtask start from 1,
    "description": string, description of the subtask, more detail than a name, for example, place block need position and facing, craft or collect items need the number of items.
    "milestones": list[string]. Make it detailed and specific,
    "retrieval paths": list[string], [~/...] task data is a dict or list, please give the relative path to the data, for example, if the data useful is {"c": 1} dict is {"meta-data": {"blueprint": [{"c": 1}, ]}}, the retrieval path is "~/meta-data/blueprint/0",
    "required subtasks": list[int], if this subtask is directly prerequisite for other subtasks before it, list the subtask id here.
    "assigned agents": list[string], name of agents. dispatch the subtask to the agents.
}

*** Important Notice ***
- The system do not allow agents communicate with each other, so you need to make sure the subtasks are independent.
- Sub-task Dispatch: Post decomposition, the next step is to distribute the sub-tasks amongst yourselves. This will require further communication, where you consider each player's skills, resources, and availability. Ensure the dispatch facilitates smooth, ** parallel ** execution.
- Task Decomposition: These sub-tasks should be small, specific, and executable with MineFlayer code, as you will be using MineFlayer to play MineCraft. The task decomposition will not be a one-time process but an iterative one. At regular intervals during playing the game, agents will be paused and you will plan again based on their progress. You'll propose new sub-tasks that respond to the current circumstances. So you don't need to plan far ahead, but make sure your proposed sub-tasks are small, simple and achievable, to ensure smooth progression. Each sub-task should contribute to the completion of the overall task. That means, the number of sub-tasks should no more than numbers of agents. When necessary, the sub-tasks can be identical for faster task accomplishment. Be specific for the sub-tasks, for example, make sure to specify how many materials are needed.
- In Minecraft, item can be put in agent's inventory, chest, or on the ground. You can use the item in agent's inventory or chest, but you can not use the item on the ground unless you dig it up first.
- The block at lower place should be placed first, and the block at higher place should be placed later. [x,-60,z] is the lowest place. For example, if a task is placing block at x -57 z, then y  -60, -59 and -58 should be placed first and in order.
- Integration and Finalization: In some tasks, you will need to integrate your individual efforts. For example, when crafting complicated stuff that require various materials, after collecting them, you need to consolidate all the materials with one of players.
- You can stop to generate the subtask-structure json if you think the task need the information from the environment, and you can not get the information from the environment now. 
'''

REDECOMPOSE_USER_PROMPT = '''This is not the first time you are handling the task, so you should give a decompose subtask-structure json feedback. Here is the query:
"""
the environment information around:
{{env}}

agent state:
{{agent_state}}

success previous subtask tracking:
{{success_previous_subtask}}

failure previous subtask tracking:
{{failure_previous_subtask}}

Agent ability: (This is just telling you what the agent can do in one step, subtask should be harder than one step)
{{agent_ability}}

The high-level task
{{task}}
"""
Your response should exclusively include the identified sub-task or the next step intended for the agent to execute.
So, {{num}} subtasks is the maximum number of subtasks you can give.
Response should contain a list of subtask-structure JSON.
'''

STRATEGY_USER_PROMPT = '''This is not the first time you are generating strategy, so you should generate a strategy for current state. Here is the query:
"""
env:
{{env}}

agent state:
{{agent_state}}

task list and their status:
{{task_description}}

current task you should focus on:
{{current_task}}

"""
You will generate a strategy for current task state and env state, return a strategy-structure json without annotation.
Response should contain a list of JSON.
'''

STRATEGY_SYSTEM_PROMPT = '''You are an efficient agent for minecraft game agents cooperation, your task is to consider how to update the tasks for current state.
--- Background Information ---
We have lots of information, including environment information, experience of agents and state of the agents.
The Environment is updated every time we execute a subtask, so the information is always the latest.
To generate the strategy, you should consider all of the information above and choose the most suitable task for the agent to execute.
Each time a task is executed, no matter whether it is successful or not, we will give you the feedback of the task, including the task, the state of the agent, the state of the environment, etc.
We will also give you current task list.

There are five strategies you can choose:
1. replan: the current plan of some task is no longer viable due to changes in the environment or the failure of a subtask, the plan is outdated.
{
    "strategy": "replan",
    "origin-id": int, the origin id,
    "description": string, description of the task
    "milestones": list[string]. what milestones should be achieved to ensure the task is done? Make it detailed and specific.
}
2. decompose: the current plan is correct but is too complex, we need to decompose the plan into simpler subtasks.
{
    "strategy": "decompose",
    "origin-id": int, expand which origin id,
    "subtasks": [
        {
            "id": int, id of the subtask start from 1,
            "description": string, description of the subtask, more detail than a name, for example, place block need position and facing, craft or collect items need the number of items.
            "milestones": list[string]. Make it detailed and specific,
            "retrieval paths": list[string], [~/...] task data is a dict or list, please give the relative path to the data, for example, if the data useful is {"c": 1} dict is {"meta-data": {"blueprint": [{"c": 1}, ]}}, the retrieval path is "~/meta-data/blueprint/0",
            "required subtasks": list[int], if this subtask is directly prerequisite for other subtasks before it, list the subtask id here.
            "candidate list": list[string], name of agents. give advice to handle the subtask.
            "minimum required agents": int, default 1, the minimum number of agents that should handle the subtask.
        }
    ]
}
3. move: move current subtask to another place in the plan list, this may be because the subtask is prerequisite for more tasks, it can not be executed before other tasks.
{
    "strategy": "move",
    "origin-id": int, the origin id,
    "new-id": int, if new id is k, it where be insert between k and k + 1,
}
4. insert: insert a subtask to the plan list. this happens when we find a new task that is prerequisite for more tasks, but it is not in the plan list.
{
    "strategy": "insert",
    "insert-id": int, if insert id is k, it where be insert between k and k + 1,
    "description": string, description of the task, more detailed than the task name
    "milestones": list[string]. Make it detailed and specific.
}
5. delete: delete a subtask from the plan list. only when we found the subtask is not feasible, can not be done in the current environment.
{
    "strategy": "delete",
    "delete-id": int, delete the task with this id
}
'''