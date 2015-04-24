from __future__ import absolute_import, division, print_function, with_statement

import collections
import functools
import itertools
import sys
import types
import weakref
import time

from tornado.concurrent import Future, TracebackFuture, is_future, chain_future
from tornado.ioloop import IOLoop
from tornado.log import app_log
from tornado import stack_context
from tornado.gen import Runner

import time
import collections
import types
import tornado
import sys
import datetime


from tornado.gen import Return
from tornado import stack_context
from tornado.gen import Return, _null_future
from tornado.web import RequestHandler

# Step 1.
# Add this before first import tornado:
#
# from profiletor import TornadoProfiler
# TornadoProfiler.initialize(path_filter=['code/cluster',])


# Step 2.
# Add this profiler handler:
#
# from profiletor import ProfilerHandler
# handlers += [(r'/profiler', ProfilerHandler),]

def coroutine(func, replace_callback=True):
    return make_coroutine_wrapper(func, replace_callback=True)


def engine(func):
    func = make_coroutine_wrapper(func, replace_callback=False)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        future = func(*args, **kwargs)
        def final_callback(future):
            if future.result() is not None:
                raise ReturnValueIgnoredError(
                    "@gen.engine functions cannot return values: %r" %
                    (future.result(),))
        future.add_done_callback(stack_context.wrap(final_callback))
    return wrapper


def make_coroutine_wrapper(func, replace_callback):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        future = TracebackFuture()

        if replace_callback and 'callback' in kwargs:
            callback = kwargs.pop('callback')
            IOLoop.current().add_future(
                future, lambda future: callback(future.result()))

        try:
            with Measure(func):
                result = func(*args, **kwargs)
        except (Return, StopIteration) as e:
            result = getattr(e, 'value', None)
        except Exception:
            future.set_exc_info(sys.exc_info())
            return future
        else:
            if isinstance(result, types.GeneratorType):
                try:
                    orig_stack_contexts = stack_context._state.contexts

                    with Measure(result, first=True):
                        yielded = next(result)

                    if stack_context._state.contexts is not orig_stack_contexts:
                        yielded = TracebackFuture()
                        yielded.set_exception(
                            stack_context.StackContextInconsistentError(
                                'stack_context inconsistency (probably caused '
                                'by yield within a "with StackContext" block)'))
                except (StopIteration, Return) as e:
                    future.set_result(getattr(e, 'value', None))
                except Exception:
                    future.set_exc_info(sys.exc_info())
                else:
                    Runner(result, future, yielded)
                try:
                    return future
                finally:
                    future = None
        future.set_result(result)
        return future
    return wrapper


def Runner__run(self):
    if self.running or self.finished:
        return
    try:
        self.running = True
        while True:
            future = self.future
            if not future.done():
                return
            self.future = None
            try:
                orig_stack_contexts = stack_context._state.contexts
                try:
                    value = future.result()
                except Exception:
                    self.had_exception = True
                    yielded = self.gen.throw(*sys.exc_info())
                else:
                    with Measure(self.gen):
                        yielded = self.gen.send(value)

                if stack_context._state.contexts is not orig_stack_contexts:
                    self.gen.throw(
                        stack_context.StackContextInconsistentError(
                            'stack_context inconsistency (probably caused '
                            'by yield within a "with StackContext" block)'))
            except (StopIteration, Return) as e:
                self.finished = True
                self.future = _null_future
                if self.pending_callbacks and not self.had_exception:
                    raise LeakedCallbackError(
                        "finished without waiting for callbacks %r" %
                        self.pending_callbacks)

                self.result_future.set_result(getattr(e, 'value', None))
                self.result_future = None
                self._deactivate_stack_context()
                return
            except Exception:
                self.finished = True
                self.future = _null_future
                self.result_future.set_exc_info(sys.exc_info())
                self.result_future = None
                self._deactivate_stack_context()
                return
            if not self.handle_yield(yielded):
                return
    finally:
        self.running = False


def tuple_normalize(t):
    return (str(item) for item in t)


