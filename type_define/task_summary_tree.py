import json


class TaskSummaryNode:
    def __init__(self, node_id):
        self.id = node_id
        self.parent_id = None
        self.children_id = []

        self.action = None  

        self.task = None  
        self.success = None  

    @classmethod
    def add_parent_and_child(cls, parent, child):
        parent.children_id.append(child.id)
        child.parent_id = parent.id


class TaskSummaryTree:
    def __init__(self):
        self.nodes = [TaskSummaryNode(0)]
        self.root_id = 0
        self.task_nodes_id = []

    def _find_child(self, node: TaskSummaryNode, action):
        for child_id in node.children_id:
            child = self.nodes[child_id]
            if child.action == action:
                return child
        return None

    def insert_action_list(self, action_list, task, success):
        cur_node = self.nodes[self.root_id]
        for action in action_list:
            child = self._find_child(cur_node, action)
            if child is None:
                child = TaskSummaryNode(len(self.nodes))
                child.action = action
                TaskSummaryNode.add_parent_and_child(cur_node, child)
                self.nodes.append(child)
            cur_node = child
        cur_node.task = task
        cur_node.success = success
        if cur_node.id not in self.task_nodes_id:
            self.task_nodes_id.append(cur_node.id)

    def get_action_list(self, task: str) -> (list[str], bool):
        for node_id in self.task_nodes_id:
            node = self.nodes[node_id]
            success = node.success
            if node.task == task:
                action_list = []
                cur_node = node
                while cur_node.parent_id is not None:
                    action_list.append(cur_node.action)
                    cur_node = self.nodes[cur_node.parent_id]
                action_list.reverse()
                return action_list, success
        return None, None

    def get_all_task(self):
        tasks = []
        for node_id in self.task_nodes_id:
            node = self.nodes[node_id]
            tasks.append(node.task)
        return tasks

    def to_json(self):
        nodes = []
        for node in self.nodes:
            nodes.append({
                'id': node.id,
                'parent_id': node.parent_id,
                'children_id': node.children_id,
                'action': node.action,
                'task': node.task,
                'success': node.success
            })
        data = {
            'nodes': nodes,
            'root_id': self.root_id,
            'task_nodes_id': self.task_nodes_id
        }
        return data

    def load_from_json(self, data):
        self.nodes = []
        for node in data['nodes']:
            new_node = TaskSummaryNode(node['id'])
            new_node.parent_id = node['parent_id']
            new_node.children_id = node['children_id']
            new_node.action = node['action']
            new_node.task = node['task']
            new_node.success = node['success']
            self.nodes.append(new_node)
        self.root_id = data['root_id']
        self.task_nodes_id = data['task_nodes_id']
