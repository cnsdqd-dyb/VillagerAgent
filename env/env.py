from env.minecraft_client import Agent
from contextlib import contextmanager
import traceback
import names
import subprocess
import json
import time
import os
from env.utils import init_logger
import logging


class env_type:
    construction = 0
    farming = 1
    puzzle = 2
    none = 3

    meta = 10

class VillagerBench:
    '''
    VillagerBench is the environment for the Minecraft task
    
    Args:
    - env_type: int, the type of the environment, 0 for construction, 1 for farming, 2 for puzzle, 3 for none (this is for pure agent environment, no judger will be launched)
    - task_id: int, the id of the task, different task_id means different task in the same scenario
    - dig_needed: bool, whether the agent need to dig the block
    - host: str, the host of the minecraft server
    - port: int, the port of the minecraft server default 25565
    - max_task_num: int, the max task number for the puzzle task
    - task_name: str, the name of the task
    - _virtual_debug: bool, whether the environment is in virtual debug mode
    '''
    def __init__(self, env_type, task_id: int, dig_needed: bool, host: str = "0.0.0.0", port: int = 25565, max_task_num: int = 1, task_name: str = "test", _virtual_debug: bool = False):
        self.env_type = env_type
        self.task_id = task_id
        self.host = host
        self.port = port
        self.task_name = task_name
        self.agent_pool = []
        self.log = {}
        self.reset_token()
        self.running = False
        self._virtual_debug = _virtual_debug
        self.logger = init_logger(name="Env", level=logging.DEBUG)
        self.max_task_num = max_task_num  # For puzzle
        self.dig_needed = dig_needed  # For construction
        self.launch_time = None
        self.langchain_model = ""
        self.base_port = 5000
        if not os.path.exists("data"):
            os.mkdir("data")

        if not os.path.exists("data/history"):
            os.mkdir("data/history")

        with open("data/score.json", "w") as f:
            json.dump({}, f, indent=4)
        
        with open("data/action_log.json", "w") as f:
            json.dump({}, f, indent=4)

        with open("data/llm_inference.json", "w") as f:
            json.dump({"time":0}, f, indent=4)

        with open(".cache/state.json", "w") as f:
            json.dump({"state": "idle"}, f)
        
        # 删除之前的log
        if os.path.exists("logs"):
            for file in os.listdir("logs"):
                file_path = os.path.join("logs", file)
                for _ in range(3):  # 尝试3次
                    try:
                        os.remove(file_path)
                        break  # 成功删除，跳出循环
                    except Exception as e:
                        print(f"删除失败：{e}")
                        time.sleep(1)  # 等待1秒再次尝试
                else:
                    print(f"无法删除文件 {file_path}，可能仍然被锁定。")
          
    @contextmanager
    def run(self, server_debug: bool = False, fast_api=False):
        try:
            if not self._virtual_debug:
                self.launch(debug=server_debug, fast_api=fast_api)
                self.logger.info(f"[env launched at {self.host}]")
            else:
                self.logger.info("[virtual debug mode, env not launched]")
            self.launch_time = time.time()
            yield
        except Exception as e:
            tb = traceback.format_exc()
            self.logger.error(f"Exception occurred: {e}\n{tb}")
            self.stop()
        finally:
            self.stop()
            if os.path.exists(".cache/state.json"):
                with open(".cache/state.json") as f:
                    state = json.load(f)
                state["state"] = "idle"
                with open(".cache/state.json", "w") as f:
                    json.dump(state, f)
            if os.path.exists(".cache/env.cache"):
                with open(".cache/env.cache", "w") as f:
                    json.dump([], f)

    def stop(self):
        if self.running:
            self.running = False
            Agent.kill()

    def virtual_env(name: str):
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
    
    def get_total_time(self):
        if self.launch_time is None:
            return 0
        return time.time() - self.launch_time
    
    def get_token_info(self):
        if os.path.exists("data/tokens.json"):
            with open("data/tokens.json") as f:
                token_info = json.load(f)
            return token_info
        else:
            return {"message": "token info not found", "status": False}
    
    def get_action_log(self):
        if os.path.exists("data/action_log.json"):
            with open("data/action_log.json") as f:
                action_log = json.load(f)
            return action_log
        else:
            return {"message": "action log not found", "status": False}
        
    def get_init_state(self) -> [dict]:
        assert self.running or self._virtual_debug, "env not running, please '.launch()' first"
        if self.running:
            return [self.agent_status(agent.name) for agent in self.agent_pool]
        else:
            return [VillagerBench.virtual_env(agent.name) for agent in self.agent_pool]

    def reset_token(self):
        tokens = {}
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        tokens["dates"] = current_time
        tokens["tokens_used"] = 0
        tokens["prompt_tokens"] = 0
        tokens["completion_tokens"] = 0
        tokens["successful_requests"] = 0
        tokens["total_cost"] = 0
        tokens["action_cost"] = 0
        with open("data/tokens.json", "w") as f:
            json.dump(tokens, f, indent=4)

    def get_all_agent_description(self) -> dict:
        agent_dict = {}
        for agent in self.agent_pool:
            tools = agent.tools
            tool_dict = {}
            for tool in tools:
                tool_dict[tool.name] = tool.description
            agent_dict[agent.name] = tool_dict
        return agent_dict


    def get_all_agent_description_tiny(self) -> dict:
        agent_dict = {}
        for agent in self.agent_pool:
            tools = agent.tools
            tool_list = []
            for tool in tools:
                tool_list.append(tool.name)
            agent_dict[agent.name] = tool_list
        
        # 分成共有和私有两部分，共有是所有agent tools的交集，私有是每个agent的独有tools
        public_tools = []
        private_tools = {}
        # 交集

        for agent in self.agent_pool:
            if len(public_tools) == 0:
                public_tools = agent_dict[agent.name]
            else:
                public_tools = list(set(public_tools).intersection(set(agent_dict[agent.name])))
        
        for agent in self.agent_pool:
            private_tools[agent.name] = list(set(agent_dict[agent.name]) - set(public_tools))
        

        return {"public_tools": public_tools, "private_tools": private_tools}
    

    def agent_describe(self, agent_name: str):
        for agent in self.agent_pool:
            if agent.name == agent_name:
                tools = agent.tools
                tool_dict = {}
                description = f"agent {agent_name} has tools:"
                for tool in tools:
                    tool_dict[tool.name] = tool.description
                    description += f" {tool.name}, {tool.description}\n"
                return tool_dict, description
        return {}, f"agent {agent_name} not found"

        

    def agent_status(self, agent_name: str):  # 返回一个dict
        for agent in self.agent_pool:
            if agent.name == agent_name:
                return Agent.get_environment_info_dict(agent_name)
        return {"message": f"agent {agent_name} not found", "status": False}

    def agent_register(self, agent_tool=[], agent_number: int = 1, name_list: [str] = []):
        '''
        register the agent to the environment
        '''
        if len(name_list) != agent_number:
            self.logger.warning(
                "[warning but dont worry] agent number not equal to names number, random names will be used")
            name_list = [names.get_first_name() for i in range(agent_number)]

        for i in range(agent_number):
            agent = Agent(name_list[i], tools=agent_tool, local_port=self.base_port + len(self.agent_pool), model=self.langchain_model)
            if len(agent_tool) != 0:
                agent.tool = agent_tool
            self.agent_pool.append(agent)
            self.log[agent.name] = []

    def launch(self, debug: bool = False, fast_api=False):
        Agent.launch(host=self.host, port=self.port, debug=debug, fast=fast_api)
        self.running = True
        self.reset()

    def reset(self):
        if self._virtual_debug:
            return
        self.logger.info("resetting...")
        if os.path.exists(".cache/load_status.cache"):
            with open(".cache/load_status.cache", "w") as f:
                json.dump({"status": "loading"}, f, indent=4)
        self.logger.info("waiting for server to start...")
        agent_names = [agent.name for agent in self.agent_pool]
        agent_names_str = ",".join(agent_names)
        if not self.running:
            assert False, "env not running, please '.launch()' first"
        
        elif self.env_type == env_type.construction:
            if self.dig_needed:
                subprocess.Popen(["python", "env/build_judger.py", "--idx", str(self.task_id), "--host", self.host, "--port" , str(self.port), "--agent_num", str(len(self.agent_pool)), "--dig_needed","true", "--agent_names", agent_names_str, "--task_name", self.task_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.logger.debug(f"python env/build_judger.py --idx {self.task_id} --host {self.host} --port {self.port} --dig_needed true --agent_num {len(self.agent_pool)} --agent_names {agent_names_str} --task_name {self.task_name}")
            else:
                subprocess.Popen(["python", "env/build_judger.py", "--idx", str(self.task_id), "--host", self.host, "--port" , str(self.port), "--agent_num", str(len(self.agent_pool)), "--agent_names", agent_names_str, "--task_name", self.task_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.logger.debug(f"python env/build_judger.py --idx {self.task_id} --host {self.host} --port {self.port} --agent_num {len(self.agent_pool)} --agent_names {agent_names_str} --task_name {self.task_name}")
        elif self.env_type == env_type.farming:
            subprocess.Popen(["python", "env/farm_craft_judger.py", "--idx", str(self.task_id), "--host", self.host, "--port" , str(self.port), "--agent_num", str(len(self.agent_pool)), "--agent_names", agent_names_str, "--task_name", self.task_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.debug(f"python env/farm_craft_judger.py --idx {self.task_id} --host {self.host} --port {self.port} --agent_num {len(self.agent_pool)} --agent_names {agent_names_str} --task_name {self.task_name}")
        elif self.env_type == env_type.puzzle:
            subprocess.Popen(["python", "env/escape_room_judger.py", "--idx", str(self.task_id), "--host", self.host, "--port" , str(self.port), "--max_task_num", str(self.max_task_num), "--agent_num", str(len(self.agent_pool)), "--agent_names", agent_names_str, "--task_name", self.task_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.debug(f"python env/escape_room_judger.py --idx {self.task_id} --host {self.host} --port {self.port} --max_task_num {self.max_task_num} --agent_num {len(self.agent_pool)} --agent_names {agent_names_str} --task_name {self.task_name}")
        elif self.env_type == env_type.meta:
            subprocess.Popen(["python", "env/meta_judger.py", "--idx", str(self.task_id), "--host", self.host, "--port" , str(self.port), "--agent_num", str(len(self.agent_pool)), "--agent_names", agent_names_str, "--task_name", self.task_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.debug(f"python env/meta_judger.py --idx {self.task_id} --host {self.host} --port {self.port} --agent_num {len(self.agent_pool)} --agent_names {agent_names_str} --task_name {self.task_name}")
        elif self.env_type == env_type.none:
            self.logger.info("no env type specified, only agent will be launched")
            return
        else:
            assert False, "env type not found"
        max_wait_num = 160
        while max_wait_num:
            time.sleep(1)
            try:
                if max_wait_num % 30 == 0 and max_wait_num != 120:
                    self.logger.info(f"waiting for server to start, guess the server is starting this task for the first time, please wait")
                if not os.path.exists(".cache/load_status.cache"):
                    continue
                with open(".cache/load_status.cache", "r") as f:
                    status_data = json.load(f)
                if status_data["status"] == "loaded":
                    self.logger.info("server started in background")
                    break
            except:
                raise Exception("server failed to start")
            max_wait_num -= 1
        if max_wait_num == 0:
            raise Exception("server failed to start")
    
    def get_msg(self, agent_name: str):
        '''
        get the message of the agent
        '''
        if self.running:
            return Agent.getMsg(agent_name)
        else:
            return {"message": "env not running", "status": False}
    
    def chat(self, from_agent: str, to_agent: str, message: str):
        '''
        chat with other agent
        '''
        if self.running:
            msg_instruction = f"/msg {to_agent} {message}"
            for agent in self.agent_pool:
                if agent.name == from_agent:
                    agent.run(msg_instruction)
                    return {"message": "success", "status": True}
            return {"message": "agent not found", "status": False}
        else:
            return {"message": "env not running", "status": False}

    def step(self, agent_name: str, action: str, max_turn: int = 2):
        '''
        final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}
        '''
        self.logger.debug("=" * 20 + " Env Step " + "=" * 20)
        self.logger.info(f"agent {agent_name}")
        self.logger.info("=" * 20 + " Env Step " + "=" * 20)
        find_agent = False
        for agent in self.agent_pool:
            if agent.name == agent_name:
                feedback, detail = agent.run(action, max_turn=max_turn)

                self.log[agent_name].append(detail)

                return feedback, detail

        if not find_agent:
            self.logger.warning(f"agent {agent_name} not found")
            return None, {"input": None, "action_list": None, "final_answer": None}

    def get_metadata(self):
        if self.env_type == env_type.construction:
            with open(f"data/map_description.json") as f:
                metadata = json.load(f)
            return metadata

    def get_score(self):
        if self.env_type == env_type.construction:
            with open(f"data/score.json") as f:
                score = json.load(f)
            return score
        if self.env_type == env_type.farming:
            with open(f"data/score.json") as f:
                score = json.load(f)
            return score
        if self.env_type == env_type.puzzle:
            with open(f"data/score.json") as f:
                score = json.load(f)
            return score


if __name__ == "__main__":

    try:

        env = VillagerBench(env_type.construction, 0)
        agent_tool = [Agent.place_item, Agent.open_container, Agent.dig_block, Agent.find_item]
        env.agent_register(agent_tool=agent_tool, agent_number=2)
        agent_tool = [Agent.place_item, Agent.open_container, Agent.dig_block, Agent.find_item]
        env.agent_register(agent_tool=agent_tool, agent_number=2)
        env.launch()

        feedback, detail = env.step(env.agent_pool[0].name, "open chest and get 1 dirt ")
        status = env.agent_status(env.agent_pool[0].name)

        env.get_score()

    finally:
        Agent.kill()
