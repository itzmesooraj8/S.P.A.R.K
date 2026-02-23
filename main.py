import os
import sys

# Ensure spark_core is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
spark_core_path = os.path.join(current_dir, "spark_core")
if spark_core_path not in sys.path:
    sys.path.insert(0, spark_core_path)

# Run the spark_core main
from spark_core.main import app
import uvicorn

if __name__ == "__main__":
    print("🛸 [SPARK] Booting Sovereign Core from Root...")
    uvicorn.run("spark_core.main:app", host="0.0.0.0", port=8000, reload=False)
