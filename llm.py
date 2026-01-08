import json

from tenacity import retry, stop_after_attempt, wait_exponential
import requests

import warnings

warnings.filterwarnings("ignore")

model = "ThinkFL"

DEFAULT_TOOL_PROMPT = (
    "You have access to the following tools:\n{tool_text}\n"
    "Use the following format if using a tool:\n"
    "```\n"
    "Action: tool name (one of [{tool_names}])\n"
    "Action Input: the input to the tool, in a JSON format representing the kwargs "
    """(e.g. ```{{"input": "hello world", "num_beams": 5}}```)\n"""
    "```\n"
)


def get_tool_names(tools):
    names = []
    for tool in tools:
        if "function" in tool:
            names.append(tool["function"]["name"])
        else:
            names.append(tool["name"])
    return names


def get_tool_from_content(content, tool_names):
    tools = []
    lines = content.split("\n")
    name = None
    for line in lines:
        if line.startswith("Action: "):
            name = line[len("Action: "):]
        elif line.startswith("✿FUNCTION✿: "):
            name = line[len("✿FUNCTION✿: "):]
        elif line.startswith("✿ARGS✿: "):
            arguments = line[len("✿ARGS✿: "):]
            if name in tool_names:
                tools.append({
                    "function": {
                        "name": name,
                        "arguments": arguments
                    }
                })
        elif line.startswith("Action Input: "):
            arguments = line[len("Action Input: "):]
            if name in tool_names:
                tools.append({
                    "function": {
                        "name": name,
                        "arguments": arguments
                    }
                })
    return tools


def chat_api(prompts, tools):
    llm_client = LLMClient(
        api_url="http://localhost:8000/v1/chat/completions",
        api_key="s"
        )
    prompts[-1]["content"] = prompts[-1]["content"] + "\n" + DEFAULT_TOOL_PROMPT.format(tool_text=json.dumps(tools),
                                                                                            tool_names=", ".join(
                                                                                                get_tool_names(tools)))
    response = llm_client.generate(prompts)
    return response


class LLMClient:
    """LLM调用客户端"""

    def __init__(self,
                 api_url="http://localhost:8000/v1/chat/completions",
                 api_key="s"
                 ):
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def generate(self, prompts: list):
        """调用LLM生成内容"""
        payload = {
            "model": model,
            "messages": prompts,
            "max_tokens": 8192,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                verify=False
            )
            response.raise_for_status()
        except Exception as e:
            print(e)
        return_message = response.json()['choices'][0]['message']
        return return_message['content']
