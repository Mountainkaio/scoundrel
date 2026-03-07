import sys
import os

# Windows
if os.name == "nt":
	import msvcrt

	class InstantInput:
		def __enter__(self):
			return self

		def __exit__(self, exc_type, exc, tb):
			pass

		def get_key(self):
			ch = msvcrt.getch()

			# Special keys
			if ch in (b'\x00', b'\xe0'):
				ch2 = msvcrt.getch()
				return (ch + ch2).decode(errors="ignore")

			try:
				return ch.decode()
			except UnicodeDecodeError:
				return ""

# Linux
else:
	import termios
	import tty

	class InstantInput:
		def __enter__(self):
			self.fd = sys.stdin.fileno()
			self.old = termios.tcgetattr(self.fd)

			tty.setcbreak(self.fd)

			# Disable echo
			new = termios.tcgetattr(self.fd)
			new[3] &= ~termios.ECHO
			termios.tcsetattr(self.fd, termios.TCSADRAIN, new)

			return self

		def __exit__(self, exc_type, exc, tb):
			termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

		def get_key(self):
			ch = sys.stdin.read(1)

			if ch == '\x1b':
				seq = ch
				while True:
					c = sys.stdin.read(1)
					seq += c
					if c.isalpha() or c == '~':
						break
				return seq

			return ch
