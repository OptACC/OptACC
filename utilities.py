import subprocess

def call_command(cmd, env=None, fail_on_nonzero=False):
    '''Calls a shell command, optionally setting environment variables

        cmd -- command to execute
        env -- a dictionary of environment variables.  Note that this is the
               full set of environment variables given to the command.  If you
               want to include the current environment variables for the Python
               process, you will need to merge them.
        fail_on_nonzero -- if True, an exception will be raised if the return
                           code of the called command is nonzero.

        Returns a tuple (output, returncode)
    '''

    handle = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Redirect stderr to stdout
            env=env,
            shell=True)

    stdout, _ = handle.communicate()

    if handle.returncode != 0 and fail_on_nonzero:
        err = subprocess.CalledProcessError(handle.returncode, cmd)
        err.output = stdout
        raise err

    return stdout, handle.returncode
