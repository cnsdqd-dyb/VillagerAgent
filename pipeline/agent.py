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

# class ChatPlugin:
#     '''
#     ### ChatPlugin is the plugin for the agent to chat with the environment
#     # TODO: still need to be implemented
#     '''
#     def __init__(self, llm:OpenAILanguageModel, env:VillagerBench, logger:logging.Logger = None, silent = False, **kwargs):
#         self.llm = llm
#         self.logger = logger
#         if self.logger is None:
#             self.logger = init_logger("ChatPlugin", dump=True, silent=silent)

#         self.chat_history = []
#         self.important_info = []
#         self.role_description = ""
#         self.name = ""
#         self.env = env


#     def chat(self):
#         message = self.env.get_msg(self.name)
#         self.chat_history.append(message)
#         if isinstance(self.llm, OpenAILanguageModel):
#             response = self.llm.few_shot_generate_thoughts(self.role_description, message, cache_enabled=False, max_tokens=256, json_check=True)
#         else:
#             response = self.llm.few_shot_generate_thoughts(self.role_description, message, cache_enabled=False, max_tokens=256, json_check=True)
#         self.chat_history.append({"name": self.name, "message": response})
        
        

class BaseAgent:
    '''
    ### BaseAgent is the single agent in the system, it can take action and reflect
    
    step: take an action and return the feedback and detail
    reflect: reflect on the task and return the result
    to_json: return the json format of the agent
    '''
    _virtual_debug = False
    def __init__(self, llm:OpenAILanguageModel , env:VillagerBench, data_manager:DataManager, name:str, logger:logging.Logger = None, silent = False, **kwargs):
        self.env = env
        self.name = name
        self.data_manager = data_manager
        self.llm = llm
        self.history_action_list = ["No action yet"]

        self.logger = logger
        if not env.running:
            BaseAgent._virtual_debug = True

        if self.logger is None:
            self.logger = init_logger("BaseAgent", dump=True, silent=silent)

    def step(self, task:Task) -> (str, dict):
        '''
        take an action and return the feedback and detail
        return: final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}
        '''
        if BaseAgent._virtual_debug:
            return self.virtual_step(task)
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
        while max_retry > 0:
            try:
                feedback, detail = self.env.step(self.name, task_str)
                break
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
