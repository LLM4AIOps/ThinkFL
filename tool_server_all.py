import json
import pickle
import sys

import pandas as pd
from flask import Flask, request, jsonify

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

app = Flask(__name__)

sub_paths = [
    "2022-03-20-cloudbed1", "2022-03-20-cloudbed2", "2022-03-20-cloudbed3",
    "2022-03-21-cloudbed1", "2022-03-21-cloudbed2", "2022-03-21-cloudbed3",
    "2022-03-24-cloudbed3"
]

cloudbed_data = {}

for sub_path in sub_paths:
    cloudbed_id = sub_path

    # 初始化存储结构
    cloudbed_data[cloudbed_id] = {
        "node_service_map": None,
        "service_node_map": None,
        "trace_df": None,
        "metric_df": None
    }

    # 加载 node-service 映射
    with open(f"data/{sub_path}/metric/node_service_map.pkl", "rb") as fr:
        cloudbed_data[cloudbed_id]["node_service_map"] = pickle.load(fr)

    with open(f"data/{sub_path}/metric/service_node_map.pkl", "rb") as fr:
        cloudbed_data[cloudbed_id]["service_node_map"] = pickle.load(fr)

    # 加载跟踪数据
    trace_df = pd.read_csv(f'data/{sub_path}/trace/all/trace_jaeger-span.csv')
    cloudbed_data[cloudbed_id]["trace_df"] = trace_df

    # 加载指标数据
    metric_df = pd.read_csv(f'data/{sub_path}/metric/all/metrics.csv')
    cloudbed_data[cloudbed_id]["metric_df"] = metric_df


@app.route('/check_trace', methods=['GET'])
def check_trace():
    span_id = request.args.get('span_id')
    if not span_id:
        return jsonify({"error": "span_id 参数缺失"}), 400

    for sub_path in sub_paths:
        trace_df = cloudbed_data[sub_path]["trace_df"]
        result_rows = trace_df[trace_df['span_id'] == span_id]
        if not result_rows.empty:
            return jsonify({"exists": True}), 200

    return jsonify({"exists": False}), 404


@app.route('/search_traces', methods=['GET'])
def search_traces():
    cloudbed_id = request.args.get('cloudbed_id')
    span_id = request.args.get('parent_span_id')
    if not span_id:
        return jsonify({"error": "span_id 参数缺失"}), 400
    if not cloudbed_id:
        return jsonify({"error": "cloudbed_id 参数缺失"}), 400
    if cloudbed_id not in cloudbed_data:
        return jsonify({"error": f"cloudbed_id '{cloudbed_id}' 不存在"}), 400

    trace_df = cloudbed_data[cloudbed_id]["trace_df"]
    result_rows = trace_df[trace_df['parent_span'] == span_id]

    if not result_rows.empty:
        print(result_rows.to_dict(orient='records'))
        return jsonify(result_rows.to_dict(orient='records'))
    else:
        return jsonify({"message": f"No trace with parent_span = '{span_id}'。"}), 200


@app.route('/search_fluctuating_metrics', methods=['GET'])
def search_metrics():
    cloudbed_id = request.args.get('cloudbed_id')
    service_name = request.args.get('service_name')
    timestamp_str = request.args.get('timestamp')

    if not cloudbed_id:
        return jsonify({"error": "cloudbed_id 参数缺失"}), 400
    if not timestamp_str:
        return jsonify({"error": "timestamp_str 参数缺失"}), 400
    if not timestamp_str:
        return jsonify({"error": "service_name 参数缺失"}), 400
    if cloudbed_id not in cloudbed_data:
        return jsonify({"error": f"cloudbed_id '{cloudbed_id}' 不存在"}), 400

    if len(timestamp_str) > 10:
        timestamp_str = timestamp_str[:10]
    timestamp = int(timestamp_str)

    service_node_map = cloudbed_data[cloudbed_id]["service_node_map"]
    metric_df = cloudbed_data[cloudbed_id]["metric_df"]
    if service_name in service_node_map:
        node_id = service_node_map[service_name]

        condition = (
                ((metric_df['service_name'].str.contains(service_name, case=False, na=False)) | (
                        (metric_df['node_id'] == node_id) & (metric_df[
                                                                 'service_name'] == ""))) &
                (metric_df['timestamp'] >= timestamp - 1200) &
                (metric_df['timestamp'] <= timestamp + 1200)
        )
    else:
        condition = (
                (metric_df['service_name'].str.contains(service_name, case=False, na=False)) &
                (metric_df['timestamp'] >= timestamp - 1200) &
                (metric_df['timestamp'] <= timestamp + 1200)
        )

    result_rows = metric_df[condition]

    if not result_rows.empty:
        kpi_dict = dict()

        for (kpi, node_id, service_name), group in result_rows.groupby(['kpi_name', 'node_id', 'service_name']):
            mean_value = group['value'].mean()
            std_dev_value = group['value'].std()
            group = group[(group['timestamp'] >= timestamp - 600) & (group['timestamp'] <= timestamp + 600)]

            if pd.notna(mean_value) and pd.notna(std_dev_value):
                threshold = 3 * std_dev_value

                is_fluctuating = (
                        (group['value'] < (mean_value - threshold)) |
                        (group['value'] > (mean_value + threshold))
                ).any()

                if is_fluctuating:
                    # 初始化 key 为 kpi_name
                    key = kpi  # 直接使用 kpi，因为 groupby 的 kpi_name 是唯一的

                    # 如果 service_name 存在且不是 NaN，则添加到 key
                    if not pd.isna(service_name):
                        key = f"{service_name}.{key}"

                    # 如果 node_id 存在且不是 NaN，则添加到 key
                    if not pd.isna(node_id):
                        key = f"{node_id}.{key}"

                    # 将最终的 key 添加到集合中
                    kpi_dict[key] = {
                        "regular_mean": round(mean_value, 2),
                        "regular_std_dev": round(std_dev_value, 2),
                        "current_mean": round(group['value'].mean(), 2),
                        "current_std_dev": round(group['value'].std(), 2),
                    }

        if len(kpi_dict) > 0:
            table = []
            header = ['key', 'regular_mean', 'regular_std_dev', 'current_mean', 'current_std_dev']
            table.append(header)

            for key, values in kpi_dict.items():
                row = [key] + list(values.values())
                table.append(row)

            # 转换为 pandas DataFrame 以便于处理
            df = pd.DataFrame(table[1:], columns=table[0])

            # 打印为 CSV 格式
            print(df.to_csv(index=False))
            return df.to_csv(index=False)
        else:
            return jsonify({"message": "No fluctuating metrics found."}), 200
    else:
        return jsonify({"message": "No matching records found."}), 200


if __name__ == '__main__':
    app.run(debug=False, port=5001)
