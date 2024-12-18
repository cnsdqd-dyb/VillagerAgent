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
from model.vllm_model import VLLMLanguageModel
from random import random, randint, choice
from pipeline.agent_prompt import *
from pipeline.agent_rl_prompt import *
from rl_env import *
import numpy as np
import torch
from model.utils import extract_info

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
    RL_mode = "", rl_env = None, rl_model = None, all_tools = [], **kwargs):
        self.env = env
        self.name = name
        self.data_manager = data_manager
        self.llm = llm
        self.history_action_list = ["No action yet"]
        self.reflect_info = {"prompt": [], "response": []}
        self.RL_mode = RL_mode
        self.logger = logger
        self.all_tools = all_tools
        if not env.running:
            BaseAgent._virtual_debug = True

        if self.logger is None:
            self.logger = init_logger("BaseAgent", dump=True, silent=silent)
        
        if self.RL_mode == "PPO":
            self.rl_env = rl_env
            self.rl_model = rl_model

        self.instruction_history = []  # 新增：保存历史指令
        self.state_history = []        # 新增：保存历史状态

    def update_reflect(self, system_prompt, user_prompt, response):
        if type(user_prompt) == str:
            user_prompt = [user_prompt]
        prompt = str(system_prompt) + "\n"
        for i in range(len(user_prompt)):
            prompt += user_prompt[i] + "\n"

        self.reflect_info["prompt"].append(prompt)
        self.reflect_info["response"].append(response)
        with open(".cache/meta_setting.json", "r") as f:
            config = json.load(f)
            task_name = config["task_name"]
        if not os.path.exists("result/" + task_name):
            os.mkdir(os.path.join("result/", task_name))
        root = os.path.join("result/", task_name)
        with open(os.path.join(root, f"{self.name}_reflect.json"), "w") as f:
            json.dump(self.reflect_info, f, indent=4)

    def update_reflect(self, system_prompt, user_prompt, response):
        if type(user_prompt) == str:
            user_prompt = [user_prompt]
        prompt = str(system_prompt) + "\n"
        for i in range(len(user_prompt)):
            prompt += user_prompt[i] + "\n"

        self.reflect_info["prompt"].append(prompt)
        self.reflect_info["response"].append(response)
        with open(".cache/meta_setting.json", "r") as f:
            config = json.load(f)
            task_name = config["task_name"]
        if not os.path.exists("result/" + task_name):
            os.mkdir(os.path.join("result/", task_name))
        root = os.path.join("result/", task_name)
        with open(os.path.join(root, f"{self.name}_reflect.json"), "w") as f:
            json.dump(self.reflect_info, f, indent=4)

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
            if isinstance(self.llm, VLLMLanguageModel):
                return self.local_step(task)
            else:
                return self.normal_step(task)
        
    def rl_step(self, task:Task) -> (str, dict):
        # 构建基础提示和状态
        instruction = format_string(task_prompt, {
            "task_description": task.description,
            "milestone_description": task.milestones,
        })
        
        basic_state = format_string(state_prompt, {
            "env": self.data_manager.query_env_with_task(task.description),
            "relevant_data": smart_truncate(task.content, max_length=4096), 
        })

        max_rl_steps = 5
        actions = []
        observations = []
        current_state = basic_state
        task_status = False

        while max_rl_steps > 0:
            # 构建当前状态字符串
            current_context = f"{instruction}\n{current_state}"
            if actions and observations:
                action_history = "\n".join([f"Action: {a}\nObservation: {o}" for a, o in zip(actions, observations)])
                current_context += f"\nHistory:\n{action_history}"

            if self.env.agents_ping()["status"] == False:
                self.logger.info("Some agents are offline!")
                break 
            
            best_act, best_obs = None, None
            best_reward = -np.inf
            print(f"# max_rl_steps: {max_rl_steps}")
            k_step = 30
            while k_step > 0:
                # 获取模型动作
                # try:
                if self.env.agents_ping()["status"] == False:
                    self.logger.info("Some agents are offline!")
                    break 
                rl_action = self.rl_model.take_action(current_context)
                assert rl_action < len(self.rl_env.available_actions) and rl_action >= 0, f"{rl_action} must in 0-{len(self.rl_env.available_actions)}"
                rl_api = self.rl_env._get_available_actions()[rl_action]
                print(f"{rl_action} - {rl_api}")
                
                
                (act, obs), detail = self.env.rl_step(self.name, current_context + "You need try to use the tool, do not use Final Answer.", 
                                                    actions=actions, 
                                                    observations=observations, 
                                                    recommended_actions=[rl_api])
                if act is None:
                    continue
                    
                # 更新状态
                current_state = f"{basic_state}\nLast Action: {act}\nLast Observation: {obs}"
                
                # 计算奖励和任务状态
                reward, task_status = self.rl_one_step_reflect(
                    task.description, 
                    task.milestones,
                    actions=actions,
                    observations=observations,
                    act=act,
                    obs=obs,
                )

                # 构建转换字典
                transition_dict = {
                    "states": current_context,
                    "actions": rl_action,
                    "rewards": reward,
                    "next_states": f"{instruction}\n{current_state}",
                    "dones": task_status
                }

                # 更新模型
                self.rl_model.update(transition_dict)
                
                if self.RL_mode == "PPO":
                    self.rl_model.train_step()

                if reward > best_reward:
                    best_reward = reward
                    best_act, best_obs = act, obs

                k_step -= 1

                # except KeyboardInterrupt:
                #     self.logger.info("KeyboardInterrupt")
                #     raise KeyboardInterrupt
                # except ConnectionError:
                #     self.logger.error("ConnectionError")
                #     raise ConnectionError
                # except ConnectionRefusedError:
                #     self.logger.error("ConnectionRefusedError")
                #     raise ConnectionRefusedError
                # except Exception as e:
                #     self.logger.error(f"Error: {e}")

            actions.append(best_act)
            observations.append(best_obs)
            max_rl_steps -= 1

        status = self.env.agent_status(self.name)
        self.data_manager.update_database(AgentFeedback(task, detail, status).to_json())
        
        if task_status:
            summary = f"successfully done {task.description}."
            task.status = Task.success
        else:
            summary = f"failed to do {task.description}."
            task.status = Task.failure
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
    
    def local_step(self, task:Task) -> (str, dict):
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

        instruction = f"Your name is {self.name}.\n{task_str}"
        system_prompt = "You are Minecraft BaseAgent. You need to complete the task by following the environment feedback."

        prompts = [instruction]    

        action_list = []

        max_steps = 5
        while max_steps > 0:
            response = self.llm.few_shot_generate_thoughts(system_prompt, prompts, cache_enabled=False, max_tokens=256, json_check=False)
            
            prompts.append(response)

            response = response.split("Action: ")[-1].strip()
            response = response.split(", 'log': '")[0].strip()
            response = response + '}'
            print(response)
            response = json.loads(response.replace("'", '"'))

            func_name = response["tool"]
            tool_input = response["tool_input"]
            print(response)
            print(func_name)
            print(tool_input)
            final_answer = None
            for tool in self.all_tools:
                if tool.name == func_name:
                    if tool.name == 'stop':
                        max_steps = 0
                        final_answer = tool_input['final_answer']
                        break

                    feedback = tool(tool_input)
                    user = f"Feedback: {feedback.get('message')}\nStatus: {feedback.get('status')}\nNew Events: {feedback.get('new_events')}"
                    
                    action_list.append({"action": response, "feedback": feedback.get('message')})

                    prompts.append(user)
                    print(feedback)
                    final_answer = user
                    break
                
            max_steps -= 1



        status = self.env.agent_status(self.name)

        detail = {"input": instruction, "action_list": action_list, "final_answer": final_answer}
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
    
    def rl_one_step_reflect(self, task_description, milestone_description, actions, observations, act, obs):
        '''
        One step reflect
        '''
        act_obs = ""
        for act, obs in zip(actions, observations):
            act_obs += f"\n{act['log']}\n{obs}"
        
        if obs["status"] == False:
            return -1, False

        prompt = format_string(one_step_reflect_prompt,
            {
                "task_description": task_description,
                "milestone_description": milestone_description,
                "action_observation": act_obs,
                "act": act,
                "obs": obs,
            })
        
        response = self.llm.few_shot_generate_thoughts(reflect_system_prompt, prompt, cache_enabled=False, max_tokens=256, json_check=True,
                                                    check_tags=["task_status", "reward"])
        print(response)
        result = extract_info(response)[0]
        task_status = result["task_status"]
        reward = result["reward"]
        print(f"rl_action: {act}, reward: {reward}")
        return reward, task_status
    
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
        self.update_reflect(reflect_system_prompt, prompt, response)
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
