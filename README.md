<div align="center">
<h1>ThinkFL: Self-Refining Failure Localization for Microservice Systems via Reinforcement Fine-Tuning</h1>
</div>

<p align="center">
  📘 <a href="https://github.com/LLM4AIOps/OpenRLHF-ThinkFL">Training Code</a >
  &nbsp;•&nbsp;
  📄 <a href="https://arxiv.org/abs/2504.18776">Paper</a >
</p >

# ThinkFL Model Family

| Model | Link |
|-------|------|
| ThinkFL-Llama3.2-3B | [🤗 Hugging Face](https://huggingface.co/Zhang-Lingzhe/ThinkFL-Llama3.2-3B) |
| ThinkFL-Llama3-8B | [🤗 Hugging Face](https://huggingface.co/Zhang-Lingzhe/ThinkFL-Llama3-8B) |
| ThinkFL-Qwen2.5-0.5B | [🤗 Hugging Face](https://huggingface.co/Zhang-Lingzhe/ThinkFL-Qwen2.5-0.5B) |
| ThinkFL-Qwen2.5-3B | [🤗 Hugging Face](https://huggingface.co/Zhang-Lingzhe/ThinkFL-Qwen2.5-3B) |

## ThinkFL Overview

ThinkFL is a lightweight, self-refining failure localization model for microservice systems that overcomes the limitations of rigid invocation workflows and resource-intensive inference in existing LLM-based approaches. Built on a sub-10B-parameter LLM and trained via a Progressive Multi-Stage Group Relative Policy Optimization (GRPO) fine-tuning strategy, ThinkFL features a Recursion-of-Thought Actor capable of autonomously exploring multi-step diagnostic paths through standardized tool invocation—integrating trace analysis and metrics evaluation to produce interpretable, ranked root cause hypotheses. These outputs are refined using expert SRE feedback and a Multi-Factor Failure Localization Grader, enabling efficient, accurate, and cost-effective failure localization even in high-frequency incident environments.

## Quickstart

ThinkFL can be directly launched using vLLM.

### Deployment with vLLM

For production deployment, you can use vLLM to serve ThinkFL as an OpenAI-compatible API endpoint. Please refer to the vLLM PR for implementation details.

```bash
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
  --model ThinkFL-Llama3.2-3B \
  --served-model-name ThinkFL \
  --trust-remote-code \
  --tensor-parallel-size=1 \
  --port 8000
```

### Example Prompt Usage

You can interact with the deployed ThinkFL model using standard OpenAI-compatible chat completions. The model is designed to act as a software operations engineer that diagnoses system failures by invoking predefined tools.

Below is a complete example of a multi-turn conversation where the model:

Analyzes a root trace,
Recursively explores child spans,
Queries fluctuating metrics around a suspicious service,
Finally outputs a ranked list of potential root causes.

```json
[
  {
    "role": "system",
    "content": "You are a software operations engineer. Your task is to systematically diagnose and identify the root cause of software failures.\n\nYou have the following tools:\n\n[{\"type\": \"function\", \"function\": {\"name\": \"search_traces\", \"description\": \"Get all traces with the input span_id as the parent\", \"parameters\": {\"type\": \"object\", \"properties\": {\"parent_span_id\": {\"type\": \"string\", \"description\": \"The parent span_id to be queried.\"}}, \"required\": [\"parent_span_id\"]}}}, {\"type\": \"function\", \"function\": {\"name\": \"search_fluctuating_metrics\", \"description\": \"Get all fluctuating metrics with the input service_name and around the input timestamp\", \"parameters\": {\"type\": \"object\", \"properties\": {\"service_name\": {\"type\": \"string\", \"description\": \"The service_name to be queried.\"}, \"timestamp\": {\"type\": \"string\", \"description\": \"The timestamp to be queried.\"}}, \"required\": [\"service_name\", \"timestamp\"]}}}, {\"type\": \"function\", \"function\": {\"name\": \"print_results\", \"description\": \"Print the root cause node/service/pod and corresponding reason.\", \"parameters\": {\"type\": \"object\", \"properties\": {\"root_causes\": {\"type\": \"array\", \"description\": \"An array of potential root causes ordered by likelihood. You may include any number of causes, but you must provide at least three potential root causes.\", \"items\": {\"type\": \"object\", \"properties\": {\"node\": {\"type\": \"string\", \"description\": \"The root cause node (e.g. node-1).\"}, \"service\": {\"type\": \"string\", \"description\": \"The root cause service (e.g. recommendationservice).\"}, \"pod\": {\"type\": \"string\", \"description\": \"The root cause pod (e.g. recommendationservice-0).\"}}, \"required\": []}}}}}}]\n\nThe parameters for these tools should be filled as a JSON object, with JSON keys as parameter names and key values as parameter content.\n\nYou must insert the following command once in your reply to call the tool:\n\n<tool_call>{'name': tool name, **can and must only** be one of [search_traces, search_fluctuating_metrics, print_results], 'arguments': tool input}<tool_call>"
  },
  {
    "role": "user",
    "content": "Please read the following root trace and identify corresponding root cause service.\nA possible approach is to recursively search for the traces you suspect have issues, and combine with metrics data to confirm the root cause.\n                             timestamp      cmdb_id           span_id                          trace_id  duration  type status_code              operation_name parent_span\n5159784  1647758897785   frontend-2  a260c8c867cf4b1c  f25cf75421090eef9c6c14270f1eb385  17244804  http           0  hipstershop.Frontend/Recv.         NaN"
  },
  {
    "role": "assistant",
    "content": "<tool_call>{\"name\": \"search_traces\", \"arguments\": \"{\\\"parent_span_id\\\": \\\"a260c8c867cf4b1c\\\"}\"}</tool_call>"
  },
  {
    "role": "tool",
    "content": "[{\"cmdb_id\":\"frontend-2\",\"duration\":17132774,\"operation_name\":\"hipstershop.CartService/GetCart\",\"parent_span\":\"a260c8c867cf4b1c\",\"span_id\":\"91486122a04fec40\",\"status_code\":\"0\",\"timestamp\":1647758897795,\"trace_id\":\"f25cf75421090eef9c6c14270f1eb385\",\"type\":\"rpc\"}, ...]"
  },
  {
    "role": "assistant",
    "content": "<tool_call>{\"name\": \"search_traces\", \"arguments\": \"{\\\"parent_span_id\\\": \\\"91486122a04fec40\\\"}\"}</tool_call>"
  },
  {
    "role": "tool",
    "content": "[{\"cmdb_id\":\"cartservice-2\",\"duration\":16177000,\"operation_name\":\"/hipstershop.CartService/GetCart\",\"parent_span\":\"91486122a04fec40\",\"span_id\":\"d55ed143102a3146\",\"status_code\":\"200\",\"timestamp\":1647758898844,\"trace_id\":\"f25cf75421090eef9c6c14270f1eb385\",\"type\":\"http\"}]"
  },
  {
    "role": "assistant",
    "content": "<tool_call>{\"name\": \"search_traces\", \"arguments\": \"{\\\"parent_span_id\\\": \\\"d55ed143102a3146\\\"}\"}</tool_call>"
  },
  {
    "role": "tool",
    "content": "[{\"cmdb_id\":\"cartservice-2\",\"duration\":2000,\"operation_name\":\"HGET\",\"parent_span\":\"d55ed143102a3146\",\"span_id\":\"f3d07142bfe0404b\",\"status_code\":\"Ok\",\"timestamp\":1647758914868,\"trace_id\":\"f25cf75421090eef9c6c14270f1eb385\",\"type\":\"db\"}]"
  },
  {
    "role": "assistant",
    "content": "<tool_call>{\"name\": \"search_fluctuating_metrics\", \"arguments\": \"{\\\"service_name\\\": \\\"cartservice\\\", \\\"timestamp\\\": \\\"1647758897785\\\"}\"}</tool_call>"
  },
  {
    "role": "tool",
    "content": "{\"node-5.cartservice2-0.container_cpu_cfs_throttled_periods\": {\"regular_mean\": 0.2, ...}, \"node-6.cartservice-2.container_cpu_usage_seconds\": {\"regular_mean\": 0.492..., \"current_mean\": 0.547...}, ...}"
  },
  {
    "role": "assistant",
    "content": "<tool_call>{\"name\": \"print_results\", \"arguments\": \"{\\\"root_causes\\\": [{\\\"service\\\": \\\"cartservice\\\"}, {\\\"pod\\\": \\\"cartservice-2\\\"}, {\\\"node\\\": \\\"node-6\\\"}, {\\\"service\\\": \\\"redis-cart\\\"}, {\\\"service\\\": \\\"productcatalog-cart\\\"}, {\\\"pod\\\": \\\"cartservice-2\\\"}, {\\\"service\\\": \\\"cartservice\\\"}, {\\\"node\\\": \\\"node-6\\\"}, {\\\"service\\\": \\\"cartservice\\\"}, {\\\"service\\\": \\\"recommendationservice\\\"}, {\\\"service\\\": \\\"adservice\\\"}, {\\\"service\\\": \\\"productcatalogservice\\\"}, {\\\"service\\\": \\\"currencyservice\\\"}]}\"}<tool_call>"
  }
]
```

In practice, you can directly adopt the calling pattern from RCLAgent ([https://github.com/LLMLog/RCLAgent](https://github.com/LLM4AIOps/ThinkFL)), which provides a more comprehensive agent framework-including advanced mechanisms such as critical rethink, tool orchestration, and multi-step reasoning. To integrate ThinkFL, simply replace the underlying LLM interface in RCLAgent with the ThinkFL API endpoint deployed via vLLM.

We also provide a dedicated calling repository for ThinkFL ([https://github.com/LLM4AIOps/ThinkFL](https://github.com/LLM4AIOps/ThinkFL)), which offers a simpler integration path-though it omits the data preprocessing steps for brevity and ease of use.

## Citation

If you find our work helpful, please cite:

```bibtex
@article{zhang2025thinkfl,
  title={ThinkFL: Self-Refining Failure Localization for Microservice Systems via Reinforcement Fine-Tuning},
  author={Zhang, Lingzhe and Zhai, Yunpeng and Jia, Tong and Duan, Chiming and Yu, Siyu and Gao, Jinyang and Ding, Bolin and Wu, Zhonghai and Li, Ying},
  journal={arXiv preprint arXiv:2504.18776},
  year={2025}
}
@article{zhang2025adaptive,
  title={Adaptive root cause localization for microservice systems with multi-agent recursion-of-thought},
  author={Zhang, Lingzhe and Jia, Tong and Wang, Kangjin and Hong, Weijie and Duan, Chiming and He, Minghua and Li, Ying},
  journal={arXiv preprint arXiv:2508.20370},
  year={2025}
}
```