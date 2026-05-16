import os
import subprocess

cmd = ["/home/silpc-064/Desktop/CallQ/venv/bin/python", "manage.py", "migrate", "configdetails", "--noinput"]
result = subprocess.run(cmd, cwd="/home/silpc-064/Desktop/CallQ/CallQ", capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RETURN CODE:", result.returncode)
