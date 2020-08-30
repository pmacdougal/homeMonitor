# homeMonitor
home automation monitoring script

You will likely encounter this error:
```
Traceback (most recent call last):
  File "main.py", line 1, in <module>
    from monitor import Monitor
  File "/home/pi/homeMonitor/monitor.py", line 11, in <module>    
    from private import password
ModuleNotFoundError: No module named 'private'
```

This is because I have not added the file private.py.  You should create it.  It is one line with your AdaFruit IO access key in it:
```python
password = "xxxxxxxxxxxxxxxxxxxxxxxxxxx"
```
