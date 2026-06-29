import pathlib
import sys

# 确保 `import app...` 在 `cd backend && pytest` 下可用
sys.path.insert(0, str(pathlib.Path(__file__).parent.resolve()))
