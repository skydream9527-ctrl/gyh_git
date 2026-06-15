#!/usr/bin/env python3
"""
SQL Query Tool for DataWorks
A command-line interface for executing SQL queries against Xiaomi DataWorks.

Usage:
    python sql_query_tool.py "SELECT * FROM table LIMIT 10"
    python sql_query_tool.py --file query.sql
    python sql_query_tool.py --host zjyprc "SELECT * FROM table"

Environment Variables:
    DATAWORKS_TOKEN_ID: Your DataWorks token ID (required)
    DATAWORKS_HOST: Default host (optional, defaults to zjyprc)
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Add the skills directory to Python path
sys.path.insert(0, str(Path(__file__).parent / ".micode" / "skills" / "sql" / "scripts"))

from run_sql import DataWorks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
    else:
        logger.warning(f".env file not found at {env_path}")


def load_sql_from_file(file_path: str) -> str:
    """Load SQL from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"SQL file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading SQL file: {e}")


def validate_environment() -> bool:
    """Validate that required environment variables are set."""
    token_id = os.environ.get("DATAWORKS_TOKEN_ID")
    if not token_id:
        logger.error("DATAWORKS_TOKEN_ID environment variable is not set")
        logger.info("Please set it in .env file or use: export DATAWORKS_TOKEN_ID=your_token_id")
        return False
    return True


def get_token_from_env() -> Optional[str]:
    """Get token from environment variables."""
    return os.environ.get("DATAWORKS_TOKEN_ID")


def list_available_hosts():
    """List all available hosts."""
    dataworks = DataWorks()
    hosts = dataworks.list_hosts()
    print("\nAvailable hosts:")
    print("-" * 50)
    for key, value in hosts.items():
        print(f"{key:20} -> {value}")
    print("-" * 50)


def main():
    # Load environment variables from .env file
    load_env_file()

    parser = argparse.ArgumentParser(
        description="SQL Query Tool for DataWorks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute a simple query
  python sql_query_tool.py "SELECT * FROM table LIMIT 10"

  # Execute SQL from file
  python sql_query_tool.py --file query.sql

  # Specify host explicitly
  python sql_query_tool.py --host zjyprc "SELECT * FROM table"

  # List available hosts
  python sql_query_tool.py --list-hosts

Environment Variables:
  DATAWORKS_TOKEN_ID: Your DataWorks token ID (required, can be in .env file)
  DATAWORKS_HOST: Default host (optional)
        """
    )

    parser.add_argument(
        'sql',
        nargs='?',
        help='SQL query to execute'
    )

    parser.add_argument(
        '--host',
        help='Specific host to use (overrides auto-detection)'
    )

    parser.add_argument(
        '--list-hosts',
        action='store_true',
        help='List all available hosts'
    )

    args = parser.parse_args()

    # Handle list-hosts command
    if args.list_hosts:
        list_available_hosts()
        return

    sql = args.sql
    # Get token from environment
    token_id = get_token_from_env()

    try:
        # Pass token_id to DataWorks constructor
        dataworks = DataWorks(token_id=token_id, host=args.host)

        # Execute SQL
        logger.info("Executing SQL query...")
        result = dataworks.execute_sql(sql)

        # Print result
        print("\n" + "="*80)
        print("QUERY RESULT:")
        print("="*80)
        print(result)
        print("="*80)

    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()