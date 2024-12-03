### This is a simple example of how to run the pipeline.
### You can modify the code to fit your own environment and task.
### You can also refer to the doc/api_library.md to add more agent tools.

from env.env import VillagerBench, env_type, Agent
from pipeline.controller import GlobalController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
import json
if __name__ == "__main__":

    # Set Environment
    env = VillagerBench(env_type.none, task_id=0, _virtual_debug=False, dig_needed=False, host="10.214.180.148")

    # Set Agent
    api_key_list = json.load(open("API_KEY_LIST", "r"))["AGENT_KEY"] # use OPENAI as an example
    base_url = "https://api.chatanywhere.tech/v1"
    llm_config = {
        "api_model": "gpt-4-1106-preview", # for example, "gpt-4-1106-preview"
        "api_base": base_url, # for example, "https://api.openai.com/v1"
        "api_key_list": api_key_list
    }

    Agent.model = "gpt-4-1106-preview"
    Agent.base_url = base_url
    Agent.api_key_list = api_key_list

    # more agent tools can be added here you can refer to the agent_tool in doc/api_library.md
    agent_tool = [Agent.talkTo, Agent.read, Agent.scanNearbyEntities, Agent.equipItem, Agent.SmeltingCooking,
                      Agent.navigateTo, Agent.withdrawItem, Agent.craftBlock, Agent.waitForFeedback, Agent.UseItemOnEntity,
                      Agent.handoverBlock]

    # Register Agent
    env.agent_register(agent_tool=agent_tool, agent_number=1, name_list=["Alice"]) # Attention that the agent number should be consistent with the agent_tool
    # Attention you should use /op to give the agent the permission to use the command in minecraft server for example /op Agent1

    # Run Environment
    with env.run():
        
        # Set Data Manager
        dm = DataManager(silent=False)
        dm.update_database_init(env.get_init_state())

        # Set Task Manager
        tm = TaskManager(silent=False)

        # Set Controller
        ctrl = GlobalController(llm_config, tm, dm, env)

        # Set Task
        tm.init_task("Alice talk with yubo", {})

        # Run Controller
        ctrl.run()