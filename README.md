# profiletor
tornado profiler, compatible versions: 4.0, 4.1

*Step 1.*
Add this before first import tornado::

    from profiletor import TornadoProfiler
    TornadoProfiler.initialize(path_filter=['code/cluster',])


*Step 2.*
Add this profiler handler::

    from profiletor import ProfilerHandler
    handlers += [(r'/profiler', ProfilerHandler),]

