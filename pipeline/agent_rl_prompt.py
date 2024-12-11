task_prompt = ''' 
*** Task ***
{{task_description}}
*** milestone ***
{{milestone_description}}
'''

state_prompt = '''
*** environment ***
{{env}}
*** The relevant data***
{{relevant_data}}
'''

one_step_reflect_prompt = '''
Now let's evaluate the #[RL Recommended Action] taken for this task.

Task Description:
{{task_description}}

Current Milestone:
{{milestone_description}}

Actions and Observations:
{{action_observation}}

#[RL Recommended Action]:
{{rl_action}}

Please analyze:
1. Does the current #[RL recommended action] match the most recent LLM action? Is it reasonable?
2. Rate the #[RL recommended action] with a reward:
   -2: Definitely wrong
   -1: Useless/irrelevant
    0: Potentially useful
    1: Useful
    2: Highly effective
3. Has the task been completed? (true/false)

Return in JSON format:
{
    "summary": str,  # Analysis explanation
    "reward": int,   # Value from -2 to 2
    "task_status": bool  # true if milestone is satisfied else false
}
'''