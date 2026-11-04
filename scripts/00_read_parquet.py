"""第 0 步：只读 Parquet 元数据，认识文件和字段。"""

import pyarrow.parquet as pq

from common import check_data


path = check_data()
parquet = pq.ParquetFile(path)

# metadata 不需要把 450 万行全部读进内存。
print("总行数：", f"{parquet.metadata.num_rows:,}")
print("Row groups：", parquet.metadata.num_row_groups)
print("顶层字段：")
for field in parquet.schema_arrow:
    print(f"  {field.name}: {field.type}")
print("数据文件路径：", path)
print("字段数量：", len(parquet.schema_arrow))
# 思考：为什么 sale_amount 是实际销量，而不是完整需求？
