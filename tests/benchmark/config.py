"""
性能测试配置文件
"""
import os
import sys
from pathlib import Path

# 添加tests目录到Python路径
TESTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_DIR))

# 基础路径
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent.parent
LOGS_DIR = TESTS_DIR / "logs"
RESULTS_DIR = TESTS_DIR / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 确保目录存在
for dir_path in [TESTS_DIR, LOGS_DIR, RESULTS_DIR, REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 服务器配置
CURRENT_IMPLEMENTATION_URL = "http://localhost:8000"
OPENCODE_WEB_URL = "http://localhost:8888"

# 测试配置
TEST_PROJECT_ID = "proj_benchmark_test"
TEST_NUM_RUNS = 10
TEST_TIMEOUT = 60  # 秒

# 认证配置（如果需要）
OPENCODE_WEB_PASSWORD = os.environ.get("OPENCODE_WEB_PASSWORD", "default_test_password")

# 日志配置
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "benchmark.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
