import inspect
import os
import os.path
import re
import unittest
from types import FunctionType
from typing import Dict, Optional, Set, Tuple


class TestTrioTests(unittest.TestCase):
    def runTest(self):
        # get files
        trio_tests: Dict[str, Tuple[str, Optional[FunctionType]]] = {
            os.path.splitext(f)[0]: (f, None)
            for f in os.listdir("tests")
            if re.match(r"^trio.*.py", f)
        }

        # must import outside top-level to avoid running test twice
        from test_flake8_trio import Flake8TrioTestCase

        # get functions
        for o in inspect.getmembers(Flake8TrioTestCase):
            if inspect.isfunction(o[1]) and re.match(r"^test_trio\d\d\d", o[0]):
                key = o[0][5:]

                self.assertIn(key, trio_tests)
                self.assertIsNone(trio_tests[key][1], msg=key)

                trio_tests[key] = (trio_tests[key][0], o[1])

        for test, (filename, func) in sorted(trio_tests.items()):
            self.assertIsNotNone(func, msg=test)
            assert func is not None  # for type checkers

            with open(os.path.join("tests", filename), encoding="utf-8") as file:
                file_error_lines = {
                    lineno + 1
                    for lineno, line in enumerate(file)
                    if re.search(r"# *error", line, flags=re.I)
                }

            func_error_lines: Set[int] = set()
            for line in inspect.getsourcelines(func)[0]:
                m = re.search(r"(?<=make_error\(TRIO\d\d\d, )\d*", line)
                if not m:
                    continue
                lineno = int(m.group())
                self.assertNotIn(lineno, func_error_lines, msg=test)
                func_error_lines.add(lineno)

            self.assertSequenceEqual(
                sorted(file_error_lines), sorted(func_error_lines), msg=test
            )
