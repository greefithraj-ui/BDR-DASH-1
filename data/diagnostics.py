import json
import os
import re
import time
import datetime
from pathlib import Path

import paramiko

_PARENT = Path(__file__).resolve().parent.parent
MACHINES_FILE = _PARENT / "machines.json"
AUTH_PASSWORD = os.environ.get("AQC_PASSWORD", "1234")

MCP_ADDRS = {1: 0x20, 2: 0x21, 3: 0x22, 4: 0x23, 5: 0x24, 6: 0x25, 7: 0x26, 8: 0x27}
GPIOB_REG = 0x13
IODIRA_REG = 0x00
IODIRB_REG = 0x01
GPIOA_REG = 0x12
OLATA_REG = 0x14
GPPUB_REG = 0x0D


def _load_machine_config(machine_name):
    with open(MACHINES_FILE) as f:
        config = json.load(f)
    def normalize(name):
        return name.strip().lower().replace("_", "-").replace(" ", "-")
    requested = normalize(machine_name)
    for m in config.get("machines", []):
        if normalize(m.get("name", "")) == requested:
            return m
    return None


def _ssh_connect(machine_config, timeout=10):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=machine_config["ip"],
        username=machine_config["user"],
        password=AUTH_PASSWORD,
        timeout=timeout,
        banner_timeout=timeout,
        auth_timeout=timeout,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def _exec(client, command, timeout=30):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_code, out, err


def _exec_script(client, script, timeout=30, use_venv=False):
    base = "cd ~/auto-dfu-tool && .venv/bin/python3" if use_venv else "python3"
    escaped = script.replace("'", "'\"'\"'")
    cmd = f"""{base} -c '{escaped}'"""
    return _exec(client, cmd, timeout=timeout)


def _exec_python(client, script, timeout=60):
    command = "python3 - <<'PY'\n" + script.rstrip() + "\nPY"
    return _exec(client, command, timeout=timeout)


def _exec_project_python(client, user, script, timeout=60):
    root = f"/home/{user}/auto-dfu-tool"
    py = f"{root}/.venv/bin/python3"
    command = (
        f"cd {_sh_quote(root)} 2>/dev/null || true; "
        f"PYTHONPATH={_sh_quote(root)} "
        f"$(test -x {_sh_quote(py)} && printf %s {_sh_quote(py)} || printf %s python3) "
        "<<'PY'\n"
        + script.rstrip()
        + "\nPY"
    )
    return _exec(client, command, timeout=timeout)


def _sh_quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _build_bus_detect_script(expected_addrs=None):
    if expected_addrs is None:
        expected_addrs = {1: "0x20", 2: "0x21", 3: "0x22", 4: "0x23", 5: "0x24", 6: "0x25", 7: "0x26", 8: "0x27"}
    addr_list = ", ".join(expected_addrs.values())
    return f"""
import json
expected = {{{', '.join(f'{k}:{v}' for k, v in expected_addrs.items())}}}
try:
    import smbus
    SMBus = smbus.SMBus
except Exception:
    try:
        from smbus2 import SMBus
    except Exception as exc:
        print(json.dumps({{"ok": False, "error": "SMBus import failed: %s" % exc}}))
        raise SystemExit(0)

def open_best_bus():
    best = None
    best_count = -1
    errors = {{}}
    for bus_num in [1, 13, 14]:
        try:
            bus = SMBus(bus_num)
            count = 0
            for addr in expected.values():
                try:
                    bus.read_byte(addr)
                    count += 1
                except Exception:
                    pass
            if count > best_count:
                if best is not None:
                    try:
                        best[1].close()
                    except Exception:
                        pass
                best = (bus_num, bus)
                best_count = count
            else:
                try:
                    bus.close()
                except Exception:
                    pass
        except Exception as exc:
            errors[str(bus_num)] = str(exc)
    if best is None:
        print(json.dumps({{"ok": False, "error": "No I2C bus could be opened", "bus_errors": errors}}))
        raise SystemExit(0)
    return best[0], best[1], best_count, errors

bus_num, bus, detected_count, bus_errors = open_best_bus()
"""


