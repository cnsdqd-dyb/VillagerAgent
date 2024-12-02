import sys
import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from model.init_model import init_language_model

sys.path.append(os.getcwd())
from type_define.graph import Task
from pipeline.task_manager import TaskManager
from pipeline.data_manager import DataManager
from pipeline.agent import BaseAgent
from pipeline.utils import *
from pipeline.controller_prompt import *
from env.env import VillagerBench
import logging


class GlobalController:
    '''
    Global Controller is the main controller of the system, it is responsible for assigning tasks to agents and monitoring the progress of the tasks.
    
    Args:
    - llm_config: dict, language model configuration
    - task_manager: TaskManager, task manager
    - data_manager: DataManager, data manager
    - env: VillagerBench, environment
    - silent: bool, whether to print logs
    - max_workers: int, the maximum number of threads to use
    
    '''
    def __init__(self, llm_config: dict, task_manager: TaskManager, data_manager: DataManager, env: VillagerBench,
                 silent: bool = False, max_workers=4):
        self.task_manager = task_manager

        tm_llm_config = llm_config.copy()
        tm_llm_config["role_name"] = "TaskManager"
        
        self.task_manager.llm = init_language_model(tm_llm_config)
        self.task_manager.dm = data_manager

        self.data_manager = data_manager

        dm_llm_config = llm_config.copy()
        dm_llm_config["role_name"] = "DataManager"

        self.data_manager.llm = init_language_model(dm_llm_config)

        llm = init_language_model(llm_config)
        self.agent_list = [BaseAgent(llm, env, data_manager, name=a.name, silent=False) for a in env.agent_pool]
        self.task_manager.agent_list = self.agent_list
        self.task_manager.agent_describe = env.get_all_agent_description_tiny()
        self.assignment = {}
        self.name_list = []
        self.collab_list = []
        for agent in self.agent_list:
            self.name_list.append(agent.name)
        self.feedback = {}

        self.logger = init_logger("GlobalController", logging.DEBUG, dump=True, silent=silent)
        self.llm = llm
        self.llm.role_name = "GlobalController"

        self.task_list = [Task]  # task published by tm
        self.query_interval = 1  # time interval between two query

        # init lock
        self.task_list_lock = threading.Lock()
        self.result_list_lock = threading.Lock()

        self.task_queue = []
        self.result_queue = []

        # init thread pool
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # adjust max_workers to control the number of threads

        # max task time for each task in seconds
        self.max_task_time = 60 * 30 # 30 minutes

        # task done signal
        self.one_task_done = True

        self.shutdown = False

    def validate_assignments(self, result: [dict]):
        validated_assignments = []

        for assign in result:
            task_id = assign["task_id"]
            agent_names = assign["agent"]
            if isinstance(agent_names, BaseAgent):
                agent_names = [agent_names.name]
            elif not isinstance(agent_names, list):
                agent_names = [agent_names]

            # Check if task exists
            if task_id >= len(self.task_list) or task_id < 0:
                self.logger.warning("Choose a non exist task!")
                continue

            task_instance = self.task_list[task_id]
            agent_instances = []

            # Check if agents exist and are valid for the task
            for agent_name in agent_names:
                agent = next((a for a in self.agent_list if a.name == agent_name), None)
                if agent is None:
                    self.logger.warning(f"Agent {agent_name} does not exist!")
                    continue

                if self.assignment.get(agent.name) is not None or agent_name not in task_instance.candidate_list:
                    self.logger.warning(f"Agent {agent_name} is not valid for the task!")
                    continue

                agent_instances.append(agent)

            if agent_instances:
                validated_assignments.append({
                    "task_instance": task_instance,
                    "agent_instances": agent_instances
                })

        return validated_assignments


    def execute_assignments(self, validated_assignments):
        for assignment in validated_assignments:
            task_instance = assignment["task_instance"]
            agent_instances = assignment["agent_instances"]
            result = ""
            if len(agent_instances) > 1:
                assign_name_list = []
                for agent in agent_instances:
                    assign_name_list.append(agent.name)
                agent_state = self.data_manager.query_agent_list(assign_name_list)
                result = self.generate_decompose_prompt_and_get_response(agent_state, assign_name_list, task_instance.description, task_instance.milestones)

                self.logger.debug("-"*10 + "decompose feedback in controller" + "-"*10)
                self.logger.debug("-"*40)
                for assign in result:
                    self.logger.debug("|" + assign["agent"] + ": " + assign["description"])
                self.logger.debug("-"*40)
                self.logger.debug("-"*15 + "decompose feedback end" + "-"*15)

                if len(result) != len(agent_instances):
                    self.logger.warning("decompose error!")
                    continue
            tmp_collab = {"task": task_instance.id, "assign agent": 0, "complete agent": 0}
            for agent in agent_instances:
                self.assignment[agent.name] = task_instance.id
                task_instance._agent.append(agent.name)
                # add task to agent's task list
                if len(agent_instances) > 1:
                    tmp_task = task_instance.copy()
                    for assign in result:
                        if assign["agent"] == agent.name:
                            tmp_task.description = assign["description"]
                            tmp_task.milestones = assign["milestones"]
                            tmp_task.status = Task.running
                            break
                    with self.task_list_lock:
                        self.task_queue.append((agent, tmp_task))
                        time.sleep(1)
                else:
                    with self.task_list_lock:
                        task_instance.status = Task.running
                        self.task_queue.append((agent, task_instance))
                        time.sleep(1)
                self.one_task_done = False
                tmp_collab["assign agent"] += 1
        
            name_list = ", ".join([agent.name for agent in agent_instances])
            self.logger.info(f"Agent(s) {name_list} are assigned to do task {task_instance.description}")
            
            self.collab_list.append(tmp_collab)
            task_instance.status = Task.running
    # 生产者
    def assign_tasks_to_agents(self, result: [dict]):
        # self.logger.info("Start to assign tasks!")
        validated_assignments = self.validate_assignments(result)
        self.execute_assignments(validated_assignments)

    def generate_prompt_and_get_response(self, env, experience, agent_state):
        controller_system_prompt = CONTROLLER_SYSTEM_PROMPT
        controller_user_prompt = format_string(CONTROLLER_USER_PROMPT, {
            "env": env[0],
            "experience": experience,
            "agent state": agent_state,
            "free agent": smart_truncate([agent.to_json() for agent in self.agent_list if self.assignment.get(agent.name) is None], 2048),
            "tasks": smart_truncate([task.assign_json(idx) for idx, task in enumerate(self.task_list) if task.available], 2048)
        })

        # self.logger.debug("-"*10 + "assign prompt in controller" + "-"*10)
        # print(controller_user_prompt)
        # self.logger.debug("-"*15 + "assign prompt end" + "-"*15)

        response = self.llm.few_shot_generate_thoughts(controller_system_prompt, controller_user_prompt, cache_enabled=True, json_check=True)
        # self.logger.debug("-"*10 + "response in controller" + "-"*10)
        # print(response)
        # self.logger.debug("-"*15 + "response end" + "-"*15)

        return extract_info(response)
    
    def generate_decompose_prompt_and_get_response(self, agent_state, name_list, task_description, task_milestones):
        controller_system_prompt = CONTROLLER_DECOMPOSE_SYSTEM_PROMPT
        controller_user_prompt = format_string(CONTROLLER_DECOMPOSE_USER_PROMPT, {
            "agent state": agent_state,
            "task description": task_description,
            "task milestones": task_milestones,
            "agent name": name_list
        })

        # self.logger.debug("-"*10 + "decompose prompt in controller" + "-"*10)
        # print(controller_user_prompt)
        # self.logger.debug("-"*15 + "decompose prompt end" + "-"*15)

        response = self.llm.few_shot_generate_thoughts(controller_system_prompt, controller_user_prompt, cache_enabled=True, json_check=True)
        self.logger.debug("-"*10 + "response in controller" + "-"*10)
        # print(response)
        self.logger.debug("-"*15 + "response end" + "-"*15)

        return extract_info(response)

    # worker
    def worker(self):
        while True:
            if self.shutdown:
                break
            with self.task_list_lock:
                if not self.task_queue:
                    time.sleep(self.query_interval)
                    continue
                while self.task_queue:
                    agent_task = self.task_queue.pop(0)
                    agent, task = agent_task

                    future = self.executor.submit(agent.step, task)
                    with self.result_list_lock:
                        self.result_queue.append((future, agent, task, time.time()))
                    time.sleep(self.query_interval)

    def set_task_status(self, task_id, status, feedback):
        for task in self.task_manager.graph.vertex:
            if task.id == task_id:
                if task.status == Task.success and status == Task.failure:
                    if status == Task.failure:
                        task.status = status
                else:
                    task.status = status

                if type(feedback) == dict and type(task.reflect) == None:
                    task.reflect = feedback
                elif type(feedback) == str and type(task.reflect) == None:
                    task.reflect = feedback
                elif type(feedback) == dict and type(task.reflect) == dict:
                    task.reflect = [task.reflect, feedback]
                elif type(feedback) == str and type(task.reflect) == str:
                    task.reflect = [task.reflect, feedback]
                elif type(task.reflect) == list:
                    task.reflect.append(feedback)
                else:
                    task.reflect = feedback
                break
    def get_task_by_id(self, task_id):
        for task in self.task_manager.graph.vertex:
            if task.id == task_id:
                return task
        return None
    
    def update_feedback(self, task, agent, detail):
        
        collab = next((c for c in self.collab_list if c["task"] == task.id), None)
        if collab == None:
            task.status = Task.success if tag else Task.failure
            self.set_task_status(task.id, task.status, detail)

            for agent in self.agent_list:
                if self.assignment.get(agent.name) == task.id:
                    self.assignment.pop(agent.name)

            self.logger.info(
                f"task {task.description} has been executed, the result is {task.status}")
            self.task_manager.feedback_task(self.get_task_by_id(task.id))
            self.one_task_done = True

            return
        else:
            collab["complete agent"] += 1
            tag = agent.reflect(task, detail)
            task.status = Task.success if tag else Task.failure
            self.set_task_status(task.id, Task.success if tag else Task.failure, task.reflect)

            if collab["complete agent"] == collab["assign agent"]:
                for agent in self.agent_list:
                    if self.assignment.get(agent.name) == task.id:
                        self.assignment.pop(agent.name)

                self.logger.info(
                    f"task {task.description} has been executed, the result is {task.status}")
                self.task_manager.feedback_task(self.get_task_by_id(task.id))
                self.one_task_done = True

                self.collab_list.remove(collab)

    def update_task_status(self, task, status, detail): 
        collab = next((c for c in self.collab_list if c["task"] == task.id), None)
        if collab == None:
            task.status = status
            self.set_task_status(task.id, status, detail)

            for agent in self.agent_list:
                if self.assignment.get(agent.name) == task.id:
                    self.assignment.pop(agent.name)

            self.logger.info(
                f"task {task.description} has been executed, the result is {task.status}")
            self.task_manager.feedback_task(self.get_task_by_id(task.id))
            self.one_task_done = True

            return
        
        else:
            collab["complete agent"] += 1
            task.status = status
            self.set_task_status(task.id, status, detail)

            if collab["complete agent"] == collab["assign agent"]:
                for agent in self.agent_list:
                    if self.assignment.get(agent.name) == task.id:
                        self.assignment.pop(agent.name)

                self.logger.info(
                    f"task {task.description} has been executed, the result is {task.status}")
                self.task_manager.feedback_task(self.get_task_by_id(task.id))
                self.one_task_done = True

                self.collab_list.remove(collab)

    # 消费者
    def process_completed_tasks(self):
        while True:
            if self.shutdown:
                break
            with self.result_list_lock:
                result_list_copy = []
                for future, agent, task, start_time in self.result_queue:
                    # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
                    if future.done():
                        try:
                            self.logger.info(f"Task {task.description} finished!")
                            _, detail = future.result()
                            self.update_feedback(task, agent, detail)

                        except Exception as e: # 没有对于 collab 的处理 这个代码不正确
                            traceback.print_exception(type(e), e, e.__traceback__)
                            self.logger.error(f"Task {task.description} failed with exception: {e}\n{e.__traceback__}")
                            self.logger.exception(e)
                            self.update_task_status(task, Task.failure, f"Task {task.description} failed with exception: {e}\n{e.__traceback__}")                            
                    
                    elif time.time() - start_time > self.max_task_time: # 没有对于 collab 的处理 这个代码不正确
                        self.logger.warning(f"Task {task.description} timeout!")
                        self.update_task_status(task, Task.failure, f"Task {task.description} timeout!")
                    
                    else:
                        result_list_copy.append((future, agent, task, start_time))
                    time.sleep(self.query_interval)
                self.result_queue = result_list_copy

                
    def check_task_list_available(self):
        available_task_list = []
        for task in self.task_list:
            task.available = True
            if len(task.candidate_list) == 0:
                task.candidate_list = self.name_list
            if len(task.predecessor_task_list) > 0 or task.status != Task.unknown:
                task.available = False
                continue
            free_candidate = 0
            for agent in self.agent_list:
                if agent.name in task.candidate_list and self.assignment.get(agent.name) is None:
                    free_candidate += 1
            if free_candidate < task.number:
                task.available = False
        
        for task in self.task_list:
            if task.available:
                available_task_list.append(task)
        
        return available_task_list

    def execute_tasks(self):
        try:
            while True:
                if self.shutdown:
                    break
                self.task_list = self.task_manager.query_subtask_list()
                if self.task_list == []:
                    self.logger.info("all assigned tasks are finished ...")
                    self.shutdown = True
                    break
                # write task list to file
                agent_states = []
                for agent in self.agent_list:
                    if self.assignment.get(agent.name) is None:
                        agent_states.append({"name": agent.name, "state": "free", "task": None})
                    else:
                        tmp_description = ""
                        for task in self.task_list:
                            if task.id == self.assignment.get(agent.name):
                                tmp_description = task.description
                                break
                        agent_states.append({"name": agent.name, "state": "busy", "task": tmp_description})

                with open("logs/task_list.json", "w") as f:
                    json.dump({
                        "agent_states": agent_states,
                        "task_list": [task.assign_json(idx) for idx, task in enumerate(self.task_list)],
                    }, f, indent=4)
                    
                if self.check_task_list_available() == []:
                    # self.logger.info("no available task ...")
                    # sleep
                    time.sleep(self.query_interval)
                    continue

                if self.one_task_done:
                    for task in self.task_list:
                        if task.number == len(task.candidate_list) and task.available and \
                            all([self.assignment.get(agent.name) is None for agent in self.agent_list if agent.name in task.candidate_list]):

                            self.logger.info(f"Task {task.description} is assigned to all agents!")
                            self.execute_assignments([{
                                "task_instance": task,
                                "agent_instances": [agent for agent in self.agent_list if agent.name in task.candidate_list]
                            }])

                    if self.check_task_list_available() != []:
                        env = self.data_manager.query_env()
                        agent_state = self.data_manager.query_agent_list(self.name_list)
                        experience = self.data_manager.query_task_list_experience(self.task_list)

                        result = self.generate_prompt_and_get_response(env, experience, agent_state)
                        self.assign_tasks_to_agents(result)
        except KeyboardInterrupt:
            self.shutdown = True
            self.task_manager = None
            self.data_manager = None
            self.executor.shutdown(wait=False)
            raise Exception("Interrupted by user")

    def run(self):
        try:
            # generate threads
            task_thread = threading.Thread(target=self.execute_tasks)
            worker_thread = threading.Thread(target=self.worker)
            result_thread = threading.Thread(target=self.process_completed_tasks)
            # start threads
            task_thread.start()
            worker_thread.start()
            result_thread.start()
            # wait for threads to finish
            task_thread.join()
            worker_thread.join()
            result_thread.join()
        except KeyboardInterrupt:
            # force to shutdown
            self.shutdown = True
            self.task_manager = None
            self.data_manager = None
            # shutdown thread pool
            self.executor.shutdown(wait=False)
            # raise exception
            raise Exception("Interrupted by user")