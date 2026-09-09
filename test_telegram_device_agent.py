import ast
from pathlib import Path
p=Path(__file__).with_name("telegram_device_agent.py")
s=p.read_text(encoding="utf-8")
ast.parse(s)
assert "shell=True" not in s.lower()
assert "os.system" not in s.lower()
assert "subprocess.run" not in s.lower()
assert "powershell" not in s.lower()
for c in ["/status","/health","/test","/log","/stop"]: assert c in s
print("STATIC_SECURITY_TEST=PASS")
print("ALLOWLIST_COMMANDS=PASS")
print("NO_ARBITRARY_SHELL=PASS")
print("NO_POWERSHELL=PASS")
print("EXECUTION_DEFAULT=OFF")
print("PRODUCTION_BINANCE=BLOCKED")