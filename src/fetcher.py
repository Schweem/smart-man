import asyncio
import shlex
import subprocess

def fetch_page(command : str):
    sanitized_command = shlex.quote(command) # shelx sanatize
    shell_command = f"man -P cat {sanitized_command} | col -b"

    try: # run command in the shell, return the stdout 
        output = subprocess.run(
            shell_command, 
            shell=True, 
            capture_output=True,
            text=True,
            check=True
        )
        return output.stdout
    
    except Exception as e: # otherwise throw exception
        return e
    
async def async_fetch(command : str):
    sanitized_command = shlex.quote(command) # sanatize command with shlex 
    shell_command = f"man -P cat {sanitized_command} | col -b"

    process = await asyncio.create_subprocess_shell( # create the asyncio process
        shell_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate() # await the output of the running process

    if process.returncode == 0: # return either the text or the error
        return stdout.decode().strip()
    else:
        return stderr


    
def main() -> None:
    test_cmd = fetch_page("brew") # testing standard command
    print(test_cmd)

    async_cmd = asyncio.run(async_fetch("cat")) # testing async
    print(async_cmd)

    return 

if __name__ == "__main__":
    main()