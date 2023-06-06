#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/3/24 13:08
# @Author : 谈林海
import allure
import pytest
from _pytest.assertion.util import assertrepr_compare

from utils import *
from utils.database_process.database_control import MysqlDB
from utils.read_file_process.read_yaml_control import HandleYaml
from utils.data_process.params_replace_control import DataHandler, Config
from utils.requests_process.requests_control import RestClient


def pytest_generate_tests(metafunc):
    """参数化测试函数"""

    test_cases = []
    markers = metafunc.definition.own_markers
    for marker in markers:
        if marker.name == 'datafile':
            test_data_path = Path(metafunc.config.rootdir) / marker.args[0] if marker.args else logger.error(
                'yaml测试文件路径拼接失败，请检查')
            test_data = HandleYaml(test_data_path).read_yaml()
            for data in test_data['tests']:
                if data['inputs'].get('file', {}):
                    data['inputs']['file'] = {'file': (
                        data['inputs']['file'], open(root / f"files/{data['inputs']['file']}", 'rb'),
                        'application/json')}
                test_case = {
                    'case': data.get('case', {}),
                    'env': (str(config.host) + str(test_data['common_inputs'].get('path', {})),
                            str(test_data['common_inputs'].get('method', ''))),
                    'inputs': data.get('inputs', {}),
                    'expectation': data.get('expectation', {})
                }
                test_cases.append(test_case)
            metafunc.parametrize(
                "env, case, inputs, expectation",
                [(tc['env'], tc['case'], tc['inputs'], tc['expectation']) for tc in test_cases],
                scope='function'
            )


@pytest.fixture(scope='function', autouse=True)
def alert_inputs(request):
    """替换inputs中的参数化数据"""

    if 'inputs' in request.fixturenames:
        inputs = request.getfixturevalue('inputs')
        if inputs.get('json'):
            DataHandler(config=Config()).replace_values(inputs['json'])
        else:
            DataHandler(config=Config()).replace_values(inputs['params'])


def pytest_assertrepr_compare(config, op, left, right):
    """处理断言内省"""

    left_name, right_name = left, right
    pytest_output = assertrepr_compare(config, op, left, right)
    # logger.debug(f"{left_name} is {left}")
    # logger.debug(f"{right_name} is {right}")
    with allure.step(f"断言: {left_name} {op} {right_name}"):
        allure.attach(f"{left_name}", "输入结果")
        allure.attach(f"{op}", "判断条件")
        allure.attach(f"{right_name}", "预期结果")
    return pytest_output


def pytest_collection_modifyitems(items):
    """处理收集的测试用例"""

    for item in items:
        item.name = item.name.encode("utf-8").decode("unicode_escape")
        item._nodeid = item.nodeid.encode("utf-8").decode("unicode_escape")

        _marks = Path(item.fspath).resolve().parts[-2]  # 测试用例对应模块
        if item.get_closest_marker(name=f'{_marks}') is None:
            item.add_marker(eval(f"pytest.mark.{_marks}"))


@pytest.fixture(autouse=True)
def collection():
    class Core:
        def __init__(self):
            self.requests = RestClient()
            self.headers = RestClient().headers()
            self.cache = HandleYaml(root / 'test_data/cache.yaml')
            self.mysql = MysqlDB() if config.mysql_db.switch else logger.warning('当前数据库配置: 关闭')

    yield Core()


@pytest.fixture()
def core(collection):
    yield collection


