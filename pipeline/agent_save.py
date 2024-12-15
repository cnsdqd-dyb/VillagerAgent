import sys
import os
sys.path.append(os.getcwd())
import time
import logging
from env.env import VillagerBench
from type_define.graph import Task
from pipeline.data_manager import DataManager
from pipeline.utils import *
from model.openai_models import OpenAILanguageModel
from random import random, randint, choice
from pipeline.agent_prompt import *
from pipeline.agent_rl_prompt import *
from rl_env import *
import numpy as np
import torch

class AgentFeedback:
    def __init__(self, task:Task, detail, status):
        self.task = task
        self.detail = detail
        self.status = status

    def to_json(self) -> dict:
        return {
            "task": self.task.to_json(),
            "detail": self.detail,
            "status": self.status,
        }

        

class BaseAgent:
    '''
    ### BaseAgent is the single agent in the system, it can take action and reflect
    
    step: take an action and return the feedback and detail
    reflect: reflect on the task and return the result
    to_json: return the json format of the agent
    '''
    _virtual_debug = False
    def __init__(self, llm:OpenAILanguageModel , env:VillagerBench, data_manager:DataManager, name:str, logger:logging.Logger = None, silent = False, 
    RL_mode = "", rl_env = None, rl_model = None, **kwargs):
        self.env = env
        self.name = name
        self.data_manager = data_manager
        self.llm = llm
        self.history_action_list = ["No action yet"]
        self.RL_mode = RL_mode
        self.logger = logger
        if not env.running:
            BaseAgent._virtual_debug = True

        if self.logger is None:
            self.logger = init_logger("BaseAgent", dump=True, silent=silent)
        
        if self.RL_mode == "PPO":
            self.rl_env = rl_env
            self.rl_model = rl_model
        

    def step(self, task:Task) -> (str, dict):
        '''
        take an action and return the feedback and detail
        return: final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}
        '''
        if BaseAgent._virtual_debug:
            return self.virtual_step(task)

        if self.RL_mode != "":
            return self.rl_step(task)

        else:
            return self.normal_step(task)    
        
    def rl_step(self, task:Task) -> (str, dict):
        if len(task._agent) == 1:
            task_str = format_string(agent_prompt, {"task_description": task.description, "milestone_description": task.milestones, 
                                    "env": self.data_manager.query_env_with_task(task.description),
                                    "relevant_data": smart_truncate(task.content, max_length=4096), # TODO: change to "relevant_data": task.content
                                    "agent_name": self.name,
                                    "agent_state": self.data_manager.query_history(self.name),
                                    "other_agents": self.other_agents(),
                                    "agent_action_list": self.history_action_list,
                                    "minecraft_knowledge_card": minecraft_knowledge_card})
        else:
            task_str = format_string(agent_cooper_prompt, {"task_description": task.description, "milestone_description": task.milestones, 
                                    "env": self.data_manager.query_env_with_task(task.description),
                                    "relevant_data": smart_truncate(task.content, max_length=4096), # TODO: change to "relevant_data": task.content
                                    "agent_name": self.name,
                                    "agent_state": self.data_manager.query_history(self.name),
                                    "other_agents": self.other_agents(),
                                    "agent_action_list": self.history_action_list,
                                    "team_members": ", ".join(task._agent),
                                    "minecraft_knowledge_card": minecraft_knowledge_card})
            
        self.logger.debug("="*20 + " Agent Step " + "="*20)
        self.logger.info(f"{self.name} try task:\n {task.description}")
        self.logger.info(f"{self.history_action_list}")
        self.logger.info(f"other agents: {self.other_agents()}")
        self.logger.info(f"{self.name} status:\n {self.data_manager.query_history(self.name)}")
        
        
        instruction = format_string(task_prompt, {
            "task_description": task.description,
            "milestone_description": task.milestones,
        })
        basic_state = format_string(state_prompt, {
            "env": self.data_manager.query_env_with_task(task.description),
            "relevant_data": smart_truncate(task.content, max_length=4096), 
        })
        if self.RL_mode == "DQN":
            self.rl_env.set_current_state(
                instrucition=task_str,
                state=task_str,
            )
        elif self.RL_mode == "PPO":
            instr_token, basic_state_token = self.rl_env.token_current_state(instruction, basic_state)
            
        max_rl_steps = 5
        actions = []
        observations = []
        act_obs_state_token = None
        task_status = False

        while max_rl_steps > 0 and not task_status:
            transition_dict = {}
            if self.RL_mode == "PPO":
                if act_obs_state_token is None:
                    state_token = basic_state_token
                else:
                    state_token = np.concatenate([basic_state_token, next_act_obs_state_token], axis=0)

                state_token = np.concatenate([instr_token, state_token], axis=0)
            else:
                raise NotImplementedError
            # print(state_token)
            rl_action = self.rl_model.take_action(state_token)
            assert rl_action < len(self.rl_env.available_actions) and rl_action >= 0, f"{rl_action} must in 0-{len(self.rl_env.available_actions)}"
            rl_api = self.rl_env._get_available_actions()[rl_action]
            print(f"{rl_action} - {rl_api}")
            # input("press")
            (act, obs), detail = self.env.rl_step(self.name, task_str, actions=actions, observations=observations, recommended_actions=[rl_api])
            next_act_obs_state_token = self.rl_env.token_current_action_observation(act, obs)
            # ts = torch.tensor(next_act_obs_state_token, dtype=torch.float32)
            # print(ts.shape)
            # input("press")
            if act == None:
                continue
            actions.append(act)
            observations.append(obs)
            max_rl_steps -= 1


            reward, task_status, summary = self.rl_one_step_reflect(task.description, task.milestones, actions=actions, observations=observations, rl_action=rl_api)

            if self.RL_mode == "PPO":
                if act_obs_state_token is None:
                    state_token = basic_state_token
                else:
                    state_token = np.concatenate([basic_state_token, next_act_obs_state_token], axis=0)
                next_state_token = next_act_obs_state_token

                state_token = np.concatenate([instr_token, state_token], axis=0)
                next_state_token = np.concatenate([instr_token, next_state_token], axis=0)
            else:
                raise NotImplementedError
            
            transition_dict["states"] = state_token
            transition_dict["next_states"] = next_state_token
            transition_dict["actions"] = rl_action
            transition_dict["rewards"] = reward
            transition_dict["dones"] = task_status

            act_obs_state_token = next_act_obs_state_token
            self.rl_model.update(transition_dict)

            if self.RL_mode == "PPO":
                self.rl_model.train_step()
              
        status = self.env.agent_status(self.name)
        self.data_manager.update_database(AgentFeedback(task, detail, status).to_json())

        # self.data_manager.save()
        return summary, detail
    

    def normal_step(self, task:Task) -> (str, dict):
        if len(task._agent) == 1:
            task_str = format_string(agent_prompt, {"task_description": task.description, "milestone_description": task.milestones, 
                                    "env": self.data_manager.query_env_with_task(task.description),
                                    "relevant_data": smart_truncate(task.content, max_length=4096), # TODO: change to "relevant_data": task.content
                                    "agent_name": self.name,
                                    "agent_state": self.data_manager.query_history(self.name),
                                    "other_agents": self.other_agents(),
                                    "agent_action_list": self.history_action_list,
                                    "minecraft_knowledge_card": minecraft_knowledge_card})
        else:
            task_str = format_string(agent_cooper_prompt, {"task_description": task.description, "milestone_description": task.milestones, 
                                    "env": self.data_manager.query_env_with_task(task.description),
                                    "relevant_data": smart_truncate(task.content, max_length=4096), # TODO: change to "relevant_data": task.content
                                    "agent_name": self.name,
                                    "agent_state": self.data_manager.query_history(self.name),
                                    "other_agents": self.other_agents(),
                                    "agent_action_list": self.history_action_list,
                                    "team_members": ", ".join(task._agent),
                                    "minecraft_knowledge_card": minecraft_knowledge_card})
            
        self.logger.debug("="*20 + " Agent Step " + "="*20)
        self.logger.info(f"{self.name} try task:\n {task.description}")
        self.logger.info(f"{self.history_action_list}")
        self.logger.info(f"other agents: {self.other_agents()}")
        self.logger.info(f"{self.name} status:\n {self.data_manager.query_history(self.name)}")
        max_retry = 3
        
        instruction = format_string(task_prompt, {
            "task_description": task.description,
            "milestone_description": task.milestones,
        })
        state = format_string(state_prompt, {
            "other_agents": self.other_agents(),
            "agent_name": self.name,
            "env": self.data_manager.query_env_with_task(task.description),
            "relevant_data": smart_truncate(task.content, max_length=4096), 
            "agent_state": self.data_manager.query_history(self.name),
        })
      
        while max_retry > 0:
            try:
                feedback, detail = self.env.step(self.name, task_str)
                break
            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt")
                raise KeyboardInterrupt
            except ConnectionError:
                self.logger.error("ConnectionError")
                raise ConnectionError
            except ConnectionRefusedError:
                self.logger.error("ConnectionRefusedError")
                raise ConnectionRefusedError
            except Exception as e:
                self.logger.error(f"Error: {e}")
                max_retry -= 1
                time.sleep(3)
        status = self.env.agent_status(self.name)
        self.data_manager.update_database(AgentFeedback(task, detail, status).to_json())

        # self.data_manager.save()
        return feedback, detail
   

    def other_agents(self) -> [str]:
        '''
        return the feedback of other agent's pretask
        '''
        return self.data_manager.query_other_agent_state(self.name)
    
    def action_format(self, action:dict) -> str:
        action_str = '''{{message}}'''
        return format_string(action_str, action["feedback"])
    
    def rl_one_step_reflect(self, task_description, milestone_description, actions, observations, rl_action):
        '''
        One step reflect
        '''
        act_obs = ""
        for act, obs in zip(actions, observations):
            act_obs += f"\n{act['log']}\n{obs}"
        
        prompt = format_string(one_step_reflect_prompt,
            {
                "task_description": task_description,
                "milestone_description": milestone_description,
                "action_observation": act_obs,
                "rl_action": rl_action
            })
        
        response = self.llm.few_shot_generate_thoughts(reflect_system_prompt, prompt, cache_enabled=False, max_tokens=256, json_check=True)
        print(response)
        result = extract_info(response)[0]
        summary = result["summary"]
        reward = result["reward"]
        task_status = result["task_status"]
        return reward, task_status, summary
    
    def reflect(self, task: Task, detail) -> bool:
        '''
        Reflect on the task and return the result
        '''
        task_description = task.description
        milestone_description = task.milestones
        action_history = detail["action_list"]
        global reflect_system_prompt, reflect_user_prompt
        if isinstance(self.llm, OpenAILanguageModel):
            prompt = format_string(reflect_user_prompt,
                                   {
                                       "task_description": task_description,
                                       "milestone_description": milestone_description,
                                       "state": self.data_manager.query_history(self.name),
                                       "action_history": action_history
                                   })
            response = self.llm.few_shot_generate_thoughts(reflect_system_prompt, prompt, cache_enabled=False, max_tokens=256, json_check=True)
        else:
            prompt = format_string(reflect_user_prompt,
                                   {
                                       "task_description": task_description,
                                       "milestone_description": milestone_description,
                                       "state": self.data_manager.query_history(self.name),
                                       "action_history": action_history
                                   })
            response = self.llm.few_shot_generate_thoughts(reflect_system_prompt, prompt, cache_enabled=False, max_tokens=256, json_check=True)
        # print(response)
        result = extract_info(response)[0]
        task.reflect = result
        task._summary.append(result["summary"])

        # add the action to the history
        self.history_action_list = [self.action_format(action) for action in action_history]
        return result["task_status"]
    
    def to_json(self) -> dict:
        return {
            "name": self.name
        }
    
    def virtual_env(name:str):
        '''
        ### virtual_env is the virtual environment for the agent to test the agent
        return the virtual environment
        '''
        env = {
            "I_held_item": {
                "spruce_planks": 1
            },
            "sign": "text",
            "blocks": [
                {
                    "spruce_planks": [
                        -3,
                        -60,
                        0
                    ]
                }
            ],
            "equipment": "hidden",
            "food": 20,
            "health": 20,
            "my_name": name,
            "my_position": [
                -1,
                -59,
                1
            ],
            "nearby_entities": [
                
            ],
            "oxygen": 20,
            "saturation": 2,
            "timeOfDay": "sunrise"
        }
        
        env = {
            "message": env,
            "status": True
        }
        return env

    def virtual_step(self, task:Task) -> (str, dict):
        '''
        ### virtual_step is the virtual step for the agent to test the agent
        take an action and return the feedback and detail
        return: final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}
        '''
        # random action
        action = choice(["place", "dig", "find", "open"])
        input = smart_truncate(task.to_json(), max_length=4096)
        random_action_num = randint(1, 10)
        action_list = []
        for i in range(random_action_num):
            action_dict = {
                "tool" : action,
                "tool_input" : {
                    "player_name": self.name,
                    "x": randint(-100, 100),
                    "y": randint(-100, 100),
                    "z": randint(-100, 100),
                },
                "log": "random action"
            }
            feedback = {
                "message": f"execute {action_dict['tool']} at {action_dict['tool_input']['x']} {action_dict['tool_input']['y']} {action_dict['tool_input']['z']}",
                "status": True
            }
            action_list.append({"action": action_dict, "feedback": feedback})
        score = random()
        if score > 0.3:
            final_answer = f"successfully done {task.description}."
            task.status = Task.success
        else:
            final_answer = f"failed to do {task.description}."
            task.status = Task.failure
        detail = {
            "input": input,
            "action_list": action_list,
            "final_answer": final_answer,
        }
        
        self.data_manager.update_database(AgentFeedback(task, detail, VillagerBench.virtual_env(self.name)).to_json())
        # self.data_manager.save()
        return final_answer, {"input": input, "action_list": action_list, "final_answer": final_answer}
