from io import StringIO
import sys
import shlex
import gc

def run_command(command="zucaro"):
    # Remove all zucaro-related modules from sys.modules BEFORE import
    modules_to_remove = [mod for mod in sys.modules if mod.startswith('zucaro')]
    for mod in modules_to_remove:
        del sys.modules[mod]
    gc.collect()

    # Import zucaro_cli dynamically
    from zucaro.cli.main import zucaro_cli

    # Redirect stdout and stderr to capture the command output
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = mystdout = StringIO()
    sys.stderr = mystderr = StringIO()
    
    try:
        # Use shlex.split to properly parse the command string
        # This will call Click's CLI as if from command line, using args
        zucaro_cli.main(args=shlex.split(command))
    except SystemExit as e:
        if e.code != 0:
            print(f"Command exited with code {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    output = mystdout.getvalue().strip()
    mystderr.getvalue().strip()

    # Cleanup: remove zucaro-related modules from sys.modules and force garbage collection
    modules_to_remove = [mod for mod in sys.modules if mod.startswith('zucaro')]
    for mod in modules_to_remove:
        del sys.modules[mod]
    gc.collect()
    
    if not output:
        return None
    return output
