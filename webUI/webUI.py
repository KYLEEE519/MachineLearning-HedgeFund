import gradio as gr
import json
from indicators import indicator_registry, indicator_params
import pandas as pd
import numpy as np
from okx_fetch_data import fetch_kline_df
from data_process import show_data, load_csv, save_data
from data_process import update_param_inputs_json, add_indicator_json, generate_features_by_json, default_feature_config
from data_process import generate_target
from data_process import clean_data
from data_process import get_columns, validate_data
from train_process import train_model
from train_process import hyperparameter_search


with gr.Blocks() as demo:
    with gr.Tab("数据处理与特征工程"):
        gr.Markdown("# XGBoost 可视化训练工具（完整功能版）")
        
        # ----- 数据获取 -----
        with gr.Row():
            days = gr.Number(label="获取最近几天数据（days）", info="例如7表示最近7天")
            bar = gr.Textbox(label="K线粒度（bar）", info="例如1m、5m、1H、4H")
            instId = gr.Textbox(label="交易对（instId）", info="例如BTC-USDT")
        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")
        load_button = gr.Button("获取并展示数据")
        load_button.click(fn=show_data, inputs=[days, bar, instId], outputs=[data_info, all_columns])
        
        # ----- 单指标生成 -----
        gr.Markdown("## 单指标生成")
        indicator_name = gr.Dropdown(choices=list(indicator_registry.keys()), label="选择指标")
        column = gr.Textbox(label="作用列", value="close")
        confirm_param_button = gr.Button("确认生成参数输入框")
        json_params = gr.Textbox(label="请在此输入指标参数（JSON 格式）", visible=False, lines=10)
        # Markdown 组件，用于显示参数说明（instruction）
        param_instructions = gr.Markdown(label="参数说明")
        confirm_param_button.click(
            fn=update_param_inputs_json,
            inputs=[indicator_name],
            outputs=[json_params, param_instructions]
        )
        new_col_name = gr.Textbox(label="新列名（可选）")
        add_indicator_button = gr.Button("生成指标")
        add_indicator_button.click(
            fn=add_indicator_json,
            inputs=[indicator_name, column, new_col_name, json_params],
            outputs=[data_info, all_columns]
        )
        
        # ----- 批量生成特征 -----
        gr.Markdown("## 编辑 JSON 自动批量生成特征")
        json_editor = gr.Code(
            label="指标配置 JSON",
            language="json",
            value=json.dumps(default_feature_config, indent=4)
        )
        new_data_info = gr.Markdown()
        new_all_columns = gr.Markdown(label="最新全部列名")
        generate_button = gr.Button("批量生成特征")
        generate_button.click(
            fn=generate_features_by_json,
            inputs=[json_editor],
            outputs=[new_data_info, new_all_columns]
        )
        
        # ----- 生成 Target 列 -----
        gr.Markdown("## 选择 Target 列")
        target_type = gr.Dropdown(choices=["涨跌（1为涨，0为跌）", "涨跌幅"], label="选择 Target 类型")
        target_data_info = gr.Markdown()
        target_all_columns = gr.Markdown(label="最新全部列名")
        generate_target_button = gr.Button("生成 Target 列")
        generate_target_button.click(
            fn=generate_target,
            inputs=[target_type],
            outputs=[target_data_info, target_all_columns]
        )
        
        # ----- 数据清理 -----
        gr.Markdown("## 数据清理")
        clean_type = gr.Dropdown(choices=["中位数填充", "均值填充", "删除含NaN的行"], label="选择数据清理方式")
        clean_info = gr.Markdown()
        clean_cols = gr.Markdown(label="最新全部列名")
        clean_button = gr.Button("执行数据清理")
        clean_button.click(
            fn=clean_data,
            inputs=[clean_type],
            outputs=[clean_info, clean_cols]
        )
        gr.Markdown("## 数据保存")

        save_path_info = gr.Markdown()
        save_button = gr.Button("保存数据为 CSV")

        save_button.click(
            fn=save_data,
            inputs=[instId],
            outputs=[save_path_info]
        )
    with gr.Tab("XGBoost 训练"):
        gr.Markdown("# XGBoost 可视化训练")

        csv_path = gr.Textbox(label="输入 CSV 文件绝对路径")
        load_csv_button = gr.Button("读取 CSV")

        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")

        feature_cols = gr.Dropdown(choices=[], label="选择特征列(可多选)", multiselect=True)
        target_col = gr.Dropdown(choices=[], label="选择目标列(单选)", multiselect=False)

        load_csv_button.click(fn=load_csv, inputs=[csv_path], outputs=[data_info, all_columns])
        load_csv_button.click(fn=get_columns, inputs=[], outputs=[feature_cols, target_col])
        with gr.Tab("模型训练"):
            gr.Markdown("### 模型参数设置")

            learning_rate = gr.Slider(0.001, 1.0, 0.1, step=0.001, label="学习率")
            n_estimators = gr.Slider(10, 500, 50, step=10, label="迭代次数")
            max_depth = gr.Slider(1, 15, 3, step=1, label="最大深度")
            subsample = gr.Slider(0.6, 0.9, 0.8, step=0.1, label="subsample（行采样比例）")
            colsample_bytree = gr.Slider(0.6, 1.0, 0.8, step=0.1, label="colsample_bytree（列采样比例）")
            gamma = gr.Slider(0.0, 0.5, 0.1, step=0.1, label="gamma（最小损失减少）")
            reg_lambda = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_lambda（L2 正则）")
            reg_alpha = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_alpha（L1 正则）")

            train_button = gr.Button("开始训练")

            loss_img = gr.Image(label="Train vs Val Loss 曲线")
            importance_img = gr.Image(label="特征重要性图")
            acc = gr.Textbox(label="验证集评估指标")
            save_info = gr.Textbox(label="模型保存信息")
            roc_img = gr.Image(label="ROC 曲线图（分类任务）")

            train_button.click(
                fn=train_model,
                inputs=[
                    feature_cols, target_col,
                    learning_rate, max_depth, n_estimators,
                    subsample, colsample_bytree, gamma, reg_lambda, reg_alpha
                ],
                outputs=[loss_img, importance_img, acc, save_info, roc_img]
            )
        with gr.Tab("超参数搜索"):
            gr.Markdown("# XGBoost 超参数搜索（RandomizedSearchCV）")

            gr.Markdown("### 超参数范围设置（最大范围固定，可缩小范围 & 调整步长）")

            # 每个超参数范围设置
            lr_min = gr.Slider(0.001, 1.0, 0.001, step=0.001, label="learning_rate 最小值")
            lr_max = gr.Slider(0.001, 1.0, 0.1, step=0.001, label="learning_rate 最大值")
            lr_step = gr.Slider(0.001, 1.0, 0.001, step=0.001, label="learning_rate 步长")

            n_min = gr.Slider(10, 500, 10, step=10, label="n_estimators 最小值")
            n_max = gr.Slider(10, 500, 100, step=10, label="n_estimators 最大值")
            n_step = gr.Slider(10, 500, 10, step=10, label="n_estimators 步长")

            depth_min = gr.Slider(1, 15, 1, step=1, label="max_depth 最小值")
            depth_max = gr.Slider(1, 15, 3, step=1, label="max_depth 最大值")
            depth_step = gr.Slider(1, 15, 1, step=1, label="max_depth 步长")

            subsample_min = gr.Slider(0.6, 0.9, 0.6, step=0.1, label="subsample 最小值")
            subsample_max = gr.Slider(0.6, 0.9, 0.8, step=0.1, label="subsample 最大值")
            subsample_step = gr.Slider(0.1, 0.3, 0.1, step=0.1, label="subsample 步长")

            colsample_min = gr.Slider(0.6, 1.0, 0.6, step=0.1, label="colsample_bytree 最小值")
            colsample_max = gr.Slider(0.6, 1.0, 0.8, step=0.1, label="colsample_bytree 最大值")
            colsample_step = gr.Slider(0.1, 0.3, 0.1, step=0.1, label="colsample_bytree 步长")

            gamma_min = gr.Slider(0.0, 0.5, 0.0, step=0.1, label="gamma 最小值")
            gamma_max = gr.Slider(0.0, 0.5, 0.1, step=0.1, label="gamma 最大值")
            gamma_step = gr.Slider(0.1, 0.3, 0.1, step=0.1, label="gamma 步长")

            lambda_min = gr.Slider(0.0, 10.0, 0.0, step=0.5, label="reg_lambda 最小值")
            lambda_max = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_lambda 最大值")
            lambda_step = gr.Slider(0.5, 5.0, 0.5, step=0.5, label="reg_lambda 步长")

            alpha_min = gr.Slider(0.0, 10.0, 0.0, step=0.5, label="reg_alpha 最小值")
            alpha_max = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_alpha 最大值")
            alpha_step = gr.Slider(0.5, 5.0, 0.5, step=0.5, label="reg_alpha 步长")

            n_iter = gr.Slider(5, 100, 20, step=1, label="采样超参数组合的次数")

            search_result = gr.Markdown(label="搜索结果")

            search_button = gr.Button("开始超参数搜索")

            # 按钮逻辑
            search_button.click(
                fn=hyperparameter_search,
                inputs=[
                    feature_cols, target_col, n_iter,
                    lr_min, lr_max, lr_step,
                    n_min, n_max, n_step,
                    depth_min, depth_max, depth_step,
                    subsample_min, subsample_max, subsample_step,
                    colsample_min, colsample_max, colsample_step,
                    gamma_min, gamma_max, gamma_step,
                    lambda_min, lambda_max, lambda_step,
                    alpha_min, alpha_max, alpha_step,
                ],
                outputs=[search_result]
            )
demo.launch()