class TornadoProfiler(object):
    call_count = collections.defaultdict(int)
    call_time = collections.defaultdict(float)
    last_work_time = collections.defaultdict(float)
    work_time = collections.defaultdict(float)
    path_filter = None

    @classmethod
    def initialize(cls, path_filter):
        tornado.gen.coroutine = coroutine
        tornado.gen.Runner.run = Runner__run
        tornado.gen.engine = engine
        TornadoProfiler.path_filter = path_filter

    @classmethod
    def reset_stats(cls):
        cls.call_count.clear()
        cls.call_time.clear()
        cls.work_time.clear()

    @classmethod
    def max_time(cls, path=None):
        try:
            return max([time for key, time in cls.work_time.iteritems() if path is None or cls.pathes_in_item(path, key[0])])
        except:
            pass
    
    @classmethod
    def coroutine_exec_time_stats(cls, path=None):
        return cls.generate_stats(cls.call_time, path)

    @classmethod
    def coroutine_real_time_stats(cls, path=None):
        return cls.generate_stats(cls.work_time, path)

    @classmethod
    def print_coroutine_exec_time_stats(cls, path=None):
        return cls.print_stats(cls.generate_stats(cls.call_time, path))

    @classmethod
    def print_coroutine_real_time_stats(cls, path=None):
        return cls.print_stats(cls.generate_stats(cls.work_time, path))

    @classmethod
    def pathes_in_item(cls, pathes, item):
        for p in pathes:
            if p in item:
                return True

        return False

    @classmethod
    def generate_stats(cls, statistics, _path=None):
        path = _path if _path else TornadoProfiler.path_filter

        measure_time = cls.max_time(path)
        stats = sorted([(key, time) for key, time in statistics.iteritems()], key=lambda tup: tup[1], reverse=True)
        result = []
        for item in stats:
            key = item[0]
            count = cls.call_count[key]
            if  path is None or cls.pathes_in_item(path, item[0][0]):
                t = (item[1], str(item[1]/measure_time * 100) + "%", count, item[1]/float(count)) + tuple((i for i in item[0]))
                if key in TornadoProfiler.last_work_time:
                    t = t + (str(TornadoProfiler.last_work_time[key]),)

                result.append(t)

        return result

    @classmethod
    def work_time_dict(cls, _path=None):
        statistics = cls.work_time
        path = _path if _path else TornadoProfiler.path_filter

        stats = sorted([(key, time) for key, time in statistics.iteritems()], key=lambda tup: tup[1], reverse=True)
        result = {}
        for item in stats:
            key = item[0]
            count = cls.call_count[key]
            if path is None or cls.pathes_in_item(path, item[0][0]):
                k = '%s::%s::%s' % (item[0][0], item[0][1], item[0][2])
                result[k] = item[1]/float(count)

        return {'profile': result}

    @classmethod
    def print_stats(cls, stats):
        for s in stats:
            print(' '.join((str(item) for item in s)))


class Measure(object):
    current_measurer_stack = collections.defaultdict(int)
    measurer_time = {}

    def __init__(self, f, first=False):
        self.__start_time = time.time() if first else None
        self.__iter_start_time = None
        self.__func = f
        self.__is_gen = isinstance(self.__func, types.GeneratorType)
        self.__name = self.__func.__name__

        if self.__is_gen:
            self.__first_line = self.__func.gi_code.co_firstlineno
            if self.__func.gi_frame:
                self.__start_line = self.__func.gi_frame.f_lineno
            else:
                self.__start_line = self.__first_line

            self.__filename = self.__func.gi_code.co_filename

            if first:
                if self.func_key not in self.measurer_time:
                    self.measurer_time[self.func_key] = self.__start_time

                self.current_measurer_stack[self.func_key] += 1
        else:
            self.__first_line = self.__func.__code__.co_firstlineno
            self.__start_line = 0

            self.__filename = self.__func.__code__.co_filename


    @property
    def filename(self):
        return self.__filename

    @property
    def name(self):
        return self.__name

    @property
    def first_line(self):
        return self.__first_line

    @property
    def start_line(self):
        return self.__start_line

    @property
    def end_line(self):
        if self.__is_gen:
            if self.__func.gi_frame:
                return self.__func.gi_frame.f_lineno
            else:
                return self.__start_line

        return 0

    @property
    def key(self):
        return (self.filename, self.name, self.first_line, self.start_line, self.end_line, self.name)

    @property
    def func_key(self):
        return (self.filename, self.name, self.first_line, self.name)

    @property
    def gen_live_key(self):
        return (self.filename, self.name, self.first_line, 0, 0, self.name)

    def __enter__(self):
        self.__iter_start_time = time.time()
        return self

    def __exit__(self, type, value, traceback):
        iter_time = float(time.time() - self.__iter_start_time)

        key = self.key

        TornadoProfiler.call_count[key] += 1
        TornadoProfiler.call_time[key] += iter_time

        if not (self.__is_gen and (type is StopIteration or type is Return)):
            return

        now = time.time()

        __start_time = self.measurer_time[self.func_key]
        work_time = float(now - __start_time)

        self.current_measurer_stack[self.func_key] -= 1
        TornadoProfiler.work_time[self.gen_live_key] += work_time
        TornadoProfiler.last_work_time[self.gen_live_key] = work_time

        if self.current_measurer_stack[self.func_key] == 0:
            del self.measurer_time[self.func_key]
        else:
            self.measurer_time[self.func_key] = now


class ProfilerHandler(RequestHandler):
    def get(self):
        build_exec = self.get_query_argument('exec', 1)
        build_real = self.get_query_argument('real', 1)
        html = self.get_query_argument('html', 1)
        reset = self.get_query_argument('reset', 0)

        if int(html) == 1:
            result = '<html><head></head><body><h1>Execution time</h1><table>%s</table><h1>Real time</h1><table>%s</table></body></html>'

            stats = TornadoProfiler.coroutine_exec_time_stats()
            exec_time = ''

            if int(build_exec) == 1:
                for s in stats:
                    exec_time += '<tr><td>' + '</td><td>'.join(tuple_normalize(s)) + '</td></tr>'

            stats = TornadoProfiler.coroutine_real_time_stats()
            real_time = ''
            if int(build_real) == 1:
                for s in stats:
                    real_time += '<tr><td>' + '</td><td>'.join(tuple_normalize(s)) + '</td></tr>'

            
            result = result % (exec_time, real_time)
        else:
            result = TornadoProfiler.work_time_dict()

        if int(reset) == 1:
            TornadoProfiler.reset_stats()

        self.write(result)
