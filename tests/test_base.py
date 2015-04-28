import time

from profiletor import TornadoProfiler
TornadoProfiler.initialize(path_filter=[])

from tornado.testing import AsyncTestCase, gen_test
from tornado.gen import coroutine, Task, Return
from tornado.ioloop import IOLoop


SLEEP_TIME = 0.01
PLACES = 2
ITERATIONS = 10


class TestBasicUsage(AsyncTestCase):
    def setUp(self):
        TornadoProfiler.reset_stats()
        super(TestBasicUsage, self).setUp()

    @gen_test
    def test_measure(self):
        @coroutine
        def measuring_coroutine():
            yield Task(IOLoop.current().add_timeout, time.time() + SLEEP_TIME)

        for i in xrange(1, ITERATIONS + 1):
            yield measuring_coroutine()

            real_time = TornadoProfiler.coroutine_real_time_stats([''])
            self.assertEqual(len(real_time), 2)

            measure = real_time[0]

            self.assertAlmostEqual(measure[0], SLEEP_TIME * i, PLACES)
            self.assertEqual(measure[1], '100.0%')
            self.assertEqual(measure[2], i)
            self.assertAlmostEqual(measure[3], SLEEP_TIME, PLACES)
            self.assertEqual(measure[4], 'tests/test_base.py')
            self.assertEqual(measure[5], 'measuring_coroutine')

    @gen_test
    def test_return(self):
        @coroutine
        def returning_coroutine():
            yield Task(IOLoop.current().add_timeout, time.time() + SLEEP_TIME)
            raise Return(0)

        for i in xrange(1, ITERATIONS + 1):
            yield returning_coroutine()

            real_time = TornadoProfiler.coroutine_real_time_stats([''])
            self.assertEqual(len(real_time), 2)

            measure = real_time[0]

            self.assertAlmostEqual(measure[0], SLEEP_TIME * i, PLACES)
            self.assertEqual(measure[1], '100.0%')
            self.assertEqual(measure[2], i)
            self.assertAlmostEqual(measure[3], SLEEP_TIME, PLACES)
            self.assertEqual(measure[4], 'tests/test_base.py')
            self.assertEqual(measure[5], 'returning_coroutine')

    @gen_test
    def test_array_and_return(self):
        @coroutine
        def child_coroutine():
            time.sleep(SLEEP_TIME)
            yield Task(IOLoop.current().add_timeout, time.time() + SLEEP_TIME)
            raise Return(0)

        @coroutine
        def parent_coroutine():
            result = yield [child_coroutine(), child_coroutine()]
            raise Return(result)

        for i in xrange(1, ITERATIONS + 1):
            result = yield parent_coroutine()
            self.assertEqual(result, [0, 0])

            real_time = TornadoProfiler.coroutine_real_time_stats([''])
            self.assertEqual(len(real_time), 3)

            parent_measure = real_time[0]
            child_measure = real_time[1]

            self.assertAlmostEqual(parent_measure[0], child_measure[0], PLACES)
            self.assertGreater(parent_measure[0], child_measure[0])
            self.assertEqual(parent_measure[1], '100.0%')

            self.assertEqual(parent_measure[2], i)
            self.assertAlmostEqual(parent_measure[3], SLEEP_TIME * 3, PLACES)
            self.assertEqual(parent_measure[4], 'tests/test_base.py')
            self.assertEqual(parent_measure[5], 'parent_coroutine')

            self.assertEqual(child_measure[2], i * 2)
            self.assertAlmostEqual(child_measure[3], SLEEP_TIME * 3 / 2, PLACES)
            self.assertEqual(child_measure[4], 'tests/test_base.py')
            self.assertEqual(child_measure[5], 'child_coroutine')

    @gen_test
    def test_non_gen(self):
        @coroutine
        def not_gen():
            time.sleep(SLEEP_TIME)
            raise Return(0)

        for i in xrange(1, ITERATIONS + 1):
            yield not_gen()

            real_time = TornadoProfiler.coroutine_real_time_stats([''])
            self.assertEqual(len(real_time), 2)

            measure = real_time[0]

            self.assertAlmostEqual(measure[0], SLEEP_TIME * i, PLACES)
            self.assertEqual(measure[1], '100.0%')
            self.assertEqual(measure[2], i)
            self.assertAlmostEqual(measure[3], SLEEP_TIME, PLACES)
            self.assertEqual(measure[4], 'tests/test_base.py')
            self.assertEqual(measure[5], 'not_gen')

    @gen_test
    def test_nested_measure(self):
        @coroutine
        def child_coroutine():
            yield Task(IOLoop.current().add_timeout, time.time() + SLEEP_TIME)

        @coroutine
        def parent_coroutine():
            yield child_coroutine()

        for i in xrange(1, ITERATIONS + 1):
            yield parent_coroutine()

            real_time = TornadoProfiler.coroutine_real_time_stats([''])
            self.assertEqual(len(real_time), 3)

            parent_measure = real_time[0]
            child_measure = real_time[1]

            self.assertAlmostEqual(parent_measure[0], child_measure[0], PLACES)
            self.assertGreater(parent_measure[0], child_measure[0])
            self.assertEqual(parent_measure[1], '100.0%')

            self.assertEqual(parent_measure[2], i)
            self.assertAlmostEqual(parent_measure[3], SLEEP_TIME, PLACES)
            self.assertEqual(parent_measure[4], 'tests/test_base.py')
            self.assertEqual(parent_measure[5], 'parent_coroutine')

            self.assertEqual(child_measure[2], i)
            self.assertAlmostEqual(child_measure[3], SLEEP_TIME, PLACES)
            self.assertEqual(child_measure[4], 'tests/test_base.py')
            self.assertEqual(child_measure[5], 'child_coroutine')

    @gen_test
    def test_blocking_nested_measure(self):
        @coroutine
        def child_coroutine():
            time.sleep(SLEEP_TIME)
            yield Task(IOLoop.current().add_timeout, time.time() + SLEEP_TIME)

        @coroutine
        def parent_coroutine():
            yield child_coroutine()

        for i in xrange(1, ITERATIONS + 1):
            yield parent_coroutine()

            real_time = TornadoProfiler.coroutine_real_time_stats([''])
            self.assertEqual(len(real_time), 3)

            parent_measure = real_time[0]
            child_measure = real_time[1]

            self.assertAlmostEqual(parent_measure[0], child_measure[0], PLACES)
            self.assertGreater(parent_measure[0], child_measure[0])
            self.assertEqual(parent_measure[1], '100.0%')

            self.assertEqual(parent_measure[2], i)
            self.assertAlmostEqual(parent_measure[3], SLEEP_TIME * 2, PLACES)
            self.assertEqual(parent_measure[4], 'tests/test_base.py')
            self.assertEqual(parent_measure[5], 'parent_coroutine')

            self.assertEqual(child_measure[2], i)
            self.assertAlmostEqual(child_measure[3], SLEEP_TIME * 2, PLACES)
            self.assertEqual(child_measure[4], 'tests/test_base.py')
            self.assertEqual(child_measure[5], 'child_coroutine')

            exec_time = TornadoProfiler.coroutine_exec_time_stats([''])

            count_of_slow = 0
            slow_measure = None

            for measure in exec_time:
                if abs(measure[0] - (SLEEP_TIME * i)) < SLEEP_TIME/5:
                    count_of_slow += 1
                    slow_measure = measure

            self.assertEqual(count_of_slow, 1)

            self.assertAlmostEqual(slow_measure[0], SLEEP_TIME * i, PLACES)
            self.assertEqual(slow_measure[2], i)
            self.assertAlmostEqual(slow_measure[3], SLEEP_TIME, PLACES)
            self.assertEqual(slow_measure[4], 'tests/test_base.py')
            self.assertEqual(slow_measure[5], 'child_coroutine')
