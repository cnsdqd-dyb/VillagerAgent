import sys
import os
import uuid
sys.path.append(os.getcwd())
import json
import networkx as nx
import matplotlib.pyplot as plt
import threading


class Task:
    success = "success"
    failure = "failure"
    unknown = "unknown"
    running = "running"

    def __init__(self, name: str, content: dict):
        self.id = str(uuid.uuid4())
        self.content = content  # Task related content (e.g. task detail, task data, etc.)
        self.parent_task_list = []  # upper level task
        self.predecessor_task_list = []  # previous task
        self.description = name # 
        self.goal = None # deprecated
        self.criticism = None # deprecated
        self.milestones = []
        self.status = Task.unknown
        self.candidate_list = []
        self.number = 1
        self.available = True
        self.reflect = None

        self._pre_idxs = [] # only used by task manager
        self._agent = [] # only used by task manager and agent
        self._summary = ["running"] # only used by task manager
        self._direct_pre_task_list = [] # only used by global controller
    
    def copy(self):
        new_task = Task(self.description, self.content)
        new_task.parent_task_list = self.parent_task_list
        new_task.predecessor_task_list = self.predecessor_task_list
        new_task.goal = self.goal
        new_task.criticism = self.criticism
        new_task.milestones = self.milestones
        new_task.status = self.status
        new_task.candidate_list = self.candidate_list
        new_task.number = self.number
        new_task.available = self.available
        new_task.reflect = self.reflect
        return new_task

    def to_json(self) -> dict:
        return {
            # "id": self.id,
            # "meta-data": self.content,
            "parent_task_list": [task.description for task in self.parent_task_list],
            "predecessor_task_list": [task.description for task in self.predecessor_task_list],
            "description": self.description,
            # "goal": self.goal,
            # "criticism": self.criticism,
            "number": self.number,
            "candidate list": self.candidate_list,
            "reflect": self.reflect,
            "milestones": self.milestones,
            "status": self.status,
        }

    def analyze_json(self) -> dict:
        return {
            "task-description": self.description,
            "task-feedback": self.reflect,
            "meta-data": self.content,
        }

    def decompose_json(self) -> dict:
        return {
            "task-description": self.description,
            "task-goal": self.goal,
            # "milestones": self.milestones,
            "parent_task_list": [task.description for task in self.parent_task_list],
            "meta-data": self.content["document"] if type(self.content) == dict and "document" in self.content.keys() else self.content,
        }

    def assign_json(self, task_id) -> dict:
        return {
            "id": task_id,
            "status": self.status,
            # "meta-data": self.content,
            "direct predecessor": [task.description for task in self._direct_pre_task_list],
            "description": self.description,
            # "goal": self.goal, # deprecated
            # "criticism": self.criticism, # deprecated
            # "milestones": self.milestones,
            "number": self.number,
            "candidate list": self.candidate_list,
            "available": self.available
        }


