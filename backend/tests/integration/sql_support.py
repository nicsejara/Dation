"""Fresh app schema from captured production DDL, in an owned disposable database."""
import os
from pathlib import Path
import subprocess
from uuid import uuid4

REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO/'supabase/baseline/20261010100000_public_schema.sql'
BASELINE_VERSION = '20261010100000'
CONTAINER = os.getenv('DATION_SQL_TEST_CONTAINER')


class SQLSandbox:
    @classmethod
    def command(cls, sql, database=None, check=True):
        result=subprocess.run(['docker','exec','-i',CONTAINER,'psql','-U','postgres',
            '-d',database or cls.database,'-X','-A','-t','-v','ON_ERROR_STOP=1'],
            input=sql,text=True,capture_output=True)
        if check and result.returncode:
            raise AssertionError(result.stderr)
        return result

    @classmethod
    def setUpClass(cls):
        cls.database='dation_qa_'+uuid4().hex
        cls.command('CREATE DATABASE '+cls.database+';',database='postgres')
        cls.command((Path(__file__).parent/'infrastructure.sql').read_text())
        cls.command(BASELINE.read_text())
        cls.upgrade()

    @classmethod
    def upgrade(cls, database=None):
        for migration in sorted((REPO/'supabase/migrations').glob('*.sql')):
            if BASELINE_VERSION < migration.name[:14] < '20261018090000':
                cls.command(migration.read_text(),database=database)

    @classmethod
    def tearDownClass(cls):
        cls.command('DROP DATABASE '+cls.database+';',database='postgres')