def check_connection(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found in config"}
    try:
        client = _ssh_connect(machine, timeout=5)
        code, out, err = _exec(client, "hostname")
        client.close()
        if code == 0:
            return {"ok": True, "hostname": out, "machine": machine["name"], "ip": machine["ip"]}
        return {"ok": False, "error": err or "SSH connected but command failed", "hostname": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def button_scan(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        bus_detect = _build_bus_detect_script()
        script = bus_detect + r"""
result = {}
pressed_count = 0
for mcp, addr in expected.items():
    try:
        gpio = bus.read_byte_data(addr, 0x13)
        iodirb = bus.read_byte_data(addr, 0x01)
        gppub = bus.read_byte_data(addr, 0x0D)
        result[str(mcp)] = {'gpio': gpio, 'iodirb': iodirb, 'gppub': gppub, 'addr': hex(addr)}
    except Exception as e:
        result[str(mcp)] = {'error': str(e), 'addr': hex(addr)}
print(json.dumps({"ok": True, "bus": bus_num, "detected_count": detected_count, "result": result}))
"""
        code, out, err = _exec_script(client, script)
        client.close()
        if code != 0:
            return {"ok": False, "error": err or "Script failed", "raw_out": out}

        parsed = json.loads(out)
        bus_info = parsed.get("bus", 1)
        detected_count = parsed.get("detected_count", 0)
        raw_result = parsed.get("result", parsed)

        grid = []
        for mcp_num in range(1, 9):
            key = str(mcp_num)
            row = []
            mcp_data = raw_result.get(key, {})
            if "error" in mcp_data:
                for b in range(8):
                    row.append({"location": (mcp_num - 1) * 8 + b + 1, "state": "error", "error": mcp_data["error"]})
            else:
                gpio_val = mcp_data.get("gpio", 0xFF)
                for b in range(8):
                    loc = (mcp_num - 1) * 8 + b + 1
                    pressed = not bool((gpio_val >> b) & 1)
                    row.append({"location": loc, "state": "pressed" if pressed else "released", "raw_bit": b, "gpio": gpio_val})
            grid.append(row)

        return {
            "ok": True,
            "bus": bus_info,
            "detected_count": detected_count,
            "grid": grid,
            "raw": raw_result,
            "pressed_count": sum(1 for row in grid for cell in row if cell["state"] == "pressed"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def read_location(machine_name, location):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    if location < 1 or location > 64:
        return {"ok": False, "error": "Location must be 1-64"}
    try:
        mcp_num = (location - 1) // 8 + 1
        bit = (location - 1) % 8
        addr = MCP_ADDRS[mcp_num]
        client = _ssh_connect(machine)
        bus_detect = _build_bus_detect_script()
        script = bus_detect + f"""
addr = {addr}
try:
    gpio = bus.read_byte_data(addr, 0x13)
    iodirb = bus.read_byte_data(addr, 0x01)
    gppub = bus.read_byte_data(addr, 0x0D)
    iodira = bus.read_byte_data(addr, 0x00)
    gpioa = bus.read_byte_data(addr, 0x12)
    import json; print(json.dumps({{"gpio":gpio,"iodirb":iodirb,"gppub":gppub,"iodira":iodira,"gpioa":gpioa,"bus":bus_num}}))
except Exception as e:
    import json; print(json.dumps({{"error":str(e)}}))
"""
        code, out, err = _exec_script(client, script)
        client.close()
        if code != 0:
            return {"ok": False, "error": err or "Script failed"}
        parsed = json.loads(out)
        if "error" in parsed:
            return {"ok": False, "error": parsed["error"]}
        gpio = parsed.get("gpio", 0xFF)
        pressed = not bool((gpio >> bit) & 1)
        return {
            "ok": True,
            "location": location,
            "mcp": mcp_num,
            "bit": bit,
            "state": "pressed" if pressed else "released",
            "registers": parsed,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def led_control(machine_name, action, **kwargs):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    valid_actions = {"fill", "set", "test", "walk", "chain", "init", "off", "restore", "diagnose"}
    if action not in valid_actions:
        return {"ok": False, "error": f"Action must be one of: {', '.join(sorted(valid_actions))}"}
    try:
        remote_home = f"/home/{machine['user']}"
        deep = kwargs.get("deep", False)
        script_content = r"""
import sys, json, time
sys.path.insert(0, '""" + remote_home + r"""/auto-dfu-tool')
try:
    from utils.pi5neo_mock import Pi5Neo
except Exception:
    from pi5neo import Pi5Neo
strip = Pi5Neo('/dev/spidev0.0', 64, 800)
COLORS = {'red':(255,0,0),'green':(0,255,0),'blue':(0,0,255),'yellow':(255,255,0),'white':(255,255,255),'off':(0,0,0),'purple':(128,0,128),'cyan':(0,255,255),'orange':(255,165,0),'pink':(255,192,203)}
STATE_COLORS = {
    'IDLE': (0,0,255), 'ASSIGNED': (255,255,0), 'QUEUED': (255,255,0),
    'CONNECTING': (255,255,0), 'TESTING': (255,255,0), 'CDT_RUNNING': (255,255,0),
    'BDR_RUNNING': (255,255,0), 'COMPLETING': (255,255,0), 'ABORTING': (255,255,0),
    'PASSED': (0,255,0), 'FAILED': (255,0,0), 'FAILED_FINAL': (255,0,0),
}
BRIGHTNESS = 30
import os as _os
for env_key in ['LED_BRIGHTNESS']:
    try:
        v = int(_os.environ.get(env_key, '30'))
        if 0 <= v <= 255: BRIGHTNESS = v
    except: pass
for env_path in [r'""" + remote_home + r"""/auto-dfu-tool/config.env', r'""" + remote_home + r"""/auto-dfu-tool/.env']:
    try:
        from pathlib import Path as _P
        if _P(env_path).exists():
            for raw in _P(env_path).read_text().splitlines():
                line = raw.strip()
                if line.startswith('LED_BRIGHTNESS') and '=' in line:
                    v = int(line.split('=', 1)[1].strip().strip('"').strip("'"))
                    if 0 <= v <= 255: BRIGHTNESS = v
    except: pass

def scale(rgb):
    return tuple(int(max(0, min(255, v)) * BRIGHTNESS / 255) for v in rgb)

def restore_configured():
    from pathlib import Path as _P
    states = {}
    for rel in ['assembly_test_app/rings_config.json', 'assembly_test_app/bdr_session.json']:
        p = _P(r'""" + remote_home + r"""/auto-dfu-tool') / rel
        if p.exists():
            try:
                data = json.loads(p.read_text())
                slots = data.get('slots') if isinstance(data.get('slots'), dict) else data
                if isinstance(slots, dict):
                    for k, v in slots.items():
                        try:
                            loc = int(k)
                            if 1 <= loc <= 64 and isinstance(v, dict):
                                states[loc] = str(v.get('state') or 'IDLE').upper()
                        except: pass
            except: pass
    restored = []
    for loc in range(1, 65):
        s = states.get(loc, 'IDLE')
        rgb = scale(STATE_COLORS.get(s, (0,0,255)))
        strip.set_led_color(loc - 1, *rgb)
        restored.append({"location": loc, "state": s, "rgb": rgb})
    strip.update_strip()
    return restored, BRIGHTNESS
"""
        if action == "fill":
            color = kwargs.get("color", "blue")
            if color in {"red", "green", "blue", "yellow", "white", "off", "purple", "cyan", "orange", "pink"}:
                r, g, b = {"red":(255,0,0),"green":(0,255,0),"blue":(0,0,255),"yellow":(255,255,0),"white":(255,255,255),"off":(0,0,0),"purple":(128,0,128),"cyan":(0,255,255),"orange":(255,165,0),"pink":(255,192,203)}[color]
            else:
                r, g, b = kwargs.get("r", 0), kwargs.get("g", 0), kwargs.get("b", 255)
            script_content += f"""
strip.fill_strip({r},{g},{b}); strip.update_strip()
print(json.dumps({{"ok":true,"action":"fill","color":"{color}","r":{r},"g":{g},"b":{b}}}))
"""
        elif action == "set":
            slot = int(kwargs.get("slot", 1))
            if slot < 1 or slot > 64:
                return {"ok": False, "error": "Slot must be 1-64"}
            color = kwargs.get("color", "red")
            if color in {"red","green","blue","yellow","white","off","purple","cyan","orange","pink"}:
                r, g, b = {"red":(255,0,0),"green":(0,255,0),"blue":(0,0,255),"yellow":(255,255,0),"white":(255,255,255),"off":(0,0,0),"purple":(128,0,128),"cyan":(0,255,255),"orange":(255,165,0),"pink":(255,192,203)}[color]
            else:
                r, g, b = kwargs.get("r", 255), kwargs.get("g", 0), kwargs.get("b", 0)
            script_content += f"""
strip.set_led_color({slot-1},{r},{g},{b}); strip.update_strip()
print(json.dumps({{"ok":true,"action":"set","slot":{slot},"color":"{color}","r":{r},"g":{g},"b":{b}}}))
"""
        elif action == "test":
            script_content += r"""
seq = [('red',255,0,0),('green',0,255,0),('blue',0,0,255),('yellow',255,255,0),('white',255,255,255),('off',0,0,0)]
for name,r,g,b in seq:
    strip.fill_strip(r,g,b); strip.update_strip(); print(json.dumps({"step":name,"r":r,"g":g,"b":b}),flush=True); time.sleep(1.5)
strip.fill_strip(0,0,0); strip.update_strip()
print(json.dumps({"ok":true,"action":"test","done":true}))
"""
        elif action == "walk":
            color = kwargs.get("color", "white")
            if color in {"red","green","blue","yellow","white","off","purple","cyan","orange","pink"}:
                r, g, b = {"red":(255,0,0),"green":(0,255,0),"blue":(0,0,255),"yellow":(255,255,0),"white":(255,255,255),"off":(0,0,0),"purple":(128,0,128),"cyan":(0,255,255),"orange":(255,165,0),"pink":(255,192,203)}[color]
            else:
                r, g, b = kwargs.get("r", 255), kwargs.get("g", 255), kwargs.get("b", 255)
            delay = kwargs.get("delay", 0.15)
            script_content += f"""
for i in range(64):
    strip.set_led_color(i,{r},{g},{b}); strip.update_strip(); time.sleep({delay})
for i in range(64):
    strip.set_led_color(i,0,0,0); strip.update_strip(); time.sleep({delay})
print(json.dumps({{"ok":true,"action":"walk","color":"{color}"}}))
"""
        elif action == "chain":
            script_content += r"""
results = []
for i in range(64):
    strip.fill_strip(0,0,0); strip.set_led_color(i,255,0,0); strip.update_strip()
    results.append({"led":i+1,"lit":True})
    time.sleep(0.25)
strip.fill_strip(0,0,0); strip.update_strip()
print(json.dumps({"ok":true,"action":"chain","results":results}))
"""
        elif action == "init":
            script_content += r"""
strip.fill_strip(0,0,255); strip.update_strip()
print(json.dumps({"ok":true,"action":"init","message":"LED strip initialized (blue)"}))
"""
        elif action == "off":
            script_content += r"""
strip.fill_strip(0,0,0); strip.update_strip()
print(json.dumps({"ok":true,"action":"off","message":"All LEDs off"}))
"""
        elif action == "restore":
            script_content += r"""
restored, brightness = restore_configured()
print(json.dumps({"ok":True,"action":"restore","brightness":brightness,"restored_slots":[i for i in restored if i["state"]!="IDLE"]}))
"""
        elif action == "diagnose":
            deep_flag = "True" if deep else "False"
            script_content += f"""
result = {{"ok": True, "steps": [], "action": "diagnose"}}
try:
    restored, brightness = restore_configured()
    result["steps"].append({{"name": "restore-start", "state": "ok"}})
    result["brightness"] = brightness
    time.sleep(0.4)
    strip.fill_strip(0,0,0); strip.update_strip()
    result["steps"].append({{"name": "off", "state": "ok"}})
    if {deep_flag}:
        for name, rgb in [("red",(255,0,0)),("green",(0,255,0)),("blue",(0,0,255)),("off",(0,0,0))]:
            strip.fill_strip(*rgb); strip.update_strip()
            result["steps"].append({{"name": name, "state": "ok"}})
            time.sleep(0.25)
    restored, brightness = restore_configured()
    result["steps"].append({{"name": "restore-end", "state": "ok"}})
    result["restored_slots"] = [i for i in restored if i["state"] != "IDLE"]
    print(json.dumps(result))
except Exception as exc:
    result["ok"] = False
    result["error"] = str(exc)
    print(json.dumps(result))
"""
        cmd = f"cd ~/auto-dfu-tool && .venv/bin/python3 -c '{script_content.replace(chr(39), chr(39)+chr(34)+chr(39)+chr(34)+chr(39))}'"
        client = _ssh_connect(machine, timeout=15)
        if action in ("test", "walk", "chain"):
            code, out, err = _exec(client, cmd, timeout=120)
        else:
            code, out, err = _exec(client, cmd, timeout=30)
        client.close()
        if not out.strip():
            return {"ok": False, "error": err or "No output from LED script"}
        try:
            result = json.loads(out.strip().split("\n")[-1])
            return result
        except (json.JSONDecodeError, IndexError):
            return {"ok": True, "action": action, "raw": out, "note": "Raw output (non-JSON)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def full_diagnostics(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        results = {}

        code, out, err = _exec(client, "hostname; uptime; uname -a")
        results["system"] = {"hostname": "", "uptime": "", "kernel": ""}
        for line in out.split("\n"):
            if line and not results["system"]["hostname"]:
                results["system"]["hostname"] = line

        code, out, err = _exec(client, "free -h | head -2")
        results["memory"] = out

        code, out, err = _exec(client, "df -h / | tail -1")
        results["disk"] = out

        code, out, err = _exec(client, "ps aux | grep -iE '(assembly|device_daemon|mcp|button)' | grep -v grep || echo 'None'")
        results["processes"] = out.split("\n") if out and out != "None" else []

        detect_script = r"""
import smbus, json
i2c = smbus.SMBus(1)
expected = {1:0x20,2:0x21,3:0x22,4:0x23,5:0x24,6:0x25,7:0x26,8:0x27}
found = []
for addr in range(0x08, 0x78):
    try:
        i2c.read_byte(addr)
        found.append(addr)
    except: pass
result = {}
for mcp, addr in expected.items():
    if addr in found:
        result[str(mcp)] = {"addr": hex(addr), "status": "present"}
    else:
        result[str(mcp)] = {"addr": hex(addr), "status": "missing"}
result["all_present"] = all(v["status"] == "present" for v in result.values())
print(json.dumps(result))
"""
        code, out, err = _exec_script(client, detect_script)
        if code == 0 and out.strip():
            try:
                results["mcp_detection"] = json.loads(out)
            except json.JSONDecodeError:
                results["mcp_detection"] = {"raw": out, "parse_error": True}

        reg_script = r"""
import smbus, json
i2c = smbus.SMBus(1)
ADDRS = {1:0x20,2:0x21,3:0x22,4:0x23,5:0x24,6:0x25,7:0x26,8:0x27}
result = {}
all_ok = True
for m, a in ADDRS.items():
    try:
        iodira = i2c.read_byte_data(a, 0x00)
        iodirb = i2c.read_byte_data(a, 0x01)
        gpioa = i2c.read_byte_data(a, 0x12)
        olata = i2c.read_byte_data(a, 0x14)
        gpiob = i2c.read_byte_data(a, 0x13)
        gppub = i2c.read_byte_data(a, 0x0D)
        result[str(m)] = {"iodira":iodira,"iodirb":iodirb,"gpioa":gpioa,"olata":olata,"gpiob":gpiob,"gppub":gppub}
        if iodira != 0 or iodirb != 0xFF:
            all_ok = False
    except Exception as e:
        result[str(m)] = {"error":str(e)}
        all_ok = False
result["all_registers_ok"] = all_ok
print(json.dumps(result))
"""
        code, out, err = _exec_script(client, reg_script)
        if code == 0 and out.strip():
            try:
                results["mcp_registers"] = json.loads(out)
            except json.JSONDecodeError:
                pass

        code, out, err = _exec(client, "python3 -c 'import smbus; print(\"smbus:ok\")' 2>&1; python3 -c 'import lgpio; print(\"lgpio:ok\")' 2>&1")
        results["python_deps"] = {"smbus": "ok" if "smbus:ok" in out else "fail", "lgpio": "ok" if "lgpio:ok" in out else "fail"}

        code, out, err = _exec(client, "cat /sys/class/i2c-adapter/i2c-1/name 2>/dev/null || echo 'N/A'")
        results["i2c_bus"] = out

        code, out, err = _exec(client, "ls -la /dev/i2c-* /dev/gpiomem 2>/dev/null")
        results["device_perms"] = out.split("\n") if out else []

        client.close()

        issues = []
        mcp_detect = results.get("mcp_detection", {})
        if mcp_detect.get("all_present") is False:
            for k, v in mcp_detect.items():
                if isinstance(v, dict) and v.get("status") == "missing":
                    issues.append(f"MCP {k} ({v.get('addr', '?')}) not responding")
        mcp_regs = results.get("mcp_registers", {})
        if mcp_regs.get("all_registers_ok") is False:
            issues.append("MCP register corruption detected")
        if results.get("python_deps", {}).get("smbus") == "fail":
            issues.append("smbus not available - I2C communication will fail")

        status = "pass"
        if issues:
            status = "warn" if len(issues) <= 2 else "fail"

        return {"ok": True, "status": status, "issues": issues, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def troubleshoot(machine_name, fix_type):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    valid_fixes = {"reconfigure_mcps", "kill_conflicts"}
    if fix_type not in valid_fixes:
        return {"ok": False, "error": f"Fix must be one of: {', '.join(sorted(valid_fixes))}"}
    try:
        client = _ssh_connect(machine)
        result = {}

        if fix_type == "reconfigure_mcps":
            script = r"""
import smbus, json
i2c = smbus.SMBus(1)
ADDRS = {1:0x20,2:0x21,3:0x22,4:0x23,5:0x24,6:0x25,7:0x26,8:0x27}
results = {}
for m, a in ADDRS.items():
    try:
        i2c.write_byte_data(a, 0x00, 0x00)
        i2c.write_byte_data(a, 0x01, 0xFF)
        i2c.write_byte_data(a, 0x0D, 0xFF)
        results[str(m)] = {"addr": hex(a), "status": "reconfigured"}
    except Exception as e:
        results[str(m)] = {"addr": hex(a), "error": str(e)}
print(json.dumps({"ok": True, "results": results}))
"""
            code, out, err = _exec_script(client, script)
            if code == 0 and out.strip():
                try:
                    result = json.loads(out)
                except json.JSONDecodeError:
                    result = {"raw": out, "note": "non-JSON output"}
            else:
                result = {"ok": False, "error": err or "Script failed"}

        elif fix_type == "kill_conflicts":

            code1, out1, err1 = _exec(client, "ps aux | grep -iE '(assembly_test_app|device_daemon)' | grep -v grep | awk '{print $2}' || true")
            pids = [p.strip() for p in out1.split("\n") if p.strip()]
            killed = []
            for pid in pids:
                try:
                    code, o, e = _exec(client, f"kill {pid} 2>&1 || kill -9 {pid} 2>&1 || true")
                    killed.append({"pid": pid, "result": o or e or "killed"})
                except Exception as ee:
                    killed.append({"pid": pid, "error": str(ee)})

            result = {"ok": True, "action": "kill_conflicts", "found_pids": pids, "killed": killed}

        client.close()
        return {"ok": True, "output": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_connection_check(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        checks = []
        diagnose = bt_diagnose(machine_name)
        if not diagnose.get("ok"):
            client.close()
            return {"ok": False, "error": diagnose.get("error", "BT diagnose failed")}

        _, now_out, _ = _exec(client, "date; uptime", timeout=10)
        _, usb_out, _ = _exec(client, "dmesg 2>&1 | grep -iE 'reset full-speed USB device|Bluetooth: hci|usb 1-1|xhci' | tail -120", timeout=20)
        _, bt_journal, _ = _exec(client, "journalctl -u bluetooth --since '2 hours ago' --no-pager 2>&1 | tail -160", timeout=25)
        _, app_log, _ = _exec(client, "for f in ~/auto-dfu-tool/ring-manager-data/logs/app.log ~/auto-dfu-tool/assembly_test_app/logs/app.log ~/auto-dfu-tool/assembly_test_app/logs/*.log; do [ -f \"$f\" ] && echo \"### $f\" && tail -1200 \"$f\"; done 2>/dev/null | tail -2500", timeout=30)
        client.close()

        combined = "\n".join([usb_out, bt_journal, app_log])
        usb_resets = [line.strip() for line in usb_out.splitlines() if "reset full-speed USB device" in line]
        no_agent = [line.strip() for line in bt_journal.splitlines() if "No agent available" in line or "device_confirm_passkey" in line]
        failures = [line.strip() for line in combined.splitlines() if any(t in line.lower() for t in ["connect failed", "connection failed", "failed to connect", "timeout", "disconnected", "not found"])]
        mac_counts = {}
        for line in failures + no_agent:
            for mac in re.findall(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", line):
                mac_counts[mac.upper()] = mac_counts.get(mac.upper(), 0) + 1
        top_macs = sorted(mac_counts.items(), key=lambda item: item[1], reverse=True)[:8]

        hci1_up = bool(diagnose.get("output", "") and "hci1" in diagnose.get("output", "") and "UP RUNNING" in diagnose.get("output", ""))
        svc_ok = "Active" in diagnose.get("output", "")
        if hci1_up and svc_ok:
            checks.append("Bluetooth is currently alive: hci1 UP, service active.")
        else:
            checks.append("Bluetooth is currently unhealthy: adapter or service down.")
        if usb_resets:
            checks.append(f"USB Bluetooth reset events found: {len(usb_resets)} recent lines in dmesg tail.")
        else:
            checks.append("No recent USB reset lines found in dmesg tail.")
        if no_agent:
            checks.append(f"Pairing-agent errors found: {len(no_agent)} in Bluetooth journal.")
        else:
            checks.append("No recent pairing-agent errors found in Bluetooth journal.")

        if len(top_macs) == 1 and top_macs[0][1] >= 3:
            checks.append(f"Likely ring-specific issue: repeated failures mention {top_macs[0][0]}.")
            likely = "ring"
        elif usb_resets or len(top_macs) > 1:
            checks.append("Likely machine Bluetooth/adapter instability: USB resets or multiple devices affected.")
            likely = "machine_bluetooth"
        else:
            checks.append("Cause unclear from recent logs; keep live log running during the next connection attempt.")
            likely = "unclear"

        output = [
            *checks, "",
            "Top failing MACs:",
            *(f"  {mac}: {count}" for mac, count in top_macs), "",
            "Recent USB reset lines:",
            *usb_resets[-8:], "",
            "Recent pairing-agent lines:",
            *no_agent[-8:], "",
            "Recent app/bluetooth failure lines:",
            *failures[-20:],
        ]
        return {"ok": True, "likely_cause": likely, "usb_reset_count": len(usb_resets), "pairing_agent_error_count": len(no_agent), "top_macs": top_macs, "output": output, "time": now_out.splitlines()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_live_log(machine_name, duration=120, lines=120):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        duration = max(5, int(duration))
        tail_lines = max(20, int(lines))
        client = _ssh_connect(machine)
        command = (
            "LOGS=\"\"; "
            "for f in ~/auto-dfu-tool/ring-manager-data/logs/app.log "
            "~/auto-dfu-tool/assembly_test_app/logs/app.log "
            "~/auto-dfu-tool/ring-manager-data/logs/app.log.1; do "
            "[ -f \"$f\" ] && LOGS=\"$LOGS $f\"; "
            "done; "
            "if [ -z \"$LOGS\" ]; then echo 'No app log files found'; exit 1; fi; "
            f"echo 'Streaming logs for {duration}s. Press Ctrl+C to stop.'; "
            f"timeout {duration} tail -n {tail_lines} -f $LOGS"
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=duration + 10)
        channel = stdout.channel
        channel.settimeout(1.0)
        collected = []
        end_at = time.time() + duration + 5
        while True:
            if channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="replace")
                if data:
                    collected.append(data)
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                if data:
                    collected.append(data)
            if channel.exit_status_ready():
                break
            if time.time() >= end_at:
                channel.close()
                break
            time.sleep(0.1)
        client.close()
        full = "".join(collected)
        return {"ok": True, "output": full}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_fix_crash_loop(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        lines = [
            "Safe Bluetooth crash-loop recovery",
            "No app files/data/config/database are changed.",
            "Bluetooth connections may briefly drop during adapter power cycle.",
        ]
        commands = [
            ("unblock rfkill", f"{prefix}rfkill unblock bluetooth 2>&1 || true"),
            ("bluetooth power off", f"{prefix}bluetoothctl power off 2>&1 || true"),
            ("settle", "sleep 2"),
            ("bluetooth power on", f"{prefix}bluetoothctl power on 2>&1 || true"),
            ("bring hci1 up", f"{prefix}hciconfig hci1 up 2>&1 || true"),
            ("bring hci0 up", f"{prefix}hciconfig hci0 up 2>&1 || true"),
        ]
        for label, command in commands:
            code, out, err = _exec(client, command, timeout=25)
            text = (out or err or "").strip()
            state = "OK" if code == 0 else "WARN"
            lines.append(f"{label}: {state}" + (f" - {text.splitlines()[-1]}" if text else ""))
        post = bt_diagnose(machine_name)
        lines.append("")
        hci0_ok = "hci0" in str(post) and "UP" in str(post)
        hci1_ok = "hci1" in str(post) and "UP" in str(post)
        lines.append(f"After recovery: hci0={'UP' if hci0_ok else 'DOWN'}, hci1={'UP' if hci1_ok else 'DOWN'}")
        client.close()
        return {"ok": True, "output": lines, "post_diagnose": post}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_fix_pairing_popup_safe(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        user = machine["user"]
        agent_path = f"/tmp/bdr_bluez_agent_{user}.py"
        log_path = f"/tmp/bdr_bluez_agent_{user}.log"
        agent_script = '''#!/usr/bin/env python3
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

AGENT_IFACE = "org.bluez.Agent1"
AGENT_PATH = "/com/ultrahuman/bdr/safe_agent"

class Agent(dbus.service.Object):
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self): pass
    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid): pass
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device): return "0000"
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device): return dbus.UInt32(0)
    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered): pass
    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey): pass
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device): pass
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self): pass

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    agent = Agent(bus, AGENT_PATH)
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1")
    try: manager.UnregisterAgent(AGENT_PATH)
    except Exception: pass
    manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    manager.RequestDefaultAgent(AGENT_PATH)
    print("BDR safe BlueZ NoInputNoOutput agent registered", flush=True)
    GLib.MainLoop().run()

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"BDR safe BlueZ agent failed: {exc}", file=sys.stderr, flush=True)
        raise
'''
        steps = [
            "Safe pairing-popup fix:",
            "- no app/config/database/log data changed",
            "- no systemd service installed",
            "- temporary agent script is written only under /tmp",
        ]
        commands = [
            ("bluetooth service", "systemctl is-active bluetooth 2>&1"),
            ("start bluetooth if needed", f"if ! systemctl is-active --quiet bluetooth; then {prefix}systemctl start bluetooth 2>&1; fi"),
            ("unblock runtime rfkill", f"{prefix}rfkill unblock bluetooth 2>&1 || true"),
            ("write temporary agent", f"cat > {_sh_quote(agent_path)} <<'PY'\n{agent_script}\nPY\nchmod +x {_sh_quote(agent_path)}"),
            ("stop old temporary agent", "for pid in $(pgrep -f '[b]dr_bluez_agent_' 2>/dev/null); do kill \"$pid\" 2>/dev/null || true; done; true"),
            ("start temporary agent", f"nohup /usr/bin/python3 {_sh_quote(agent_path)} > {_sh_quote(log_path)} 2>&1 & echo $!"),
            ("configure pairable mode", "sleep 2; printf 'power on\\npairable on\\ndiscoverable off\\nquit\\n' | bluetoothctl 2>&1"),
        ]
        for label, command in commands:
            code, out, err = _exec(client, command, timeout=20)
            text = (out or err or "").strip()
            if code == 0:
                steps.append(f"{label}: OK" + (f" - {text.splitlines()[-1]}" if text else ""))
            else:
                steps.append(f"{label}: FAIL - {text}")
        _, ps_out, _ = _exec(client, f"ps aux | grep -F {_sh_quote(agent_path)} | grep -v grep || true", timeout=10)
        _, log_out, _ = _exec(client, f"tail -20 {_sh_quote(log_path)} 2>/dev/null || true", timeout=10)
        _, bt_out, _ = _exec(client, "systemctl is-active bluetooth 2>&1", timeout=10)
        agent_active = bool(ps_out.strip())
        steps.append(f"temporary agent: {'active' if agent_active else 'not active'}")
        if log_out.strip():
            steps.append("agent log:")
            steps.extend(log_out.splitlines()[-8:])
        steps.append(f"Bluetooth service: {bt_out.strip()}")
        client.close()
        return {"ok": agent_active, "output": steps}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fetch_app_logs(machine_name, lines=200):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        # Command to get the last N lines from all log files
        command = (
            "LOGS=\"\"; "
            "for f in ~/auto-dfu-tool/ring-manager-data/logs/app.log "
            "~/auto-dfu-tool/assembly_test_app/logs/app.log "
            "~/auto-dfu-tool/ring-manager-data/logs/app.log.1 "
            "~/auto-dfu-tool/assembly_test_app/logs/app.log.1; do "
            "[ -f \"$f\" ] && LOGS=\"$LOGS $f\"; "
            "done; "
            "if [ -z \"$LOGS\" ]; then echo 'No app log files found'; exit 1; fi; "
            f"tail -n {lines} $LOGS"
        )
        code, out, err = _exec(client, command, timeout=30)
        client.close()
        if code != 0:
            return {"ok": False, "error": err or out or "Failed to fetch logs"}
        # Parse log lines, try to extract timestamps
        log_entries = []
        timestamp_patterns = [
            # Common log timestamp formats
            re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6})'),  # ISO 8601 with microseconds
            re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'),  # ISO like
            re.compile(r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})'),  # MM/DD/YYYY
        ]
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            timestamp = None
            for pattern in timestamp_patterns:
                match = pattern.search(line)
                if match:
                    timestamp_str = match.group(1)
                    # Try to parse to datetime
                    try:
                        if 'T' in timestamp_str:
                            dt = datetime.datetime.fromisoformat(timestamp_str)
                        else:
                            dt = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        timestamp = dt.timestamp()
                    except ValueError:
                        try:
                            dt = datetime.datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
                            timestamp = dt.timestamp()
                        except ValueError:
                            pass
                    break
            log_entries.append({
                'timestamp': timestamp,
                'line': line
            })
        return {"ok": True, "entries": log_entries}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_fix_pairing_popup_persistent(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        user = machine["user"]
        home = f"/home/{user}"
        agent_path = f"{home}/.bdr_bluez_agent.py"
        service_path = "/etc/systemd/system/bdr-bluez-agent.service"
        agent_script = '''#!/usr/bin/env python3
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

AGENT_IFACE = "org.bluez.Agent1"
AGENT_PATH = "/com/ultrahuman/bdr/agent"

class Agent(dbus.service.Object):
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self): pass
    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid): pass
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device): return "0000"
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device): return dbus.UInt32(0)
    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered): pass
    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey): pass
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device): pass
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self): pass

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    agent = Agent(bus, AGENT_PATH)
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1")
    try: manager.UnregisterAgent(AGENT_PATH)
    except Exception: pass
    manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    manager.RequestDefaultAgent(AGENT_PATH)
    print("BDR BlueZ NoInputNoOutput agent registered", flush=True)
    GLib.MainLoop().run()

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"BDR BlueZ agent failed: {exc}", file=sys.stderr, flush=True)
        raise
'''
        service = f"""[Unit]
Description=BDR BlueZ NoInputNoOutput Pairing Agent
After=bluetooth.service dbus.service
Wants=bluetooth.service

[Service]
Type=simple
User={user}
ExecStart=/usr/bin/python3 {agent_path}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
"""
        steps = []
        commands = [
            ("unblock", f"{prefix}rfkill unblock bluetooth 2>&1 || true"),
            ("restart bluetooth", f"{prefix}systemctl restart bluetooth 2>&1"),
            ("write agent", f"cat > {_sh_quote(agent_path)} <<'PY'\n{agent_script}\nPY\nchmod +x {_sh_quote(agent_path)}"),
            ("unmask agent", f"{prefix}systemctl unmask bdr-bluez-agent.service 2>&1 || true"),
            ("remove masked link", f"{prefix}rm -f {_sh_quote(service_path)} 2>&1 || true"),
            ("write service", f"cat <<'SERVICE' | {prefix}tee {_sh_quote(service_path)} >/dev/null\n{service}\nSERVICE"),
            ("reload systemd", f"{prefix}systemctl daemon-reload 2>&1"),
            ("enable agent", f"{prefix}systemctl enable --now bdr-bluez-agent.service 2>&1"),
            ("configure adapter", "printf 'power on\\npairable on\\ndiscoverable off\\nagent NoInputNoOutput\\ndefault-agent\\nquit\\n' | bluetoothctl 2>&1"),
        ]
        for label, command in commands:
            code, out, err = _exec(client, command, timeout=30)
            text = (out or err or "").strip()
            if code == 0:
                steps.append(f"{label}: OK" + (f" - {text.splitlines()[-1]}" if text else ""))
            else:
                steps.append(f"{label}: FAIL - {text}")
        _, status, _ = _exec(client, "systemctl is-active bdr-bluez-agent.service 2>&1; systemctl status bdr-bluez-agent.service --no-pager 2>&1 | head -12", timeout=20)
        _, bluetooth_status, _ = _exec(client, "systemctl is-active bluetooth 2>&1", timeout=10)
        client.close()
        return {"ok": True, "output": steps + ["", "Agent service:", *status.splitlines(), f"Bluetooth service: {bluetooth_status.strip()}"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def motor_status(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        code, out, err = _exec(client, "ps aux | grep -iE '(motor|homing|servo)' | grep -v grep || echo 'No motor process found'")
        client.close()
        return {"ok": True, "processes": out.split("\n") if out else []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Advanced MCP / I2C Diagnostics ────────────────────────────────

def mcp_scan(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        bus_detect = _build_bus_detect_script()
        script = bus_detect + r"""
result = {}
all_present = True
for mcp, addr in expected.items():
    try:
        iodira = bus.read_byte_data(addr, 0x00)
        iodirb = bus.read_byte_data(addr, 0x01)
        gpioa = bus.read_byte_data(addr, 0x12)
        gpiob = bus.read_byte_data(addr, 0x13)
        olata = bus.read_byte_data(addr, 0x14)
        gppub = bus.read_byte_data(addr, 0x0D)
        result[str(mcp)] = {
            "addr": hex(addr), "present": True,
            "iodira": iodira, "iodirb": iodirb,
            "gpioa": gpioa, "gpiob": gpiob,
            "olata": olata, "gppub": gppub,
        }
    except Exception as exc:
        result[str(mcp)] = {"addr": hex(addr), "present": False, "error": str(exc)}
        all_present = False
print(json.dumps({"ok": True, "bus": bus_num, "detected_count": detected_count, "all_present": all_present, "bus_errors": bus_errors, "result": result}))
"""
        code, out, err = _exec_python(client, script, timeout=45)
        client.close()
        if code != 0 and not out:
            return {"ok": False, "error": err or "MCP scan failed"}
        try:
            return json.loads(out)
        except Exception:
            return {"ok": False, "error": "Could not parse MCP scan output", "raw": out or err}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_repair(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        bus_detect = _build_bus_detect_script()
        script = bus_detect + r"""
import time
result = {}
for mcp, addr in expected.items():
    try:
        saved_olata = bus.read_byte_data(addr, 0x14)
        bus.write_byte_data(addr, 0x00, 0x00)
        bus.write_byte_data(addr, 0x01, 0xFF)
        bus.write_byte_data(addr, 0x0D, 0xFF)
        bus.write_byte_data(addr, 0x14, saved_olata)
        result[str(mcp)] = {"addr": hex(addr), "fixed": True, "saved_olata": saved_olata}
    except Exception as exc:
        result[str(mcp)] = {"addr": hex(addr), "fixed": False, "error": str(exc)}
print(json.dumps({"ok": True, "bus": bus_num, "detected_count": detected_count, "result": result}))
"""
        code, out, err = _exec_python(client, script, timeout=45)
        client.close()
        if code != 0 and not out:
            return {"ok": False, "error": err or "MCP repair failed"}
        try:
            return json.loads(out)
        except Exception:
            return {"ok": False, "error": "Could not parse MCP repair output", "raw": out or err}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_advanced_repair(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        bus_detect = _build_bus_detect_script()
        script = bus_detect + r"""
import time
results = {}
changed = False
for mcp, addr in expected.items():
    entry = {"addr": hex(addr), "present": False, "changed": False}
    try:
        before = {
            "iodira": bus.read_byte_data(addr, 0x00),
            "iodirb": bus.read_byte_data(addr, 0x01),
            "gppub": bus.read_byte_data(addr, 0x0D),
            "olata": bus.read_byte_data(addr, 0x14),
            "gpioa": bus.read_byte_data(addr, 0x12),
            "gpiob": bus.read_byte_data(addr, 0x13),
        }
        entry["present"] = True
        entry["before"] = before
        saved_olata = before["olata"]
        writes = []
        if before["iodira"] != 0x00:
            bus.write_byte_data(addr, 0x00, 0x00)
            writes.append("IODIRA->0x00")
        if before["iodirb"] != 0xFF:
            bus.write_byte_data(addr, 0x01, 0xFF)
            writes.append("IODIRB->0xFF")
        if before["gppub"] != 0xFF:
            bus.write_byte_data(addr, 0x0D, 0xFF)
            writes.append("GPPUB->0xFF")
        if writes:
            time.sleep(0.03)
            bus.write_byte_data(addr, 0x14, saved_olata)
            changed = True
            entry["changed"] = True
            entry["writes"] = writes
        after = {
            "iodira": bus.read_byte_data(addr, 0x00),
            "iodirb": bus.read_byte_data(addr, 0x01),
            "gppub": bus.read_byte_data(addr, 0x0D),
            "olata": bus.read_byte_data(addr, 0x14),
            "gpioa": bus.read_byte_data(addr, 0x12),
            "gpiob": bus.read_byte_data(addr, 0x13),
        }
        entry["after"] = after
        entry["safe"] = after["olata"] == saved_olata
    except Exception as exc:
        entry["error"] = str(exc)
    results[str(mcp)] = entry

print(json.dumps({
    "ok": True, "mode": "advanced-safe",
    "bus": bus_num, "detected_count": detected_count,
    "changed": changed, "bus_errors": bus_errors, "result": results,
}))
"""
        code, out, err = _exec_python(client, script, timeout=45)
        client.close()
        if code != 0 and not out:
            return {"ok": False, "error": err or "Advanced MCP repair failed"}
        try:
            return json.loads(out)
        except Exception:
            return {"ok": False, "error": "Could not parse advanced MCP repair output", "raw": out or err}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def button_advanced_repair(machine_name):
    return mcp_advanced_repair(machine_name)


# ── Audit Functions ────────────────────────────────────────────────

def audit_folders(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        root = f"/home/{machine['user']}/auto-dfu-tool"
        script = f"""
import json, os
from pathlib import Path

root = Path({_sh_quote(root)})
targets = {{
    "assembly_test_app": root / "assembly_test_app",
    "ring-manager-data": root / "ring-manager-data",
}}
result = {{}}
for name, path in targets.items():
    entry = {{"path": str(path), "exists": path.is_dir()}}
    if path.is_dir():
        try:
            listing = []
            for child in sorted(path.iterdir()):
                listing.append(child.name)
                if len(listing) >= 30:
                    break
            entry["top_level"] = listing
            file_hits = []
            for child in path.rglob("*"):
                if not child.is_file():
                    continue
                if child.suffix.lower() in {{".py", ".json", ".log", ".service", ".sh", ".txt"}}:
                    file_hits.append(str(child.relative_to(path)))
                if len(file_hits) >= 60:
                    break
            entry["important_files"] = file_hits
        except Exception as exc:
            entry["error"] = str(exc)
    result[name] = entry
print(json.dumps(result))
"""
        code, out, err = _exec_python(client, script, timeout=45)
        client.close()
        if code != 0 and not out:
            return {"ok": False, "error": err or "Folder audit failed"}
        try:
            return {"ok": True, "folders": json.loads(out)}
        except Exception:
            return {"ok": False, "error": "Could not parse folder audit output", "raw": out or err}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def audit_processes(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        code, out, err = _exec(client, "ps aux | grep -iE '(assembly_test_app|ring-manager-data|device_daemon|bdr_report|bluetooth|mcp|button)' | grep -v grep || true", timeout=20)
        client.close()
        if code != 0 and not out:
            return {"ok": False, "error": err or "Process summary failed"}
        return {"ok": True, "output": out.splitlines() if out else []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def audit_system(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        code, out, err = _exec(client, "hostname; uptime; uname -a", timeout=15)
        client.close()
        if code != 0 and not out:
            return {"ok": False, "error": err or "System summary failed"}
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        return {"ok": True, "output": lines}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def kill_conflicts(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        code, out, err = _exec(client, "ps aux | grep -iE '(assembly_test_app|device_daemon)' | grep -v grep | awk '{print $2}' || true", timeout=20)
        pids = [line.strip() for line in out.splitlines() if line.strip()]
        killed = []
        for pid in pids:
            kcode, kout, kerr = _exec(client, f"kill {pid} 2>&1 || kill -9 {pid} 2>&1 || true", timeout=10)
            killed.append({"pid": pid, "output": kout or kerr or "killed"})
        client.close()
        return {"ok": True, "found_pids": pids, "killed": killed}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Bluetooth Diagnostics ──────────────────────────────────────────

def _bt_sudo_prefix():
    return f"echo '{AUTH_PASSWORD}' | sudo -S -k "


def _bt_get_hci_devices(client):
    code, out, _ = _exec(client, "hciconfig 2>&1 | grep -E '^hci' | awk -F: '{print $1}'")
    return [line.strip() for line in out.splitlines() if line.strip()]


def _bt_parse_hciconfig(output):
    adapters = re.split(r'\n(?=hci\d+:)', output)
    lines = []
    for block in adapters:
        block = block.strip()
        if not block:
            continue
        name_match = re.match(r"(hci\d+):", block)
        name = name_match.group(1) if name_match else "?"
        state = "UP" if "UP RUNNING" in block else "DOWN"
        bd_match = re.search(r"BD Address:\s+([0-9A-Fa-f:]{17})", block)
        bd_addr = bd_match.group(1) if bd_match else "N/A"
        bus = "USB" if "Bus: USB" in block else ("UART" if "Bus: UART" in block else "?")
        features = []
        if "LE" in block:
            features.append("BLE")
        if "BR/EDR" in block or "SCO" in block:
            features.append("BR/EDR")
        feat_str = ", ".join(features) if features else "N/A"
        lines.append(f"  {name:6s} | {state:5s} | {bus:4s} | {bd_addr:17s} | {feat_str}")
    return "\n".join(lines) if lines else output


def _bt_detect_crash_loop(dmesg_out):
    resets = []
    for line in dmesg_out.splitlines():
        if "reset full-speed USB" in line and "xhci-hcd" in line:
            resets.append(line.strip())
    return resets if len(resets) >= 2 else []


def _bt_check_hci_up(hci_out, name):
    blocks = hci_out.split("hci")[1:]
    for b in blocks:
        if ":" not in b:
            continue
        bname = "hci" + b[:b.index(":")]
        if bname == name:
            return "UP RUNNING" in b
    return False


def bt_status(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        lines = []
        code, out, err = _exec(client, "hciconfig -a 2>&1")
        if code != 0 and not out:
            lines.append(f"No Bluetooth adapters found: {err}")
        else:
            lines.append(_bt_parse_hciconfig(out) if out else "No hciconfig output")
        lines.append("")
        code, out, _ = _exec(client, f"{prefix}systemctl status bluetooth 2>&1 | head -10")
        lines.append("Service:")
        for line in out.splitlines():
            if any(k in line for k in ("Active:", "bluetooth.service", "Main PID", "Status:")):
                lines.append(f"  {line.strip()}")
        client.close()
        return {"ok": True, "output": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_diagnose(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"Bluetooth Diagnosis Report - {timestamp}", "=" * 60]

        _, hci_out, _ = _exec(client, "hciconfig -a 2>&1")
        _, svc_out, _ = _exec(client, "systemctl status bluetooth 2>&1 | head -12")
        _, svc_active, _ = _exec(client, "systemctl is-active bluetooth 2>&1")
        _, rf_out, _ = _exec(client, "rfkill list bluetooth 2>&1")
        _, dbus_out, _ = _exec(client, "dbus-send --system --dest=org.bluez --print-reply / org.freedesktop.DBus.Introspectable.Introspect 2>&1 | head -3")
        _, dmesg_out, _ = _exec(client, "dmesg 2>&1 | grep -iE 'bluetooth|hci|bt' | tail -30")
        _, con_out, _ = _exec(client, f"{prefix}hcitool con 2>&1")

        hci0_up = _bt_check_hci_up(hci_out, "hci0")
        hci1_up = _bt_check_hci_up(hci_out, "hci1")

        lines.append("\nADAPTER STATUS")
        lines.append("-" * 40)
        for line in hci_out.splitlines():
            if line.startswith("hci") or "BD Address" in line or "UP RUNNING" in line or "DOWN" in line:
                lines.append(f"  {line.strip()}")

        lines.append("\nSERVICE STATUS")
        lines.append("-" * 40)
        for line in svc_out.splitlines():
            if any(k in line for k in ("Active:", "bluetooth.service", "Main PID", "Status:")):
                lines.append(f"  {line.strip()}")
        dbus_ok = bool(dbus_out)
        lines.append(f"  BlueZ D-Bus: {'RESPONDING' if dbus_ok else 'NOT RESPONDING'}")
        rf_available = bool(rf_out.strip()) and "not found" not in rf_out
        if rf_available:
            blocked = "blocked" in rf_out.lower() and "yes" in rf_out.lower()
            lines.append(f"  RF Kill: {'BLOCKED' if blocked else 'Not blocked'}")
        else:
            lines.append("  RF Kill: not installed (skipped)")

        crash_resets = _bt_detect_crash_loop(dmesg_out)
        in_crash_loop = len(crash_resets) >= 2
        if in_crash_loop:
            lines.append("\nCRASH LOOP DETECTED")
            lines.append("-" * 40)
            lines.append(f"  hci1 (TP-Link USB) crashed {len(crash_resets)} times")
            for r in crash_resets[-3:]:
                lines.append(f"    {r[:90]}")

        con_raw = con_out or "(no active connections)"
        if "not permitted" not in con_raw.lower() and "permission denied" not in con_raw.lower():
            lines.append("\nACTIVE CONNECTIONS")
            lines.append("-" * 40)
            for cl in con_raw.splitlines():
                if cl.strip():
                    lines.append(f"  {cl.strip()}")

        lines.append(f"\n{'=' * 60}")
        lines.append("SUMMARY")
        lines.append("=" * 60)
        lines.append(f"  hci0 (UART):       [{'OK' if hci0_up else 'FAIL'}] {'UP RUNNING' if hci0_up else 'NOT UP'}")
        lines.append(f"  hci1 (USB TP-Link): [{'OK' if hci1_up else 'FAIL'}] {'UP RUNNING' if hci1_up else ('DOWN (crash loop)' if in_crash_loop else 'DOWN')}")
        svc_ok = "active" in svc_active
        lines.append(f"  Bluetooth service:  [{'OK' if svc_ok else 'FAIL'}] {'Active' if svc_ok else 'Inactive'}")
        lines.append(f"  BlueZ D-Bus:        [{'OK' if dbus_ok else 'FAIL'}] {'Responding' if dbus_ok else 'Not responding'}")
        lines.append(f"  RF Kill:            {'[OK] Not blocked' if rf_available and not blocked else '[--] N/A' if not rf_available else '[FAIL] Blocked'}")

        client.close()
        return {"ok": True, "output": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_scan(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        _exec(client, f"{prefix}hciconfig hci0 down 2>/dev/null; sleep 1; {prefix}hciconfig hci0 up 2>/dev/null")
        lines = []
        for hci in ["hci0", "hci1"]:
            cmd = f"{prefix}timeout 8 hcitool -i {hci} lescan 2>&1 | head -50"
            _, out, _ = _exec(client, cmd)
            safe = out.encode("ascii", errors="replace").decode("ascii") if out else ""
            valid = [l.strip() for l in safe.splitlines()
                     if l.strip() and ":" in l and "Duplicate" not in l
                     and "Set scan parameters failed" not in l
                     and "password for" not in l
                     and "LE Scan" not in l
                     and "Input/output error" not in l]
            if valid:
                lines.append(f"BLE devices on {hci}:")
                seen = set()
                for l in valid:
                    parts = l.split(None, 1)
                    mac = parts[0] if parts else "?"
                    if mac in seen:
                        continue
                    seen.add(mac)
                    name = parts[1] if len(parts) > 1 else "(unknown)"
                    lines.append(f"  {mac:42s} {name:30s}")
        if not lines:
            lines.append("No BLE devices found in range.")
        client.close()
        return {"ok": True, "output": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_reset(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        hci_list = _bt_get_hci_devices(client)
        if not hci_list:
            client.close()
            return {"ok": False, "error": "No hci devices found"}
        results = []
        for hci in hci_list:
            _exec(client, f"{prefix}hciconfig {hci} down 2>&1")
            time.sleep(0.5)
            _, out, _ = _exec(client, f"{prefix}hciconfig {hci} up 2>&1")
            results.append(f"  {hci}: {out.strip() or 'OK'}")
        _, out, _ = _exec(client, "hciconfig -a 2>&1")
        parsed = _bt_parse_hciconfig(out) if out else "No output"
        client.close()
        return {"ok": True, "output": "Reset results:\n" + "\n".join(results) + "\n\nPost-reset status:\n" + parsed}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_full_reset(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        lines = []
        lines.append("=== Step 1: Restarting Bluetooth Service ===")
        _, out, _ = _exec(client, f"{prefix}systemctl restart bluetooth 2>&1; sleep 2; systemctl status bluetooth 2>&1 | head -10")
        lines.append(out or "Bluetooth service restarted")
        lines.append("\n=== Step 2: Resetting Adapter(s) ===")
        hci_list = _bt_get_hci_devices(client)
        if hci_list:
            for hci in hci_list:
                _exec(client, f"{prefix}hciconfig {hci} down 2>&1")
                time.sleep(0.5)
                _, out, _ = _exec(client, f"{prefix}hciconfig {hci} up 2>&1")
                lines.append(f"  {hci}: {out.strip() or 'OK'}")
        lines.append("\n=== Step 3: Verifying ===")
        _, out, _ = _exec(client, "hciconfig -a 2>&1")
        lines.append(_bt_parse_hciconfig(out) if out else "No output")
        _, out, _ = _exec(client, f"{prefix}systemctl status bluetooth 2>&1 | grep -E 'Active:|Loaded:'")
        lines.append(out or "Service status unavailable")
        lines.append("\n=== Step 4: BLE Scan Test ===")
        _exec(client, f"{prefix}hciconfig hci0 down 2>/dev/null; sleep 1; {prefix}hciconfig hci0 up 2>/dev/null")
        _, out, _ = _exec(client, f"{prefix}timeout 8 hcitool -i hci0 lescan 2>&1 | head -10")
        safe = out.encode("ascii", errors="replace").decode("ascii") if out else ""
        valid = [l.strip() for l in safe.splitlines() if l.strip() and ":" in l]
        lines.append(f"  Found {len(valid)} BLE devices" if valid else "  No BLE devices found")
        client.close()
        return {"ok": True, "output": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bt_recover(machine_name):
    machine = _load_machine_config(machine_name)
    if not machine:
        return {"ok": False, "error": f"Machine '{machine_name}' not found"}
    try:
        client = _ssh_connect(machine)
        prefix = _bt_sudo_prefix()
        lines = ["=" * 60, "  BLUETOOTH RECOVERY", "=" * 60]
        _, hci_out, _ = _exec(client, "hciconfig -a 2>&1")
        hci0_up = _bt_check_hci_up(hci_out, "hci0")
        hci1_up = _bt_check_hci_up(hci_out, "hci1")
        lines.append(f"\n  Current: hci0={'UP' if hci0_up else 'DOWN'}, hci1={'UP' if hci1_up else 'DOWN'}")
        if hci1_up and hci0_up:
            lines.append("  Both adapters already UP - no recovery needed.")
            client.close()
            return {"ok": True, "output": "\n".join(lines)}
        lines.append("\n  Step 1: bluetoothctl power cycle...")
        _exec(client, f"{prefix}bluetoothctl power off 2>&1")
        time.sleep(2)
        _exec(client, f"{prefix}bluetoothctl power on 2>&1")
        time.sleep(3)
        _, hci_out, _ = _exec(client, "hciconfig -a 2>&1")
        if _bt_check_hci_up(hci_out, "hci1"):
            lines.append("  Result: hci1 is UP - gentle recovery worked")
            client.close()
            return {"ok": True, "output": "\n".join(lines)}
        lines.append("\n  Step 2: systemctl restart bluetooth...")
        _, out, _ = _exec(client, f"{prefix}systemctl restart bluetooth 2>&1")
        if out.strip():
            lines.append(f"  restart: {out.strip()[:80]}")
        time.sleep(5)
        _, out, _ = _exec(client, f"{prefix}systemctl status bluetooth 2>&1 | grep 'Active:'")
        lines.append(f"  service: {out.strip() or '(checking...)'}")
        time.sleep(2)
        _, hci_out, _ = _exec(client, "hciconfig -a 2>&1")
        hci1_up = _bt_check_hci_up(hci_out, "hci1")
        hci0_up = _bt_check_hci_up(hci_out, "hci0")
        lines.append(f"  Result: hci0={'UP' if hci0_up else 'DOWN'}, hci1={'UP' if hci1_up else 'DOWN'}")
        if hci1_up or hci0_up:
            lines.append("  Recovery completed - adapters are UP")
        else:
            lines.append("  Adapters still DOWN - physical intervention needed:")
            lines.append("    1. Unplug the TP-Link USB dongle")
            lines.append("    2. Wait 10 seconds")
            lines.append("    3. Plug it back in")
        client.close()
        return {"ok": True, "output": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
