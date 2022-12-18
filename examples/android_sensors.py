import asyncio
import json
import sys


async def get_sensor_output():
    # Create the subprocess process
    process = await asyncio.create_subprocess_shell(
        "termux-sensor -s gravit -d 50 | jq --unbuffered -c",
        # "termux-sensor -s linear_ac -d 50 | jq --unbuffered -c",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Initialize a dictionary to store the values for each index
    values = {0: None, 1: None, 2: None}

    # Read the output of the process and store the values
    try:
        async for line in process.stdout:
            data = json.loads(line)
            if data:
                yield data["gravity  Non-wakeup"]["values"]
                # yield data["linear_acceleration"]["values"]
    finally:
        await asyncio.create_subprocess_shell("termux-sensor -c")


if __name__ == "__main__":

    async def main():
        # Run the sensor cleanup command before starting the loop
        from brailliant.sparkline import get_sparkbar_normalized, sparkline

        line_data = [], [], []
        async for data in get_sensor_output():  # as sensor_data:
            s = get_sparkbar_normalized(data, 60, 10, 20)
            for i, ld in zip(data, line_data):
                ld.append(i)

            # sys.stdout.buffer.write(b"Ok, I can do this\n")
            # sys.stdout.buffer.write(b"\n  " + s.encode())# +b"\r\033[F")
            # for ld in line_data:
            #    sys.stdout.buffer.write(b"\n  " + sparkline(ld, 60).encode())
            # sys.stdout.buffer.write(b"\r\033[F"*4)
            ss = [s.encode()]
            for ld in line_data:
                ss.append(sparkline(ld, 50).encode())
            buf = b"\033[2J\033[0;0H" + b"\n\n  ".join(ss) + b"\n\n"
            sys.stdout.buffer.write(buf)

    # Run the main function
    asyncio.run(main())
