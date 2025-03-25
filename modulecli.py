import click
from picomc.cli.main import picomc_cli
from io import StringIO
import sys

def run_command(command="picomc"):
    # Redirect stdout and stderr to capture the command output
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = mystdout = StringIO()
    sys.stderr = mystderr = StringIO()
    
    try:
        picomc_cli.main(args=command.split())
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
    error = mystderr.getvalue().strip()
    
    if not output:
        return f"Error: No output from command. Stderr: {error}"
    
    return output