from langchain.embeddings.openai import OpenAIEmbeddings
import numpy as np
import time
from typing import List, Dict, Tuple, Union
import sys
import os
import json
sys.path.append(os.getcwd())
import difflib
from pipeline.utils import document2string
from concurrent.futures import ThreadPoolExecutor
os.environ["OPENAI_API_KEY"] = json.load(open("API_KEY_LIST", "r"))["AGENT_KEY"][0]
# os.environ["OPENAI_API_KEY"] = json.load(open("/home/yubo/VillagerAgent-Minecraft-multiagent-framework/API_KEY_LIST", "r"))["AGENT_KEY"][0]
os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
class Retriever:
    '''
    This class is the retriever for the pipeline, it is used to retrieve the most similar data from the given data.
    '''
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    def __init__(self):
        self.embedding_map = {}

    def string_similar(self, s1, s2):
        return difflib.SequenceMatcher(None, s1, s2).quick_ratio()
    
    def parallel_vector(self, query:Union[str, List[str]], data:Dict):
        if isinstance(query, str):
            emb_need = self.get_flatten_emb(query, data)
            emb_need += self.get_key_value_emb(query, data)

        elif isinstance(query, list):
            emb_need = []
            for q in query:
                emb_need += self.get_flatten_emb(q, data)
                emb_need += self.get_key_value_emb(q, data)
        embeddings = self.embeddings

        def process_emb(emb):
            if emb not in self.embedding_map:
                self.embedding_map[emb] = embeddings.embed_query(emb)

        with ThreadPoolExecutor() as executor:
            executor.map(process_emb, emb_need)

    
    def similarity_get(self, text1, text2, embedding1=None, embedding2=None):
        embeddings = self.embeddings
        # print(f"Query: {text1}", f"Document: {text2}", sep="\n")
        start_time = time.time()
        if embedding1 is None:
            embedding1 = embeddings.embed_query(text1)
        if embedding2 is None:
            embedding2 = embeddings.embed_query(text2)
        similarity_score = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

        string_similarity = self.string_similar(text1, text2)

        score = similarity_score * 0.8 + string_similarity * 0.2
        # print(f"Similarity score: {similarity_score}")
        # print(f"String similarity score: {string_similarity}")
        # print(f"Final score: {score}")
        # print(f"Time taken: {time.time() - start_time}")
        return score
    
    def get_flatten_emb(self, query, data):
        emb_need = []
        data_dict = self.flatten_json(data)
        for key, value in data_dict.items():
            data = value[1]
            value = str(value[0])
            if key in emb_need:
                pass
            else:
                emb_need.append(key)

            if value in emb_need:
                pass
            else:
                emb_need.append(value)

            if query in emb_need:
                pass
            else:
                emb_need.append(query)

        return emb_need
    
    def get_key_value_emb(self, query, data):
        emb_need = []
        def search(x):
            if isinstance(x, dict):
                for key, value in x.items():
                    if key in emb_need:
                        pass
                    else:
                        emb_need.append(key)
                    value_str = document2string(value,MAX_LENGTH=600)
                    if value_str in emb_need:
                        pass
                    else:
                        emb_need.append(value_str)

                    if query in emb_need:
                        pass
                    else:
                        emb_need.append(query)

                    if isinstance(value, (dict, list)):
                        search(value)
            elif isinstance(x, list):
                for item in x:
                    if isinstance(item, (dict, list)):
                        search(item)

        search(data)
        return emb_need

    def find_most_similar_key(self, query, data, threshold, max_results):
        results = []
        embedding_map = self.embedding_map
        embeddings = self.embeddings
        def search(x):
            if isinstance(x, dict):
                for key, value in x.items():
                    if key in embedding_map:
                        embedding_key = embedding_map[key]
                    else:
                        embedding_map[key] = embeddings.embed_query(key)
                        embedding_key = embedding_map[key]
                    value_str = document2string(value,MAX_LENGTH=600)
                    if value_str in embedding_map:
                        embedding_value = embedding_map[value_str]
                    else:
                        embedding_map[value_str] = embeddings.embed_query(value_str)
                        embedding_value = embedding_map[value_str]

                    if query in embedding_map:
                        embedding_query = embedding_map[query]
                    else:
                        embedding_map[query] = embeddings.embed_query(query)
                        embedding_query = embedding_map[query]

                    similarity_key = self.similarity_get(query, key, embedding_query, embedding_key)
                    similarity_value = self.similarity_get(query, value_str, embedding_query, embedding_value)
                    if similarity_key > threshold or similarity_value > threshold:
                        results.append((max(similarity_key, similarity_value), key, value))
                    if isinstance(value, (dict, list)):
                        search(value)
            elif isinstance(x, list):
                for item in x:
                    if isinstance(item, (dict, list)):
                        search(item)

        search(data)
        results.sort(reverse=True, key=lambda x: x[0])
        return results[:max_results]

    def flatten_json(self, y, threshold=800):
        # 这个函数是将任意的json文件转换为一维的dict 方便进行retreival search
        out = {}

        def flatten(x, name='', data=[]):
            if type(x) is dict:
                if len(str(x)) < threshold:
                    out[name[:-1]] = [x, data]
                else:
                    for a in x:
                        flatten(x[a], name + a + '_', x)
            elif type(x) is list:
                if len(str(x)) < threshold:
                    out[name[:-1]] = str(x)
                else:
                    i = 0
                    for a in x:
                        flatten(a, name + str(i) + '_', x)
                        i += 1
            else:
                out[name[:-1]] = [x, data]

        flatten(y, data=y)
        return out

    def flatten_search(self, query, data, threshold, max_results):
        embeddings = self.embeddings
        embedding_map = self.embedding_map
        data_dict = self.flatten_json(data)
        results = []
        for key, value in data_dict.items():
            data = value[1]
            value = str(value[0])
            if key in embedding_map:
                embedding_key = embedding_map[key]
            else:
                embedding_map[key] = embeddings.embed_query(key)
                embedding_key = embedding_map[key]

            if value in embedding_map:
                embedding_value = embedding_map[value]
            else:
                embedding_map[value] = embeddings.embed_query(value)
                embedding_value = embedding_map[value]

            if query in embedding_map:
                embedding_query = embedding_map[query]
            else:
                embedding_map[query] = embeddings.embed_query(query)
                embedding_query = embedding_map[query]

            similarity_key = self.similarity_get(query, key, embedding_query, embedding_key)
            similarity_value = self.similarity_get(query, value, embedding_query, embedding_value)
            if similarity_key > threshold:
                results.append((max(similarity_key, similarity_value), key, document2string(data)))
            elif similarity_value > threshold:
                results.append((max(similarity_key, similarity_value), value, document2string(data)))
            

        results.sort(reverse=True, key=lambda x: x[0])
        return results[:max_results]
    
    def post_process(self, data) -> str:
        data_str = str(data)
        data_str = data_str.replace("{","")
        data_str = data_str.replace("}","")
        data_str = data_str.replace("[","")
        data_str = data_str.replace("]","")
        data_str = data_str.replace("(","")
        data_str = data_str.replace(")","")
        data_str = data_str.replace("'","")
        # print(len(data_str))
        return data_str
    
    def search(self, query:Union[str, List[str]], data:Dict, threshold:float, max_results:int, length_threshold=2048):

        if len(self.post_process(data)) < length_threshold:
            # print("less")
            return data
        
        self.parallel_vector(query, data)

        if isinstance(query, str):
            result1 = self.find_most_similar_key(query, data, threshold, max_results)
            result2 = self.flatten_search(query, data, threshold, max_results)
            result = result1 + result2

        elif isinstance(query, list):
            result = []
            for q in query:
                result += self.search(q, data, threshold, max_results)
            return result

        result.sort(reverse=True, key=lambda x: x[0])
        result = result[:max_results]
        new_result = []
        result.sort(reverse=True, key=lambda x: len(str(x[2])))
        for r in result:
            if str(r[2]) not in str(new_result):
                new_result.append(r)
        new_result.sort(reverse=True, key=lambda x: x[0])
        return new_result
    
if __name__ == "__main__":
    retriever = Retriever()
    test_data = {
        "name": "Sam",
        "age": 18,
        "hobbies": ["basketball", "football", "swimming"],
        "address": {
            "country": "China",
            "province": "Shanghai",
            "city": "Shanghai"
        },
        "friends": [
            {
                "name": "Amy",
                "age": 18,
                "hobbies": ["pingpong", "football", "swimming"],
                "address": {
                    "country": "China",
                    "province": "Shanghai",
                    "city": "Shanghai"
                }
            },
            {
                "name": "Bob",
                "age": 18,
                "hobbies": ["pingpong", "football", "swimming"],
                "address": {
                    "country": "China",
                    "province": "Shanghai",
                    "city": "Shanghai"
                }
            }
        ]
    }
    query = "who like play pingpong"
    print(retriever.search(query, test_data, 0.5, 10))