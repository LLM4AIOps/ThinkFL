print_result_function = {
    "name": "print_results",
    "description": "Print a list of potential root causes with corresponding nodes/services/pods and reasons, ordered by likelihood.",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_causes": {
                "type": "array",
                "description": "An array of potential root causes ordered by likelihood.",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "string",
                            "description": "The root cause timestamp."
                        },
                        "node": {
                            "type": "string",
                            "description": "The root cause node (e.g. node-1)."
                        },
                        "service": {
                            "type": "string",
                            "description": "The root cause service (e.g. recommendationservice)."
                        },
                        "pod": {
                            "type": "string",
                            "description": "The root cause pod (e.g. recommendationservice-0)."
                        },
                        "reason": {
                            "type": "string",
                            "description": "The corresponding reason."
                        }
                    },
                    "required": [
                        "timestamp",
                        "reason"
                    ]
                }
            }
        },
        "required": [
            "root_causes"
        ]
    }
}

search_traces_function = {
    "name": "search_traces",
    "description": "Get all traces with the input span_id as the parent",
    "input_schema": {
        "type": "object",
        "properties": {
            "parent_span_id": {
                "type": "string",
                "description": "The parent span_id to be queried."
            },
        },
        "required": [
            "parent_span_id"
        ]
    }
}

search_fluctuating_metrics_function = {
    "name": "search_fluctuating_metrics",
    "description": "Get all fluctuating metrics with the input service_name and around the input timestamp",
    "input_schema": {
        "type": "object",
        "properties": {
            "service_name": {
                "type": "string",
                "description": "The service_name to be queried."
            },
            "timestamp": {
                "type": "string",
                "description": "The timestamp to be queried."
            }
        },
        "required": [
            "service_name",
            "timestamp"
        ]
    }
}
