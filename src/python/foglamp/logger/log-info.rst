LEVELS
------

- DEBUG 	Detailed information, typically of interest only when diagnosing problems.
- INFO 	Confirmation that things are working as expected.
- WARNING 	An indication that something unexpected happened, or indicative of some problem in the near future (e.g. ‘disk space low’). The software is still working as expected.
- ERROR 	Due to a more serious problem, the software has not been able to perform some function.
- CRITICAL 	A serious error, indicating that the program itself may be unable to continue running.

syslog_handler
--------------
.. code-block:: yaml

   address: /dev/log # /dev/log for Linux; /var/run/syslog for OSX

**In OSX**, you can see syslogs using Console app.

- System Log Queries
- Files > system.log

Log file: `/var/log/system.log`

**In Ubuntu**, you can see syslogs using System Log app.

Log file: `/var/log/syslog`

`tail -f /var/log/syslog` to monitor logs

How to run/ test
----------------

1) `source build.sh -c`
2) delete `src/python/foglamp/foglamp-env.yaml`
3) `source build.sh -i`
4) `python foglamp/logger/log.py` (not using yaml stuff)
5) `python foglamp/logger/log_demo.py`
6) `python foglamp/logger/log_demo2.py`

if you are installing and want to use in API (or run it), make sure to call `make develop` to get `aiohttp_cors` dependency.

**Note:** `setup_logging()` is being called via `load_config()`