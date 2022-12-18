from __future__ import annotations

import sys
import termios
import tty
import asyncio
import os
from collections import Counter
from typing import AsyncGenerator


async def async_getch() -> AsyncGenerator[bytes, None]:
    """
    Returns an async iterator that yields a character from the terminal
    in a non-blocking way.
    """
    # Save the current terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    # Set the terminal to cbreak mode and make sys.stdin non-blocking
    tty.setcbreak(sys.stdin)
    os.set_blocking(sys.stdin.fileno(), False)

    # Save the initial state of stdin in variable "old_stdin_blocking"
    old_stdin_blocking = os.get_blocking(sys.stdin.fileno())

    # Add a reader for sys.stdin
    ev = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_reader(sys.stdin, ev.set)

    try:
        while True:
            await ev.wait()
            char = sys.stdin.buffer.read()
            if not char:
                ev.clear()
                continue
            _ = yield char
    finally:
        # Remove the reader for sys.stdin
        asyncio.get_running_loop().remove_reader(sys.stdin)
        # Restore the blocking state of sys.stdin
        os.set_blocking(sys.stdin.fileno(), old_stdin_blocking)
        # Set the terminal settings back to their original state
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":

    async def main() -> None:
        """
        An example of how to use get_char.
        """
        # Create a counter to keep track of the number of times each character is typed
        c = Counter()

        # Start a task that prints a message every second with the number of keys typed
        # and the most common character
        async def print_stats():
            print("Go ahead and press some keys!")

            while True:
                await asyncio.sleep(1)
                count = sum(c.values())
                if not count:
                    print("Go ahead and press some keys!")
                    continue

                common, common_count = c.most_common(1)[0]
                print(f"Wow! {count} keys typed so far. {common_count} just for {common}!")
                if count > 60:
                    print("Alright, that's enough. Bye!")
                    break

        task = asyncio.create_task(print_stats())

        # Asynchronously iterate over the characters returned by get_char
        async for char in async_getch():
            print(f"You typed: {char}")
            c[char] += 1
        await task

    asyncio.run(main())
