#!/usr/bin/env python3
"""
Inventory Analysis / 库存分析工具

依赖 Dependencies：
    pip install streamlit pandas altair
"""
import sys

# 依赖检查 Dependency check
try:
    import streamlit as st
    import pandas as pd
    import altair as alt
except ModuleNotFoundError as e:
    print(f"错误 Error: 缺少模块 {e.name} / missing module {e.name}，请使用 pip 安装依赖后再运行 / please install dependencies via pip and retry.")
    sys.exit(1)

import re

# 工具函数 Utility: 清洗数字字符串 / clean numeric strings
def to_number(s):
    """去掉货币符号、逗号和括号，并转换为 float / remove currency symbols, commas, parentheses, convert to float"""
    s = str(s)
    s = re.sub(r'[\$,()]', '', s)
    try:
        return float(s)
    except ValueError:
        return 0.0

# 应用标题 App title
st.title("Inventory Analysis / 库存分析")

# 文件上传 File uploader
uploaded = st.file_uploader("Please upload csv file / 请上传 CSV 文件", type="csv")

if uploaded:
    # 读取数据并清洗列名，跳过前3行说明 / read data, strip names, skip 3 header rows
    df = pd.read_csv(uploaded, skiprows=3)
    df.columns = df.columns.str.strip().str.replace(' ', '', regex=False)
    for col in df.columns:
        if col != 'Item':
            df[col] = df[col].apply(to_number)

    # 提取总收入并过滤明细 / extract total revenue, filter details
    total_mask = df['Item'].str.strip().str.lower().str.startswith('total')
    if not total_mask.any():
        st.error("CSV 中未找到以 'Total' 开头的汇总行 / could not find summary row starting with 'Total'.")
        st.stop()
    total_rev = df.loc[total_mask, 'TotalRevenue'].iloc[0]
    df_items = df.loc[~total_mask].copy()

    # 预算设置 Budget settings
    st.sidebar.header("Budget Settings / 预算设置")
    total_budget = st.sidebar.number_input(
        "Annual Total Budget (currency) / 年度总预算(货币单位)", min_value=0.0, value=100000.0, step=1000.0
    )

    # 计算预算分配 Calculate budget allocation
    df_items['RevWeight'] = df_items['TotalRevenue'] / total_rev
    df_items['AnnualBudgetAlloc'] = df_items['RevWeight'] * total_budget
    df_items['MonthlyBudgetAlloc'] = df_items['AnnualBudgetAlloc'] / 12.0
    df_items['CurrentInventoryValue'] = df_items['CurrentOnHandValue']
    df_items['CoverMonths'] = df_items['CurrentInventoryValue'] / df_items['MonthlyBudgetAlloc']

    # 库存水平分类 Inventory level categorization
    def categorize(m):
        if m < 1:
            return 'Danger (<1 month) / 危险 (<1月)'
        elif m < 3:
            return 'Low (1-3 months) / 不足 (1-3月)'
        elif m <= 6:
            return 'Normal (3-6 months) / 正常 (3-6月)'
        else:
            return 'Excess (>6 months) / 过剩 (>6月)'
    df_items['Category'] = df_items['CoverMonths'].apply(categorize)

    # 定义 Category 颜色映射 Color map for Category column
    color_map = {
        'Danger (<1 month) / 危险 (<1月)': '#d62728',
        'Low (1-3 months) / 不足 (1-3月)': '#ff7f0e',
        'Normal (3-6 months) / 正常 (3-6月)': '#2ca02c',
        'Excess (>6 months) / 过剩 (>6月)': '#7f7f7f'
    }

    # 格式化显示设置：RevWeight 显示为百分比，保留6位小数，其它数值保留2位
    format_dict = {
        'RevWeight': '{:.6%}',
        'AnnualBudgetAlloc': '{:,.2f}',
        'MonthlyBudgetAlloc': '{:,.2f}',
        'CoverMonths': '{:.2f}'
    }

    # 搜索功能 Search by Item
    st.subheader("🔍 Search by Item / 按 Item 搜索")
    q = st.text_input("Enter keyword / 输入关键词：Item")
    if q:
        res = df_items[df_items['Item'].str.contains(q, case=False, na=False)]
        if res.empty:
            st.info(f"未找到匹配 '{q}' 的产品 / no matching items for '{q}'.")
        else:
            # 样式应用：格式化并为 Category 列添加背景色
            styler_res = res.style.format(format_dict) \
                .applymap(lambda v: f"background-color: {color_map.get(v, '')}", subset=['Category'])
            st.dataframe(styler_res, use_container_width=True)

    # 显示完整结果表 Show full results
    st.subheader("Results Table / 计算结果表")
    styler_full = df_items.style.format(format_dict) \
        .applymap(lambda v: f"background-color: {color_map.get(v, '')}", subset=['Category'])
    st.dataframe(styler_full, use_container_width=True)

    # Top20 按收入排名 Top 20 by revenue
    top20_rev = df_items.nlargest(20, 'TotalRevenue')
    st.subheader("🏆 Top20 Items by Revenue / 按收入排名前20产品")
    chart = alt.Chart(top20_rev).mark_bar().encode(
        y=alt.Y('Item:N', sort='-x', title=None),
        x=alt.X('CoverMonths:Q', title='Cover Months / 库存覆盖月数'),
        color=alt.Color('Category:N', scale=alt.Scale(
            domain=list(color_map.keys()),
            range=list(color_map.values())
        )),
        tooltip=[
            alt.Tooltip('Item:N', title='Item / 产品'),
            alt.Tooltip('TotalRevenue:Q', title='Total Revenue / 总收入', format='.2f'),
            alt.Tooltip('CoverMonths:Q', title='Cover Months / 覆盖月数', format='.2f'),
            alt.Tooltip('CurrentInventoryValue:Q', title='Inventory Value / 当前库存价值', format='.2f'),
            alt.Tooltip('MonthlyBudgetAlloc:Q', title='Monthly Budget / 月度预算', format='.2f'),
            alt.Tooltip('Category:N', title='Category / 分类')
        ]
    ).properties(width=700, height=400)
    st.altair_chart(chart, use_container_width=True)

    # 完成提示 Finish message
    st.success("Analysis complete! / 分析完成，可依据结果进行决策。")