class Graph:
    def __init__(self):
        self.vertex = []
        self.edge = []
        self.G = nx.DiGraph()

        self._json_count = 0

    def add_node(self, node: Task):
        if node not in self.vertex:
            self.vertex.append(node)

    def add_edge(self, start_node: Task, end_node: Task):
        if (start_node, end_node) not in self.edge:
            self.edge.append((start_node, end_node))

    def get_node_from(self, node: Task):
        return [edge[1] for edge in self.edge if edge[0] == node]

    def get_node_to(self, node: Task):
        return [edge[0] for edge in self.edge if edge[1] == node]

    def get_entry_node(self):
        return [node for node in self.vertex if len(self.get_node_to(node)) == 0]

    def get_exit_node(self):
        return [node for node in self.vertex if len(self.get_node_from(node)) == 0]

    def delete_node(self, node: Task):
        self.vertex.remove(node)
        self.edge = [edge for edge in self.edge if edge[0] != node and edge[1] != node]

    def remove_node_merge_edge(self, node: Task):
        predecessor_list = self.get_node_to(node)
        successor_list = self.get_node_from(node)
        for predecessor in predecessor_list:
            for successor in successor_list:
                self.add_edge(predecessor, successor)
        self.delete_node(node)

    def insert_node_merge_edge(self, node: Task, predecessor: Task):
        # predecessor -> node -> successor / predecessor -> successor
        # insert node between predecessor and all successor
        successor_list = self.get_node_from(predecessor)
        # add parent list
        node.parent_task_list = predecessor.parent_task_list
        for successor in successor_list:
            self.add_edge(node, successor)
        self.add_edge(predecessor, node)
        self.add_node(node)

    def delete_edge(self, start_node: Task, end_node: Task):
        self.edge.remove((start_node, end_node))

    def merge_at(self, sub_graph, node: Task):
        predecessor_list = self.get_node_to(node)
        successor_list = self.get_node_from(node)

        sub_graph_entry_list = sub_graph.get_entry_node()
        sub_graph_exit_list = sub_graph.get_exit_node()

        for predecessor in predecessor_list:
            for sub_graph_entry in sub_graph_entry_list:
                self.add_edge(predecessor, sub_graph_entry)

        for edge in sub_graph.edge:
            self.add_edge(edge[0], edge[1])

        for successor in successor_list:
            for sub_graph_exit in sub_graph_exit_list:
                self.add_edge(sub_graph_exit, successor)

        for sub_node in sub_graph.vertex:
            self.add_node(sub_node)

        self.delete_node(node)

    def replace_node(self, old_node: Task, new_node: Task):
        new_node.parent_task_list = old_node.parent_task_list
        predecessor_list = self.get_node_to(old_node)
        successor_list = self.get_node_from(old_node)
        for predecessor in predecessor_list:
            self.add_edge(predecessor, new_node)
        for successor in successor_list:
            self.add_edge(new_node, successor)
        self.delete_node(old_node)
        self.add_node(new_node)

    def get_all_predecessor(self, node: Task):
        predecessor_list = []
        for predecessor in self.get_node_to(node):
            predecessor_list.append(predecessor)
            predecessor_list += self.get_all_predecessor(predecessor)
        return predecessor_list

    def get_all_successor(self, node: Task):
        successor_list = []
        for successor in self.get_node_from(node):
            successor_list.append(successor)
            successor_list += self.get_all_successor(successor)
        return successor_list

    def get_all_node(self):
        return self.vertex

    def get_open_node(self):
        return [node for node in self.vertex if node.status == Task.unknown or node.status == Task.running]

    def get_closed_node(self):
        return [node for node in self.vertex if node.status == Task.success]

    def get_failed_node(self):
        return [node for node in self.vertex if node.status == Task.failure]

    def get_open_task_list(self):
        open_task_list = self.get_open_node()
        for node in open_task_list:
            predecessor = self.get_all_predecessor(node)
            _direct_pre_task_list = []
            for task in predecessor:
                if (task.status == Task.unknown or task.status == Task.running) and task in open_task_list:
                    node.predecessor_task_list.append(task)
                    _direct_pre_task_list.append(task)
            node._direct_pre_task_list =_direct_pre_task_list

            for p_n in set(node.predecessor_task_list):
                if (p_n.status == Task.unknown or p_n.status == Task.running) and p_n in open_task_list:
                    node.predecessor_task_list.append(p_n)
            predecessor_task_list = []
            for task in node.predecessor_task_list:
                if task.status == Task.unknown or task.status == Task.running:
                    predecessor_task_list.append(task)
            node.predecessor_task_list = list(set(predecessor_task_list))
        return open_task_list
    
    def check_graph_completion(self):
        all_nodes = self.get_all_node()  # get all nodes
        running_nodes = [node for node in all_nodes if node.status == Task.running]
        if not running_nodes:  # there is no running node
            for node in all_nodes:
                if node.status == Task.unknown:  # there is a node that has not been executed
                    predecessors = self.get_all_predecessor(node)
                    if not predecessors or all(pred.status == Task.success for pred in predecessors):
                        # all unexecuted nodes have completed predecessors
                        return False  # the graph is not completed
            # all unexecuted nodes have completed predecessors
            return True
        return False # there is a running node

    def to_json(self) -> dict:
        return {
            "vertex": [node.to_json() for node in self.vertex],
            "edge": [(edge[0].description, edge[1].description) for edge in self.edge]
        }

    def graph_flow(self) -> dict:
        return {
            "entry_node": [node.description for node in self.get_entry_node()],
            "exit_node": [node.description for node in self.get_exit_node()],
            "node_list": [node.description for node in self.vertex],
            "edge_list": [(edge[0].description, edge[1].description) for edge in self.edge]
        }

    def graph_flow_json(self) -> dict:
        return {
            "entry_node": [node.to_json() for node in self.get_entry_node()],
            "exit_node": [node.to_json() for node in self.get_exit_node()],
            "node_list": [node.to_json() for node in self.vertex],
            "edge_list": [(edge[0].to_json(), edge[1].to_json()) for edge in self.edge]
        }
    
    def get_graph_status(self) -> str:
        # traverse from the entry node, write a description for each node, and write the current running status
        open_node_list = self.get_entry_node()
        close_node_list = []
        description = ""

        while len(open_node_list) != 0:
            node = open_node_list.pop(0)
            close_node_list.append(node)
            if node.status == Task.running:
                description += f"{node.description} is running\n"
            elif node.status == Task.success:
                description += f"{node.description} is finished\n"
            elif node.status == Task.failure:
                description += f"{node.description} is failed\n"
            else:
                description += f"{node.description} is waiting to be executed\n"

            for successor in self.get_node_from(node):
                successor_predecessor_list = self.get_node_to(successor)
                if all(predecessor in close_node_list for predecessor in successor_predecessor_list):
                    if successor not in open_node_list and successor not in close_node_list:
                        open_node_list.append(successor)

        return description
    

    def get_graph_status_with_id(self) -> str:
        # traverse from the entry node, write a description for each node, and write the current running status
        open_node_list = self.get_entry_node()
        close_node_list = []
        description = ""
        idx = 1
        while len(open_node_list) != 0:
            node = open_node_list.pop(0)
            close_node_list.append(node)
            if node.status == Task.unknown or node.status == Task.running:
                description += f"id {idx} {node.description} is running\n"
            elif node.status == Task.success:
                description += f"id {idx} {node.description} is finished\n"
            elif node.status == Task.failure:
                description += f"id {idx} {node.description} is failed\n"
            else:
                assert False, f"id {idx} {node.description} is waiting to be executed\n"
            idx += 1

            for successor in self.get_node_from(node):
                successor_predecessor_list = self.get_node_to(successor)
                if all(predecessor in close_node_list for predecessor in successor_predecessor_list):
                    if successor not in open_node_list and successor not in close_node_list:
                        open_node_list.append(successor)
                        
        return description

    def get_graph_list(self) -> [Task]:
        node_list = []
        open_node_list = self.get_entry_node()
        close_node_list = []

        while len(open_node_list) != 0:
            node = open_node_list.pop(0)
            close_node_list.append(node)
            
            node_list.append(node)
            for successor in self.get_node_from(node):
                successor_predecessor_list = self.get_node_to(successor)
                if all(predecessor in close_node_list for predecessor in successor_predecessor_list):
                    if successor not in open_node_list and successor not in close_node_list:
                        open_node_list.append(successor)
                        
        return node_list


    def __str__(self):
        return str(self.graph_flow())
    
    def draw_graph(self, path):
        self.G.clear()
        for node in self.vertex:
            self.G.add_node(node.description, description=node.description)
        for edge in self.edge:
            self.G.add_edge(edge[0].description, edge[1].description)
        pos = nx.spring_layout(self.G)
        nx.draw(self.G, pos, with_labels=True)
        node_labels = nx.get_node_attributes(self.G, 'description')
        nx.draw_networkx_labels(self.G, pos, labels=node_labels)
        plt.savefig(path)  # Save as png image
        plt.close()

    def _write_graph_to_md(self, path):
        with open(path, 'w') as f:
            f.write('```mermaid\n')
            f.write('graph TD\n')
            for node in self.vertex:
                f.write(f'    {node.id}["{node.description} task-status: {node.status}"]\n')
            for edge in self.edge:
                f.write(f'    {edge[0].id} --> {edge[1].id}\n')
            f.write('```\n')

    def write_graph_to_md(self, path):
        thread = threading.Thread(target=self._write_graph_to_md, args=(path,))
        thread.start()

    def write_graph_to_json(self, path):
        path = path + "graph_" + str(self._json_count) + ".json"
        self._json_count += 1
        with open(path, 'w') as f:
            json_vertex = [node.to_json() for node in self.vertex]
            json_edge = [(edge[0].description, edge[1].description) for edge in self.edge]
            json.dump({"vertex": json_vertex, "edge": json_edge}, f, indent=4)

    def get_co_parent_list(node1:Task, node2:Task) -> [Task]:
        parent_list1 = node1.parent_task_list
        parent_list2 = node2.parent_task_list
        co_parent_list = []
        if len(parent_list1) == 0 or len(parent_list2) == 0:
            assert False, f"node {node1.description} or node {node2.description} has no parent"
        if len(parent_list1) > len(parent_list2):
            parent_list1, parent_list2 = parent_list2, parent_list1
        for parent in parent_list1:
            if parent in parent_list2:
                co_parent_list.append(parent)
        return co_parent_list

    def get_exist_sub_graph(self, task:Task):
        # get the sub graph that contains the task
        sub_graph = Graph()
        sub_node_list = []
        for node in self.vertex:
            if task in node.parent_task_list:
                sub_node_list.append(node)
        for node in sub_node_list:
            sub_graph.add_node(node)
        for node in sub_node_list:
            for successor in self.get_node_from(node):
                if successor in sub_node_list:
                    sub_graph.add_edge(node, successor)
        return sub_graph



if __name__ == "__main__":
    # TEST
    graph = Graph()
    node1 = Task("node1", {"name": "node1"})
    node2 = Task("node2", {"name": "node2"})
    node3 = Task("node3", {"name": "node3"})
    node4 = Task("node4", {"name": "node4"})
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)
    graph.add_node(node4)
    graph.add_edge(node1, node2)
    graph.add_edge(node1, node3)
    graph.add_edge(node1, node4)
    graph.write_graph_to_md("img/graph.md")

    graph.remove_node_merge_edge(node1)
    graph.write_graph_to_md("img/remove_graph.md")
