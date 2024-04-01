from enum import Enum

from type_define import Graph, Task


class DecomposeSummaryNode:
    def __init__(self):
        self.task = None
        self.decompose_plans = []
        self.status = []


class DecomposeSummarySystem:
    class OperationStatus(Enum):
        success = 0
        cannot_find_task = 1
        cannot_find_sub_task = 2

    def __init__(self):
        self.task_list = []

    @staticmethod
    def _check_all_sub_task_finished(graph: Graph):
        for node in graph.vertex:
            if node.status != Task.success:
                return False
        return True

    def insert_task_decompose(self, task: str, decompose_plan: Graph):
        for node in self.task_list:
            if node.task == task:
                
                for i, status in enumerate(node.status):
                    if not status:
                        node.decompose_plans.pop(i)
                        node.status.pop(i)
                node.decompose_plans.append(decompose_plan)
                node.status.append(False)
                if self._check_all_sub_task_finished(decompose_plan):
                    node.status[-1] = True

        node = DecomposeSummaryNode()
        node.task = task
        node.decompose_plans.append(decompose_plan)
        node.status = [False]
        if self._check_all_sub_task_finished(decompose_plan):
            node.status[-1] = True
        self.task_list.append(node)

    def update_decompose_plan_status(self, task: str, sub_task: str, status):
        for i, node in enumerate(self.task_list):
            if node.task == task:
                for decompose_plan in node.decompose_plans:
                    
                    nodes_in_graph = decompose_plan.vertex
                    for node_in_graph in nodes_in_graph:
                        if node_in_graph.description == sub_task:
                            node_in_graph.status = status

                            if self._check_all_sub_task_finished(decompose_plan):
                                node.status[i] = True
                            return DecomposeSummarySystem.OperationStatus.success

                return DecomposeSummarySystem.OperationStatus.cannot_find_sub_task

        return DecomposeSummarySystem.OperationStatus.cannot_find_task

    def query_task_decompose(self, task: str):
        for node in self.task_list:
            if node.task == task:
                return node
        return None

