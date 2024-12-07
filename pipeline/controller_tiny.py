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
    Global Controller for Minecraft game agents. The task is to assign tasks to agents. Create a plan that assigns tasks to suitable agents and return a list of task-assignment JSON objects.
    
    This is a tiny version of the GlobalController, which is used for faster task assignment and execution. It is designed for the purpose of testing and debugging.
    
    Args:
    - llm_config (dict): Configuration for the language model.
    - task_manager (TaskManager): TaskManager object.
    - data_manager (DataManager): DataManager object.
    - env (VillagerBench): VillagerBench object.
    - silent (bool): Whether to suppress the log output. Default is False.
    - max_workers (int): The maximum number of workers in the thread pool. Default is 4.
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
        self.assignment = {}
        self.feedback = {}

        self.logger = init_logger("GlobalController", level=logging.WARNING, dump=True, silent=silent)
        self.env = env
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
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # 可以根据需要调整max_workers的数量

        # init max task time
        self.max_task_time = 60 * 30 # 3min

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

            for agent in agent_instances:
                self.assignment[agent.name] = task_instance.id
                task_instance._agent.append(agent.name)

            with self.task_list_lock:
                task_instance.status = Task.running
                self.task_queue.append((agent_instances[0], task_instance))
                time.sleep(1)
        
            name_list = ", ".join([agent.name for agent in agent_instances])
            self.logger.info(f"Agent(s) {name_list} assigned to do task {task_instance.description}")

            # agent_env_dict = self.env.get_init_state()
            # for env_dict in agent_env_dict:
            #     self.logger.warning(str(env_dict))

            task_instance.status = Task.running

    # worker
    def worker(self):
        while True:
            if self.shutdown:
                break

            # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
            if self.env.agents_ping()["status"] == False:
                self.logger.info("Some agents are offline!")
                self.shutdown = True
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
        
        task.status = Task.success if agent.reflect(task, detail) else Task.failure
        self.set_task_status(task.id, task.status, detail)

        for agent in self.agent_list:
            if self.assignment.get(agent.name) == task.id:
                self.assignment.pop(agent.name)

        self.logger.info(
            f"task {task.description} has been executed, the result is {task.status}")
        self.task_manager.feedback_task(self.get_task_by_id(task.id))

        return

    def update_task_status(self, task, status, detail): 
        task.status = status
        self.set_task_status(task.id, status, detail)

        for agent in self.agent_list:
            if self.assignment.get(agent.name) == task.id:
                self.assignment.pop(agent.name)

        self.logger.info(
            f"task {task.description} has been executed, the result is {task.status}")
        self.task_manager.feedback_task(self.get_task_by_id(task.id))

        return
        

    def process_completed_tasks(self):
        while True:
            if self.shutdown:
                break

            # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
            if self.env.agents_ping()["status"] == False:
                self.logger.info("Some agents are offline!")
                self.shutdown = True
                break

            with self.result_list_lock:
                result_list_copy = []
                for future, agent, task, start_time in self.result_queue:

                    if self.shutdown:
                        break
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
                task.candidate_list = [agent.name for agent in self.agent_list]
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
    # 生产者
    def execute_tasks(self):
        try:
            while True:
                if self.shutdown:
                    break

                # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
                if self.env.agents_ping()["status"] == False:
                    self.logger.info("Some agents are offline!")
                    self.shutdown = True
                    break

                self.task_list = self.task_manager.query_subtask_list()
                if self.task_list == []:
                    self.logger.info("all assigned tasks are finished ...")
                    self.shutdown = True
                    break
                # 写到 logs/task_list.json 中
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

                if len(self.assignment) == 0:
                    # 如果 number == candidate_list 的长度，那么直接分配任务
                    for task in self.task_list:
                        if task.number == len(task.candidate_list) and task.available and \
                            all([self.assignment.get(agent.name) is None for agent in self.agent_list if agent.name in task.candidate_list]):

                            self.logger.info(f"Task {task.description} is assigned to all agents!")
                            self.execute_assignments([{
                                "task_instance": task,
                                "agent_instances": [agent for agent in self.agent_list if agent.name in task.candidate_list]
                            }])

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
            # shutdown
            self.shutdown = True
            self.task_manager = None
            self.data_manager = None

            self.executor.shutdown(wait=False)
            # raise exception
            raise Exception("Interrupted by user")