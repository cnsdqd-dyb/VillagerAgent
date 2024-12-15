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

one_step_reflect_prompt_v2 = '''
Now let's evaluate the #RL-Recommended-Action taken for this task.

Task Description:
{{task_description}}

Current Milestone:
{{milestone_description}}

Actions and Observations:
{{action_observation}}

#RL-Recommended-Action:
{{rl_action}}

Remember to rate the #RL-Recommended-Action with a reward:
1. Rate the #RL-Recommended-Action with a reward:
   -2: Definitely wrong
   -1: Useless/irrelevant
    0: Potentially useful
    1: Useful
    2: Highly effective
2. Has the task been completed? (true/false)

Return in JSON format directly.
{
    "reward": int,   # Value from -2 to 2
    "task_status": bool  # true if milestone is satisfied else false
}
'''

one_step_reflect_prompt = '''
Now let's evaluate whether the latest action is reasonable or not suitable for current step.

Task Description:
{{task_description}}

Current Milestone:
{{milestone_description}}

Actions and Observations:
{{action_observation}}

New Action:
{{act}}

New Observation:
{{obs}}

Has the task been completed? (true/false)

Return in JSON format directly.
{
    "reward": int # -2, -1, 0, 1, 2 the latest action from action_observation if is suitable for current step
    "task_status": bool  # true if milestone is satisfied else false
}
'''