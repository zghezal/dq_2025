from src.context.spark_context import SparkDQContext
from dq.executors.missing_rate_runner import run_missing_rate_with_filter

context = SparkDQContext(catalog={ "sales_2024": "sourcing/input/sales_2024.csv" })

# Example 1: filter region == 'North'
out1 = run_missing_rate_with_filter(
    context,
    dataset="sales_2024",
    column=None,               # missing rate on entire dataset
    filter_name="region_north",
    stream="streamA",
    project="p1",
    zone="raw"
)
print("Region North -> Blocked:", out1["blocked"], "Reason:", out1["reason"])
for t in out1["prechecks"]:
    print("  precheck:", t["control_id"], t["control_name"], "=>", t["result"])

# Example 2: filter quantity == 10 (uses type N)
out2 = run_missing_rate_with_filter(
    context,
    dataset="sales_2024",
    column="quantity",         # profile a specific column
    filter_name="quantity_eq_10",
    stream="streamA",
    project="p1",
    zone="raw"
)
print("Quantity==10 -> Blocked:", out2["blocked"], "Reason:", out2["reason"])
for t in out2["prechecks"]:
    print("  precheck:", t["control_id"], t["control_name"], "=>", t["result"])

if not out1["blocked"] and out1["metric_result"]:
    print("MR (region_north):", out1["metric_result"].value)
if not out2["blocked"] and out2["metric_result"]:
    print("MR (quantity==10 on 'quantity'):", out2["metric_result"].value)

# Note: interval_check plugin is the authorized test for threshold validation
# Example: using interval_check to validate missing_rate is within bounds
# from src.plugins.tests.interval_check import IntervalCheck
# metric_id = "streamA.p1.raw.metric.missing_rate.sales_2024.col=quantity.filter=quantity_eq_10"
# t = IntervalCheck()
# tres = t.run(
#     context,
#     specific={"metric_id": metric_id, "lower": 0.0, "upper": 0.2},
#     id="T-interval-1",
#     label="Interval check on MR"
# )
# print("interval_check:", tres.passed, tres.message)
