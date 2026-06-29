import os
import time
import logging
import pandas as pd
from typing import Optional, Dict
from pyhive import hive
from TCLIService.ttypes import TOperationState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataWorks:
    def __init__(self, token_id: Optional[str] = None, host: Optional[str] = None):
        self.token_id = token_id or os.environ.get("DATAWORKS_TOKEN_ID")
        if not self.token_id:
            # Allow initialization without token, but warn/fail on execution
            logger.warning("DATAWORKS_TOKEN_ID not provided. Execution will fail.")

        self.default_host = host or os.environ.get("DATAWORKS_HOST", "proxy-service-thrift-cnbj1-dp.api.xiaomi.net")
        self.host = self.default_host

        self.host_map = {
            'zjyprc': 'proxy-service-thrift-cnbj1-dp.api.xiaomi.net',
            'nc4cloudprc': 'proxy-service-thrift-nc4cloudprc-dp.api.xiaomi.net',
            'nc4prc': 'proxy-service-thrift-nc4prc-dp.api.xiaomi.net',
            'tjwq': 'proxy-service-thrift-cnbj2-dp.api.xiaomi.net',
            'alsgprc': 'proxy-service-thrift-alisgp0-dp.api.xiaomi.net',
            'ksmosprc': 'proxy-service-thrift-ksyru0-dp.api.xiaomi.net',
            'usaor': 'proxy-service-thrift-awsor0-dp.api.xiaomi.net',
            'nlams': 'proxy-service-thrift-azamsprc0-dp.api.xiaomi.net',
            'azpnprc': 'proxy-service-thrift-azpnprc-dp.api.xiaomi.net',
            'tjv1autopilotprc': 'proxy-service-thrift-tjv1autopilotprc-dp.api.xiaomi.net'
        }

    def _get_host_for_sql(self, sql: str) -> str:
        for key, value in self.host_map.items():
            if key in sql:
                return value
        return self.default_host

    def list_hosts(self) -> Dict[str, str]:
        return self.host_map

    def execute_sql(self, sql: str) -> str:
        if not self.token_id:
            return "Error: DATAWORKS_TOKEN_ID is not configured."

        self.host = self._get_host_for_sql(sql)

        start_time = time.time()
        config = {"proxy.engine": "presto"}

        try:
            conn = hive.connect(host=self.host, configuration=config, port=80, username=self.token_id)
            cursor = conn.cursor()
            cursor.execute(sql, async_=True)

            status = cursor.poll().operationState

            while status in (
            TOperationState.INITIALIZED_STATE, TOperationState.RUNNING_STATE, TOperationState.PENDING_STATE):
                status = cursor.poll().operationState
                if time.time() - start_time > 250:
                    return "Error: Execution timed out (250s). Please reduce data scope or add partitions."
                time.sleep(0.5)

            if status == TOperationState.ERROR_STATE:
                logs = cursor.fetch_logs()
                error_msg = ';'.join(logs)
                logger.error(f"SQL Execution Error: {error_msg}")
                return f"SQL Execution Failed.\nError: {error_msg}"

            if status == TOperationState.CANCELED_STATE:
                return "SQL Execution Canceled."

            # Fetch results
            if cursor.description:
                header = [field[0] for field in cursor.description]
                rows = cursor.fetchall()
            else:
                return "SQL executed successfully (no results)."

            df = pd.DataFrame(rows, columns=header)

            if len(rows) == 0:
                return "SQL executed successfully, but result is empty."

            # Check for large result set
            is_limit = 'LIMIT' in sql.upper()
            is_describe = 'DESCRIBE' in sql.upper()

            if len(rows) > 15 and not is_limit and not is_describe:
                timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
                filename = f"data_{timestamp}.csv"
                filepath = os.path.join("./", filename)
                df.to_csv(filepath, index=False)
                return f"Result too large ({len(rows)} rows). Saved to {filepath}"

            return df.to_string(index=False)

        except Exception as e:
            logger.exception("Unexpected error during SQL execution")
            return f"Error: {str(e)}"

