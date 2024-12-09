import datetime

import numpy as np
from langchain.retrievers.multi_vector import SearchType

from model.openai_models import OpenAILanguageModel
from pipeline.data_prompt import SOMEONE_NEARBY_INFO_FORMAT, NOONE_NEARBY_INFO_FORMAT, AGENT_INFO_STORE_FORMAT, \
    SUCCESS_DECOMPOSE_PLAN_FORMAT, NOT_SUCCESS_DECOMPOSE_PLAN_FORMAT, PERSON_INFO_FORMAT, ENVIRONMENT_INFO_FORMAT, \
    HISTORY_SUMMARY_PROMPT, \
    SUMMARY_ENVIRONMENT_SYSTEM_PROMPT, SUMMARY_ENVIRONMENT_EXAMPLE_PROMPT
from type_define.decomposed_summary_system import DecomposeSummarySystem
from type_define.task_summary_tree import TaskSummaryTree
from type_define.graph import Task, Graph
from pipeline.utils import *
import logging
import random

class DataManager:
    '''
    DataManager is responsible for managing the data of the environment, agent, history, and experience.

    Args:
        use_cache: bool, whether to use cache
        silent: bool, whether to print log
        model_name: str, the name of the language model
    '''
    def __init__(self, use_cache=False, silent=False, model_name="gpt-4-1106-preview"):
        self._experience_path = "data/experience.json"
        self._history_path = "data/history.json"
        self._env_path = "data/env.json"
        self._agent_path = "data/agent.json"
        self._cache = {}
        self._history_data = {}
        self._env_data = {
            "person_info": [],
            "blocks_info": [],
            "sign_info": "",
            "nearby_entities": [],
            "time": None
        }
        self._agent_data = []
        if use_cache:
            self._history_data = self._load_json(self._history_path)
            self._env_data = self._load_json(self._env_path)
            self._agent_data = self._load_json(self._agent_path)

        self.llm = None
        self.model = model_name
        
        self.query_history_log = {"prompt": [], "response": []}
        self.update_history_log = {"prompt": [], "response": []}

        self._logger = init_logger("DataManager", dump=True, silent=silent)
        self._logger.info("DataManager initialized")

    @staticmethod
    def _process_experience(info: dict) -> dict:
        # process experience
        info_copy = info.copy()
        action_list = []
        for action in info_copy["detail"]["action_list"]:
            action_list.append(action["action"]["tool"])
        task = info_copy["task"]["description"]

        success = False
        if info_copy["task"]["status"] == Task.success:
            success = True

        return {
            "action_list": action_list,
            "task": task,
            "success": success
        }

    @staticmethod
    def _process_history(info: dict) -> dict:
        # process history
        info_copy = info.copy()
        name = info_copy["status"]["my_name"]

        action_list = []
        try:
            for action in info_copy["detail"]["action_list"]:
                action["feedback"]["status"] = str(action["feedback"]["status"])
                action_dict = {
                    "behavior": action["action"]["tool"],
                    "feedback": action["feedback"]["message"]
                }
                action_list.append(action_dict)
        except Exception as e:
            # self.logger.ERROR(info_copy)
            raise e        
        
        held_items = info_copy["status"]["I_held_item"]
        holding_items_str = ""
        for i, (item, num) in enumerate(held_items.items()):
            if i != 0:
                holding_items_str += ", "
            holding_items_str += f"{item}*{num}"
        if holding_items_str == "":
            holding_items_str = "nothing"

        inventory = info_copy["status"]["inventory"]
        inventory_str = ""
        for i, item in enumerate(inventory):
            if i != 0:
                inventory_str += ", "
            item_name = list(item.keys())[0]
            num = item[item_name]
            inventory_str += f"{item_name}*{num}"
        if inventory_str == "":
            inventory_str = "nothing"

        return {
            "name": name,
            "action_list": action_list,
            "held_items": holding_items_str,
            "bag(aka inventory)": inventory_str
        }

    @staticmethod
    def _process_env(info: dict) -> dict:
        # process env
        info_copy = info.copy()
        person_info = {
            "name": info_copy["status"]["my_name"],
            "position": info_copy["status"]["my_position"],
            # "health": info_copy["status"]["health"],
            # "food": info_copy["status"]["food"],
            "held_items": info_copy["status"]["I_held_item"]
        }
        blocks_info = info_copy["status"]["blocks"]
        entity_info = info_copy["status"]["nearby_entities"]
        sign_info = info_copy["status"]["sign"]
        time = info_copy["status"]["timeOfDay"]

        return {
            "person_info": person_info,
            "blocks_info": blocks_info,
            "sign_info": sign_info,
            "time": time,
            "nearby_entities": entity_info
        }

    @staticmethod
    def _process_agent(info: dict) -> dict:
        # process agent
        info_copy = info.copy()
        name = info_copy["status"]["my_name"]
        position = info_copy["status"]["my_position"]

        nearby_name_list = info_copy["status"]["nearby_entities"]
        # 过滤item
        for nearby_entity in nearby_name_list:
            is_creature = True
            for key in nearby_entity.keys():
                if key in ["item"]:
                    is_creature = False
                    break
            if not is_creature:
                nearby_name_list.remove(nearby_entity)
        nearby_name_list_str = ""
        for i, nearby_entity in enumerate(nearby_name_list):
            if i != 0:
                nearby_name_list_str += ", "

            entity_name = None
            for key in nearby_entity.keys():
                # 如果对应的是一个长度为3的list，说明是名字
                if isinstance(nearby_entity[key], list) and len(nearby_entity[key]) == 3:
                    entity_name = key
                    break
            if entity_name is None:
                continue
            pos = nearby_entity[entity_name]
            pos_str = "["
            for j, coordinate in enumerate(pos):
                if j != 0:
                    pos_str += " ,"
                pos_str += str(coordinate)
            pos_str += "]"
            nearby_name_list_str += (entity_name + " at " + pos_str)
        if len(nearby_name_list) == 0:
            nearby_info = NOONE_NEARBY_INFO_FORMAT
        else:
            nearby_info = SOMEONE_NEARBY_INFO_FORMAT.format(name_list=nearby_name_list_str)

        nearby_blocks_info = info_copy["status"]["blocks"]

        holding_items = info_copy["status"]["I_held_item"]
        holding_items_str = ""
        for i, (item, num) in enumerate(holding_items.items()):
            if i != 0:
                holding_items_str += ", "
            holding_items_str += f"{item}*{num}"
        if holding_items_str == "":
            holding_items_str = "nothing"

        inventory = info_copy["status"]["inventory"]
        inventory_str = ""
        for i, item in enumerate(inventory):
            if i != 0:
                inventory_str += ", "
            item_name = list(item.keys())[0]
            num = item[item_name]
            inventory_str += f"{item_name}*{num}"
        if inventory_str == "":
            inventory_str = "nothing"

        content = AGENT_INFO_STORE_FORMAT.format(
            name=name,
            position=position,
            items=holding_items_str,
            inventory=inventory_str,
            nearby_info=nearby_info,
            blocks_info=nearby_blocks_info
        )

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "content": content,
            "name": name,
            "timestamp": timestamp
        }

    @staticmethod
    def _process_decompose(info: dict) -> dict:
        # process decompose
        info_copy = info.copy()
        sub_task = info_copy["task"]["description"]
        task = info_copy["task"]["parent_task_list"][0]  # TODO: Is 0 always correct?
        status = info_copy["task"]["status"]

        return {
            "sub_task": sub_task,
            "task": task,
            "status": status
        }

    @staticmethod
    def _load_json(json_path: str):
        if (not os.path.exists(json_path)) or os.path.getsize(json_path) == 0:
            return None
        else:
            with open(json_path, "r") as f:
                json_data = json.load(f)
            return json_data

    @staticmethod
    def _save_json(json_path: str, json_data):
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=4)

    @staticmethod
    def json2documents(json_path: str) -> list:
        """
        Convert a json file to documents in Chroma
        return a list of documents
        """
        if not os.path.exists(json_path):
            return []
        else:
            with open(json_path, "r") as f:
                json_list = json.load(f)
            documents = []
            for item in json_list:
                page_content = item["content"]
                del item["content"]
                metadata = item
                document = Document(
                    page_content=page_content,
                    metadata=metadata
                )
                documents.append(document)
            return documents

    def update_database_init(self, info: list):
        self._logger.debug("=" * 20 + " Update Database Init " + "=" * 20)
        self._logger.info(f"gathering info data: \n{info}")
        print(info)
        new_info = info.copy()
        for item in new_info:
            item["status"] = item["message"] if item["status"] else {}

        for item in new_info:
            env = self._process_env(item)
            agent = self._process_agent(item)

            # update agent
            for i, data in enumerate(self._agent_data):
                if data["name"] == agent["name"]:
                    self._agent_data.pop(i)
                    break
            self._agent_data.append(agent)
            self._logger.info(f"Update agent {agent['name']} successfully")

            # update env
            for i, data in enumerate(self._env_data["person_info"]):
                if data["name"] == env["person_info"]["name"]:
                    self._env_data["person_info"].pop(i)
                    break
            self._env_data["person_info"].append(env["person_info"])
            for block in env["blocks_info"]:
                if block not in self._env_data["blocks_info"]:
                    self._env_data["blocks_info"].append(block)
            self._env_data["sign_info"] = env["sign_info"]
            self._env_data["time"] = env["time"]
            self._env_data["nearby_entities"] = env["nearby_entities"]
            self._logger.info(f"Update env successfully")

        self._logger.info("Update database finished")

    def update_database(self, new_info: dict):
        self._logger.info("Start updating database...")
        new_info["status"] = new_info["status"]["message"] if new_info["status"]["status"] else {}

        history = self._process_history(new_info)
        env = self._process_env(new_info)
        agent = self._process_agent(new_info)
        # update agent
        for i, item in enumerate(self._agent_data):
            if item["name"] == agent["name"]:
                self._agent_data.pop(i)
                break
        self._agent_data.append(agent)
        self._logger.info(f"Update agent {agent['name']} successfully")

        # update env
        for i, item in enumerate(self._env_data["person_info"]):
            if item["name"] == env["person_info"]["name"]:
                self._env_data["person_info"].pop(i)
                break
        self._env_data["person_info"].append(env["person_info"])
        for block in env["blocks_info"]:
            if block not in self._env_data["blocks_info"]:
                self._env_data["blocks_info"].append(block)
        self._env_data["sign_info"] = env["sign_info"]
        self._env_data["time"] = env["time"]
        self._env_data["nearby_entities"] = env["nearby_entities"]
        self._logger.info(f"Update env successfully")

        # update history
        model = self.model
        # model = "gemini-pro"
        # model = "glm-4"
        self._logger.info(f"Summarizing history {history['name']}...")
        # self._logger.debug(f"Using {model}")

        if isinstance(self.llm, OpenAILanguageModel):
            if history["name"] not in self._history_data.keys():
                prompt = HISTORY_SUMMARY_PROMPT.format(name=history["name"],
                                                       summary_so_far="",
                                                       latest_development=history)
            else:
                prompt = HISTORY_SUMMARY_PROMPT.format(name=history["name"],
                                                       summary_so_far=self._history_data[history["name"]],
                                                       latest_development=history)
            model = "gpt-3.5-turbo-1106"
            response = self.llm.few_shot_generate_thoughts(system_prompt="You are a helpful assistant in Minecraft.",
                                                           example_prompt=prompt,
                                                           cache_enabled=False,
                                                           api_model=model,
                                                           max_tokens=512)
            
        else:
            if history["name"] not in self._history_data.keys():
                prompt = HISTORY_SUMMARY_PROMPT.format(name=history["name"],
                                                       summary_so_far="",
                                                       latest_development=history)
            else:
                prompt = HISTORY_SUMMARY_PROMPT.format(name=history["name"],
                                                       summary_so_far=self._history_data[history["name"]],
                                                       latest_development=history)
            response = self.llm.few_shot_generate_thoughts(system_prompt="You are a helpful assistant in Minecraft.",
                                                           example_prompt=prompt,
                                                           cache_enabled=False,
                                                           max_tokens=512)
        self._logger.debug(f"Update history: {response}")
        self._history_data[history["name"]] = response
        self._logger.info(f"Update history {history['name']} successfully")

        self._logger.info("Update database finished")

    @timed_cache(max_age=30)
    def query_env(self) -> (str, dict):
        person_info = self._env_data["person_info"]
        if len(person_info) == 0:
            person_info_str = "There is no agent in the environment."
        else:
            person_info_str = ""
            for i, person in enumerate(person_info):
                if i != 0:
                    person_info_str += ", "
                items_str = ""
                for j, (item, num) in enumerate(person["held_items"].items()):
                    if j != 0:
                        items_str += ", "
                    items_str += f"{item}"
                if items_str == "":
                    items_str = "nothing"
                person_info_str += PERSON_INFO_FORMAT.format(name=person["name"],
                                                             position=person["position"],
                                                             items=items_str)
        blocks_info_str = ""
        flag = []  # 用于去重
        for i, block_info in enumerate(self._env_data["blocks_info"]):
            for j, (key, value) in enumerate(block_info.items()):
                if key in flag:
                    continue
                else:
                    if key not in ["facing"]:
                        flag.append(key)
                        if i != 0:
                            blocks_info_str += ", "
                        blocks_info_str += f"{key}"
        if blocks_info_str == "":
            blocks_info_str = "nothing"

        sign_info_str = self._env_data["sign_info"]
        time_str = self._env_data["time"]

        return ENVIRONMENT_INFO_FORMAT.format(time=time_str,
                                              person_info=person_info_str,
                                              block_list=blocks_info_str,
                                              sign_info=sign_info_str), self._env_data
    
    @timed_cache(max_age=30)
    def query_env_with_task(self, task: str) -> str:
        # input task description
        # output task relevant env data
        self._logger.info(f"Start querying environment with task {task}...")
        # self._logger.debug(f"Using {model}")
        system_prompt = SUMMARY_ENVIRONMENT_SYSTEM_PROMPT
        example_prompt = SUMMARY_ENVIRONMENT_EXAMPLE_PROMPT.copy()
        example_prompt[-1] = example_prompt[-1].format(environment_info=self._env_data,
                                                       task=task + str(self._env_data["sign_info"]))
        self._logger.debug(f"System prompt: {system_prompt}")
        self._logger.debug(f"Example prompt: {example_prompt}")
        if isinstance(self.llm, OpenAILanguageModel):
            model = "gpt-3.5-turbo-1106"
            response = self.llm.few_shot_generate_thoughts(system_prompt=system_prompt,
                                                           example_prompt=example_prompt,
                                                           cache_enabled=False,
                                                           api_model=model,
                                                           max_tokens=256)
        else:
            response = self.llm.few_shot_generate_thoughts(system_prompt=system_prompt,
                                                           example_prompt=example_prompt,
                                                           cache_enabled=False,
                                                           max_tokens=256)
        # print(example_prompt)
        # print(response)
        self._logger.debug(f"Response: {response}")

        return response + "\nSign info: " + self._env_data["sign_info"]

    def query_task_list_experience(self, task_list: list[Task]) -> [str]:
        result_list = []
        for task in task_list:
            result_list.append(self.query_task_experience(task.description))

        return result_list

    def query_history(self, name: str) -> str:
        # summarization from history to current state
        if name not in self._history_data.keys():
            return "No history found."
        else:
            return self._history_data[name]
        
    def query_other_agent_state(self, agent_name: str) -> str:
        # query other agent state
        # self._history_data
        return [self._history_data[name] for name in self._history_data.keys() if name != agent_name]
    def query_agent(self, name) -> str:
        # used by controller
        for item in self._agent_data:
            if item["name"] == name:
                return item["content"]
        return "No agent found."

    def query_agent_list(self, name_list: list) -> [str]:
        # used by controller
        result_list = []
        for name in name_list:
            result_list.append(self.query_agent(name))

        return result_list

    def query_all_agent(self) -> [str]:
        # used by task manager
        result_list = []
        for item in self._agent_data:
            result_list.append(item["content"])

        return result_list

    def save(self):
        self._logger.info("Start saving...")
        with open(self._history_path, "w") as f:
            json.dump(self._history_data, f)
        with open(self._env_path, "w") as f:
            json.dump(self._env_data, f)
        with open(self._agent_path, "w") as f:
            json.dump(self._agent_data, f)
        self._logger.info("Save finished")
