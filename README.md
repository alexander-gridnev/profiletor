# profiletor
**Profiletor** measures tornado coroutines timings. You can't measure execution time with regular profilers, because asyncronouse nature of **tornado**. Compatible tornado versions: 4.0, 4.1. 

*Step 1.*
Add this before first import tornado:

    from profiletor import TornadoProfiler
    # path_fitler - prefix of path with source files
    TornadoProfiler.initialize(path_filter=['code/cluster',])


*Step 2.*
Add this profiler handler:

    from profiletor import ProfilerHandler
    
    # Add this handler to your app
    handlers += [(r'/profiler', ProfilerHandler),]

